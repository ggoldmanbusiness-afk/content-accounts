"""
Blueprint Adapter
Maps a saved blueprint + account config into a content brief.
Supports format_clone (exact structure) and inspired_adaptation (looser fit).
"""

import json
import logging
import os
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

ACCOUNTS_DIR = Path(__file__).parent.parent / "accounts"
BLUEPRINTS_DIR = Path(__file__).parent.parent / "blueprints"


class BlueprintAdapter:
    """Adapt viral post blueprints to specific account profiles."""

    def __init__(self, openrouter_key: str = None):
        key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OpenRouter API key required")
        self.llm = LLMClient(api_key=key, model="anthropic/claude-sonnet-4.5")

    def list_accounts(self) -> list:
        """List available account names."""
        accounts = []
        for d in ACCOUNTS_DIR.iterdir():
            if d.is_dir() and (d / "config.py").exists():
                accounts.append(d.name)
        return sorted(accounts)

    def load_account_config(self, account_name: str) -> Dict:
        """
        Load account config.py as a dict of its module-level variables.

        Args:
            account_name: Name of the account directory

        Returns:
            Dict with all config variables
        """
        config_path = ACCOUNTS_DIR / account_name / "config.py"
        if not config_path.exists():
            raise FileNotFoundError(f"Account config not found: {config_path}")

        spec = importlib.util.spec_from_file_location(
            f"accounts.{account_name}.config", config_path
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Extract relevant config variables
        config = {}
        for key in dir(module):
            if key.isupper() and not key.startswith("_"):
                config[key] = getattr(module, key)

        return config

    def adapt(
        self,
        blueprint: Dict,
        account_name: str,
        mode: str = "format_clone",
        topic_hint: str = "",
    ) -> Dict:
        """
        Adapt a blueprint to an account profile.

        Args:
            blueprint: Blueprint dict (from JSON file)
            account_name: Target account name
            mode: "format_clone" or "inspired_adaptation"
            topic_hint: Optional topic suggestion for the adapted content

        Returns:
            Content brief dict
        """
        account_config = self.load_account_config(account_name)
        post_type = blueprint.get("post_type", "text_heavy")

        logger.info(
            f"Adapting blueprint {blueprint.get('blueprint_id', 'unknown')} "
            f"for {account_name} (mode={mode}, post_type={post_type})"
        )

        if mode == "format_clone":
            brief = self._format_clone(blueprint, account_config, topic_hint)
        elif mode == "inspired_adaptation":
            brief = self._inspired_adaptation(blueprint, account_config, topic_hint)
        else:
            raise ValueError(f"Unknown adaptation mode: {mode}")

        # Save brief to account's output directory
        brief_path = self._save_brief(brief, account_config, blueprint)
        brief["saved_to"] = str(brief_path)

        return brief

    def _save_brief(self, brief: Dict, config: Dict, blueprint: Dict) -> Path:
        """Save the content brief to the account's output directory.

        Uses OUTPUT_CONFIG.base_directory from the account config.
        Falls back to blueprints/ if no output config exists.
        """
        output_config = config.get("OUTPUT_CONFIG", {})
        base_dir = output_config.get("base_directory")

        if base_dir:
            # Save to account's Google Drive output folder
            briefs_dir = Path(base_dir) / "briefs"
        else:
            # Fallback to blueprints/ in project root
            briefs_dir = BLUEPRINTS_DIR

        briefs_dir.mkdir(parents=True, exist_ok=True)

        brief_id = brief.get("brief_id", "unknown")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        brief_path = briefs_dir / f"{brief_id}_{timestamp}.json"
        brief_path.write_text(json.dumps(brief, indent=2, default=str))

        logger.info(f"Brief saved to: {brief_path}")
        return brief_path

    def _format_clone(
        self, blueprint: Dict, config: Dict, topic_hint: str
    ) -> Dict:
        """
        Exact structural clone: same slide count, roles, patterns.
        New copy for the account's niche using brand voice.
        """
        post_type = blueprint.get("post_type", "text_heavy")
        brand = config.get("BRAND_IDENTITY", {})
        colors = config.get("COLOR_SCHEMES", [])
        visual_style = config.get("VISUAL_STYLE", {})
        hashtag_strategy = config.get("HASHTAG_STRATEGY", {})
        account_name = config.get("ACCOUNT_NAME", "unknown")

        # Build context for LLM
        context = self._build_context(blueprint, config, topic_hint)

        if post_type in ("text_heavy", "hybrid", "meme_quote"):
            prompt = self._build_text_clone_prompt(blueprint, context)
        elif post_type in ("visual_first", "photo_dump"):
            prompt = self._build_visual_clone_prompt(blueprint, context)
        elif post_type == "infographic":
            prompt = self._build_text_clone_prompt(blueprint, context)
        else:
            prompt = self._build_text_clone_prompt(blueprint, context)

        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": self._system_prompt(brand)},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=3000,
            )
            result = json.loads(self._strip_code_fences(response))
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Format clone failed: {e}")
            result = {"slides": [], "caption": {"text": "", "hashtags": []}}

        return self._build_brief(
            result, blueprint, account_name, "format_clone", colors, visual_style
        )

    def _inspired_adaptation(
        self, blueprint: Dict, config: Dict, topic_hint: str
    ) -> Dict:
        """
        Looser adaptation: extract winning factors, map to account's format.
        """
        brand = config.get("BRAND_IDENTITY", {})
        carousel = config.get("CAROUSEL_STRATEGY", {})
        colors = config.get("COLOR_SCHEMES", [])
        visual_style = config.get("VISUAL_STYLE", {})
        account_name = config.get("ACCOUNT_NAME", "unknown")

        context = self._build_context(blueprint, config, topic_hint)

        # Extract virality factors
        virality = blueprint.get("virality", {})
        key_factors = virality.get("key_factors", [])

        prompt = f"""You are adapting a viral post concept for a different account.

VIRAL POST ANALYSIS:
- Format: {blueprint.get('format_analysis', {}).get('format_description', 'Unknown')}
- Key virality factors: {json.dumps(key_factors)}
- Virality score: {virality.get('virality_score', 0)}/100
- Replicability notes: {virality.get('replicability_notes', '')}

{context}

TARGET ACCOUNT FORMAT:
- Preferred format: {carousel.get('format', 'habit_list')}
- Default slide count: {carousel.get('default_slide_count', 7)}
- CTA focus: {carousel.get('cta_focus', 'save_this')}
- Caption style: {carousel.get('caption_style', 'hashtags_only')}

Create an INSPIRED ADAPTATION that captures what made the original viral but fits naturally into the target account's style. You have creative freedom to:
- Change slide count to match account preference
- Adjust the format to the account's usual style
- Reinterpret the concept for the account's niche

Return JSON:
{{
    "slides": [
        {{"slide_number": 1, "role": "hook", "copy": "<text>", "visual_direction": "<description>"}}
    ],
    "caption": {{
        "text": "<caption text>",
        "hashtags": ["tag1", "tag2"]
    }},
    "adaptation_notes": "<how this captures the original's viral factors>"
}}"""

        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": self._system_prompt(brand)},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=3000,
            )
            result = json.loads(self._strip_code_fences(response))
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Inspired adaptation failed: {e}")
            result = {"slides": [], "caption": {"text": "", "hashtags": []}}

        return self._build_brief(
            result, blueprint, account_name, "inspired_adaptation", colors, visual_style
        )

    def _build_context(self, blueprint: Dict, config: Dict, topic_hint: str) -> str:
        """Build shared context block for LLM prompts."""
        brand = config.get("BRAND_IDENTITY", {})
        pillars = config.get("CONTENT_PILLARS", [])
        hashtag_strategy = config.get("HASHTAG_STRATEGY", {})

        # Original post info
        visual = blueprint.get("visual_analysis", {})
        format_info = blueprint.get("format_analysis", {})
        caption_analysis = blueprint.get("caption_analysis", {})

        # Slide details from original
        slides_text = ""
        slide_structure = format_info.get("slide_structure")
        if slide_structure:
            for s in slide_structure:
                slides_text += (
                    f"  Slide {s.get('slide_number', '?')}: "
                    f"[{s.get('role', '?')}] template: \"{s.get('text_template', '')}\" "
                    f"({s.get('word_count', 0)} words)\n"
                )

        visual_seq = format_info.get("visual_sequence")
        if visual_seq:
            slides_text += f"  Visual narrative: {visual_seq.get('narrative_arc', '')}\n"
            for i, subj in enumerate(visual_seq.get("subject_progression", []), 1):
                slides_text += f"  Slide {i}: {subj}\n"

        topic_line = f"\nSUGGESTED TOPIC: {topic_hint}" if topic_hint else ""

        return f"""ORIGINAL POST:
- Author: @{blueprint.get('source_author', 'unknown')}
- Format: {format_info.get('format_description', 'Unknown')}
- Slide count: {visual.get('slide_count', 0)}
- Caption framework: {caption_analysis.get('primary_framework', 'none')}
- Original caption: "{caption_analysis.get('original_caption', '')[:200]}"
{slides_text}
TARGET ACCOUNT:
- Name: {config.get('DISPLAY_NAME', config.get('ACCOUNT_NAME', 'unknown'))}
- Personality: {brand.get('personality', '')}
- Value proposition: {brand.get('value_proposition', '')}
- Voice: {', '.join(brand.get('voice_attributes', []))}
- Content pillars: {', '.join(pillars[:10])}
- Hashtags: {', '.join(hashtag_strategy.get('primary', []))}
- Max hashtags: {hashtag_strategy.get('max_per_post', 4)}{topic_line}"""

    def _build_text_clone_prompt(self, blueprint: Dict, context: str) -> str:
        """Build prompt for cloning text-heavy/hybrid posts."""
        format_info = blueprint.get("format_analysis", {})
        slide_structure = format_info.get("slide_structure", [])
        copy_analysis = blueprint.get("visual_copy_analysis") or {}
        caption_analysis = blueprint.get("caption_analysis", {})

        slides_spec = ""
        for s in slide_structure:
            slides_spec += (
                f"  Slide {s.get('slide_number', '?')}: "
                f"role={s.get('role', '?')}, "
                f"pattern={s.get('pattern', '?')}, "
                f"template=\"{s.get('text_template', '')}\", "
                f"target_words={s.get('word_count', 0)}\n"
            )

        return f"""Clone this viral post's EXACT format for the target account.
Keep the same slide count, roles, and text patterns. Generate NEW copy for the target niche.

{context}

EXACT SLIDE STRUCTURE TO CLONE:
{slides_spec}

COPY APPROACH TO REPLICATE:
- Framework: {copy_analysis.get('primary_framework', 'none')}
- Techniques: {', '.join(copy_analysis.get('copy_techniques', []))}
- Tone: {copy_analysis.get('tone', 'conversational')}

CAPTION APPROACH:
- Framework: {caption_analysis.get('primary_framework', 'none')}
- Hook technique: {caption_analysis.get('hook_technique', 'none')}
- CTA type: {caption_analysis.get('cta_type', 'save')}

Return JSON:
{{
    "slides": [
        {{"slide_number": 1, "role": "<same role>", "copy": "<new text matching template pattern and word count>", "visual_direction": "<what this slide should look like>"}}
    ],
    "caption": {{
        "text": "<new caption using same framework/technique>",
        "hashtags": ["<relevant hashtags from account strategy>"]
    }}
}}"""

    def _build_visual_clone_prompt(self, blueprint: Dict, context: str) -> str:
        """Build prompt for cloning visual-first/photo dump posts."""
        format_info = blueprint.get("format_analysis", {})
        visual_seq = format_info.get("visual_sequence", {})
        visual = blueprint.get("visual_analysis", {})

        subjects = ""
        for slide in visual.get("slides", []):
            subjects += (
                f"  Slide {slide.get('slide_number', '?')}: "
                f"{slide.get('visual_description', '')} "
                f"(mood: {slide.get('mood', 'unknown')})\n"
            )

        return f"""Clone this viral visual post's concept for the target account.
Keep the same slide count and visual storytelling approach. Describe what EACH slide should show for the target niche.

{context}

ORIGINAL VISUAL SEQUENCE:
- Narrative arc: {visual_seq.get('narrative_arc', 'unknown')}
- Curation strategy: {visual_seq.get('curation_strategy', 'unknown')}
{subjects}

Return JSON:
{{
    "slides": [
        {{"slide_number": 1, "role": "<slide role>", "copy": "<text overlay if any, empty string if visual-only>", "visual_direction": "<detailed description of what this slide should show>"}}
    ],
    "caption": {{
        "text": "<new caption for target account>",
        "hashtags": ["<relevant hashtags>"]
    }}
}}"""

    def _system_prompt(self, brand: Dict) -> str:
        voice = ", ".join(brand.get("voice_attributes", []))
        return (
            f"You are a social media content strategist writing for a {brand.get('character_type', 'brand')}. "
            f"Brand voice: {voice}. "
            f"Personality: {brand.get('personality', '')}. "
            "Write copy that sounds natural and human, never generic or AI-generated. "
            "Return valid JSON only."
        )

    def _build_brief(
        self,
        llm_result: Dict,
        blueprint: Dict,
        account_name: str,
        mode: str,
        colors: list,
        visual_style: Dict,
    ) -> Dict:
        """Assemble the final content brief dict."""
        slides = []
        for s in llm_result.get("slides", []):
            slides.append({
                "slide_number": s.get("slide_number", 0),
                "role": s.get("role", ""),
                "copy": s.get("copy", ""),
                "visual_direction": s.get("visual_direction", ""),
                "layout": visual_style.get("slide_layout", ""),
                "word_count_target": len(s.get("copy", "").split()),
            })

        caption_data = llm_result.get("caption", {})

        # Map colors
        primary_color = colors[0] if colors else {"bg": "#1E3A5F", "text": "#FFFFFF"}

        return {
            "brief_id": f"{blueprint.get('blueprint_id', 'unknown')}_{account_name}",
            "source_blueprint_id": blueprint.get("blueprint_id", ""),
            "target_account": account_name,
            "adaptation_mode": mode,
            "slides": slides,
            "caption": {
                "text": caption_data.get("text", ""),
                "hashtags": caption_data.get("hashtags", []),
            },
            "visual_direction": {
                "color_palette": [c.get("bg", "") for c in colors[:3]],
                "text_color": primary_color.get("text", "#FFFFFF"),
                "font_style": visual_style.get("font_style", "clean_sans_serif"),
                "aesthetic": visual_style.get("mode", "text_only_slides"),
            },
            "generation_notes": llm_result.get("adaptation_notes", ""),
        }

    def _strip_code_fences(self, raw: str) -> str:
        """Strip markdown code fences from LLM response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_newline + 1:last_fence].strip()
        return cleaned
