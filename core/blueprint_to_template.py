"""
Blueprint to Template Converter
Converts a saved blueprint into a reusable format template for content_templates.json.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

ACCOUNTS_DIR = Path(__file__).parent.parent / "accounts"
BLUEPRINTS_DIR = Path(__file__).parent.parent / "blueprints"


class BlueprintToTemplate:
    """Converts analyzed post blueprints into reusable content format templates."""

    def __init__(self, openrouter_key: str = None):
        key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OpenRouter API key required")
        self.llm = LLMClient(api_key=key, model="anthropic/claude-sonnet-4.5")

    def convert(
        self,
        blueprint: Dict,
        format_name: str,
        account_name: str,
    ) -> Dict:
        """Convert a blueprint into a reusable format template and register it.

        Args:
            blueprint: Blueprint dict (loaded from JSON)
            format_name: Name for the new format (e.g., "before_after")
            account_name: Account to register the format for

        Returns:
            The template dict that was added to content_templates.json
        """
        logger.info(f"Converting blueprint {blueprint.get('blueprint_id')} to template '{format_name}'")

        # Generate the template via LLM
        template = self._generate_template(blueprint, format_name)

        # Register in the account's content_templates.json
        self._register_template(template, format_name, account_name)

        return template

    def _generate_template(self, blueprint: Dict, format_name: str) -> Dict:
        """Use LLM to abstract a blueprint into a reusable template."""
        # Gather blueprint details
        format_analysis = blueprint.get("format_analysis", {})
        visual_analysis = blueprint.get("visual_analysis", {})
        copy_analysis = blueprint.get("visual_copy_analysis") or {}
        caption_analysis = blueprint.get("caption_analysis", {})
        virality = blueprint.get("virality", {})

        slide_count = visual_analysis.get("slide_count", 3)
        post_type = blueprint.get("post_type", "hybrid")

        # Build slide details for context
        slides_context = ""
        slide_structure = format_analysis.get("slide_structure", [])
        if slide_structure:
            for s in slide_structure:
                slides_context += (
                    f"  Slide {s.get('slide_number', '?')}: "
                    f"role={s.get('role', '?')}, "
                    f"template=\"{s.get('text_template', '')}\", "
                    f"words={s.get('word_count', 0)}\n"
                )

        visual_seq = format_analysis.get("visual_sequence", {})
        if visual_seq:
            slides_context += f"  Visual narrative: {visual_seq.get('narrative_arc', '')}\n"
            for i, subj in enumerate(visual_seq.get("subject_progression", []), 1):
                slides_context += f"  Slide {i} visual: {subj}\n"

        # Visual details per slide
        visual_slides = ""
        for s in visual_analysis.get("slides", []):
            ts = s.get("text_styling", {})
            visual_slides += (
                f"  Slide {s.get('slide_number', '?')}: "
                f"layout={s.get('layout', '')}, "
                f"text_position={s.get('text_position', '')}, "
                f"hierarchy={ts.get('text_hierarchy', '')}, "
                f"bg_treatment={ts.get('background_treatment', '')}, "
                f"text_ratio={ts.get('text_to_image_ratio', 0)}\n"
            )

        prompt = f"""You are converting a viral post analysis into a REUSABLE format template.

The template must be ABSTRACT — replace all specific content with {{topic}} placeholders so it can generate posts about ANY topic in the same structural format.

ORIGINAL POST ANALYSIS:
- Format: {format_analysis.get('format_description', 'Unknown')}
- Post type: {post_type}
- Slide count: {slide_count}
- Copy framework: {copy_analysis.get('primary_framework', 'none')}
- Caption framework: {caption_analysis.get('primary_framework', 'none')}
- Caption CTA: {caption_analysis.get('cta_type', 'none')}
- Key virality factors: {json.dumps(virality.get('key_factors', [])[:3])}

SLIDE STRUCTURE:
{slides_context}

VISUAL DETAILS:
{visual_slides}

Return JSON with this EXACT structure:
{{
    "description": "<1-sentence description of this format>",
    "source_blueprint": "{blueprint.get('blueprint_id', '')}",
    "is_cloned_format": true,
    "structure": [
        {{"type": "<hook|content|before|after|cta>", "position": 1, "max_words": <int>, "has_image": true, "has_text_overlay": <true|false>}}
    ],
    "default_slide_count": {slide_count},
    "image_mode": "gemini",
    "caption_strategy": "<describe how caption should work: tease_value, direct_cta, hashtags_only, etc>",
    "prompt_template": "<FULL prompt that Claude will use to generate content in this format. Must include {{topic}} and {{slide_count}} placeholders. Be very specific about slide roles, word counts, text overlay rules, and what NOT to include. This prompt must produce the same JSON slide structure as other formats.>",
    "image_prompts": [
        {{"slide": 1, "template": "<Gemini image generation prompt with {{topic}} placeholder>"}},
        ...one per slide
    ],
    "text_overlay_config": {{
        "hook_style": "<centered|left_aligned|none>",
        "content_style": "<centered|left_aligned|none>",
        "font_size_hook": <int px>,
        "font_size_body": <int px or null>,
        "text_position": "<center|top|bottom>"
    }}
}}

IMPORTANT:
- The prompt_template must instruct Claude to return JSON with: {{"slides": [{{"slide_num": N, "text": "...", "type": "..."}}], "caption": "...", "topic": "..."}}
- Image prompts should be abstract enough to work for any topic in this niche
- Use {{topic}} as placeholder everywhere specific content appeared
- The text_overlay_config should match the original post's visual style"""

        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a content format engineer. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=3000,
            )
            cleaned = self._strip_code_fences(response)
            template = json.loads(cleaned)
            logger.info(f"Template generated: {template.get('description', '')}")
            return template
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Template generation failed: {e}")
            raise RuntimeError(f"Failed to generate template: {e}") from e

    def _register_template(self, template: Dict, format_name: str, account_name: str):
        """Write the template to the account's content_templates.json."""
        templates_path = ACCOUNTS_DIR / account_name / "content_templates.json"

        if templates_path.exists():
            with open(templates_path) as f:
                templates = json.load(f)
        else:
            templates = {"formats": {}}

        # Ensure formats key exists
        if "formats" not in templates:
            templates["formats"] = {}

        # Add the new format
        templates["formats"][format_name] = template

        # Write back
        templates_path.write_text(json.dumps(templates, indent=2, default=str))
        logger.info(f"Registered format '{format_name}' in {templates_path}")

    def _strip_code_fences(self, raw: str) -> str:
        """Strip markdown code fences from LLM response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_newline + 1:last_fence].strip()
        return cleaned
