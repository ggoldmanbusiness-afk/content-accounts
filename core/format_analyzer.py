"""
Adaptive Format Analyzer
Discovers post format rather than classifying into pre-defined buckets.
Adapts analysis depth based on post_type from visual analysis.
"""

import json
import logging
import os
from typing import Dict, Optional

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)


class FormatAnalyzer:
    """Discovers format structure adaptively based on visual analysis post_type."""

    def __init__(self, openrouter_key: str = None):
        """Initialize using LLMClient from core.llm_client."""
        api_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key required (pass directly or set OPENROUTER_API_KEY)")
        self.llm = LLMClient(api_key=api_key)
        logger.info("FormatAnalyzer initialized")

    def analyze_format(self, visual_analysis: dict, caption: str, metrics: dict) -> dict:
        """
        Main entry point. Adapts analysis based on visual_analysis["post_type"].

        Args:
            visual_analysis: Output from visual analyzer (post_type, slides, text_overlays, etc.)
            caption: Post caption text
            metrics: Engagement metrics dict

        Returns:
            Format analysis dict with flexible fields based on post type.
        """
        post_type = visual_analysis.get("post_type", "hybrid")
        logger.info(f"Analyzing format for post_type: {post_type}")

        prompt_builders = {
            "text_heavy": self._build_text_heavy_prompt,
            "visual_first": self._build_visual_first_prompt,
            "photo_dump": self._build_visual_first_prompt,
            "hybrid": self._build_hybrid_prompt,
            "meme_quote": self._build_meme_prompt,
            "infographic": self._build_infographic_prompt,
        }

        builder = prompt_builders.get(post_type, self._build_hybrid_prompt)
        prompt = builder(visual_analysis, caption, metrics)

        messages = [
            {"role": "system", "content": "You are a content format analyst. Respond ONLY with valid JSON. No markdown, no explanation."},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self.llm.chat_completion(messages, temperature=0.3, max_tokens=2000)
            result = self._parse_response(raw, post_type)
            logger.info(f"Format analysis complete for post_type: {post_type}")
            return result
        except Exception as e:
            logger.error(f"Format analysis failed: {e}")
            return self._empty_result(post_type)

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_text_heavy_prompt(self, visual_analysis: dict, caption: str, metrics: dict) -> str:
        """Full slide role analysis with text templates, information flow, word counts."""
        context = self._format_visual_context(visual_analysis, caption, metrics)
        return f"""{context}

This is a TEXT-HEAVY post (carousel/slides with significant text overlays). Analyze the format deeply.

Return JSON with this structure:
{{
    "format_description": "<free-form description, e.g. '7-slide listicle with numbered tips'>",
    "slide_structure": [
        {{
            "slide_number": 1,
            "role": "<hook|content|example|transition|cta|intro|summary>",
            "pattern": "<number_promise|question|bold_claim|list_item|story_beat|tip|stat|testimonial|before_after>",
            "text_template": "<abstracted template, e.g. '[N] [topic] that [outcome]'>",
            "word_count": <approximate words on this slide>
        }}
    ],
    "information_architecture": {{
        "flow": "<sequence description, e.g. 'hook -> numbered_tips -> cta'>",
        "pacing": "<even|front_loaded|back_loaded|variable>",
        "content_density": "<low|medium|high>",
        "where_value_lives": "<slides|caption|both>"
    }}
}}

Be specific about each slide's role and the abstracted text template. The template should replace specifics with placeholders like [N], [topic], [outcome], [benefit]."""

    def _build_visual_first_prompt(self, visual_analysis: dict, caption: str, metrics: dict) -> str:
        """Visual sequence analysis: narrative arc, subject progression, curation strategy."""
        context = self._format_visual_context(visual_analysis, caption, metrics)
        return f"""{context}

This is a VISUAL-FIRST post (photos/images are the primary content). Analyze the visual format.

Return JSON with this structure:
{{
    "format_description": "<free-form description, e.g. 'photo dump of 5 travel shots with warm editing'>",
    "visual_sequence": {{
        "narrative_arc": "<describe how the visual story opens, develops, and closes>",
        "subject_progression": ["<what slide/image 1 shows>", "<what slide/image 2 shows>", "..."],
        "curation_strategy": "<why these images work together, what makes the selection compelling>"
    }},
    "information_architecture": {{
        "flow": "<sequence description>",
        "pacing": "<even|front_loaded|back_loaded|variable>",
        "content_density": "<low|medium|high>",
        "where_value_lives": "<slides|caption|both>"
    }}
}}

Focus on the visual storytelling: how images are sequenced, what makes the curation effective, and the narrative arc across the set."""

    def _build_hybrid_prompt(self, visual_analysis: dict, caption: str, metrics: dict) -> str:
        """Both visual and text analysis at moderate depth."""
        context = self._format_visual_context(visual_analysis, caption, metrics)
        return f"""{context}

This is a HYBRID post (mix of meaningful visuals and text overlays). Analyze both dimensions at moderate depth.

Return JSON with this structure:
{{
    "format_description": "<free-form description>",
    "slide_structure": [
        {{
            "slide_number": 1,
            "role": "<hook|content|example|transition|cta|intro|summary>",
            "pattern": "<number_promise|question|bold_claim|list_item|story_beat|tip|stat>",
            "text_template": "<abstracted template>",
            "word_count": <approximate words>
        }}
    ],
    "visual_sequence": {{
        "narrative_arc": "<how visuals support the text narrative>",
        "subject_progression": ["<what each slide shows visually>"],
        "curation_strategy": "<how visuals and text work together>"
    }},
    "information_architecture": {{
        "flow": "<sequence description>",
        "pacing": "<even|front_loaded|back_loaded|variable>",
        "content_density": "<low|medium|high>",
        "where_value_lives": "<slides|caption|both>"
    }}
}}

Analyze how text and visuals complement each other across the post."""

    def _build_meme_prompt(self, visual_analysis: dict, caption: str, metrics: dict) -> str:
        """Template identification, emotional technique, humor type."""
        context = self._format_visual_context(visual_analysis, caption, metrics)
        return f"""{context}

This is a MEME/QUOTE post. Analyze the template structure and emotional technique.

Return JSON with this structure:
{{
    "format_description": "<free-form description, e.g. 'relatable quote on gradient background'>",
    "template_structure": {{
        "template_type": "<reaction_meme|text_quote|image_macro|screenshot|comparison|starter_pack>",
        "emotional_technique": "<relatability|shock|irony|absurdity|nostalgia|aspiration|frustration>",
        "humor_type": "<observational|self_deprecating|absurd|sarcasm|wordplay|none>",
        "text_template": "<abstracted template of the meme/quote format>"
    }},
    "information_architecture": {{
        "flow": "<how the joke/message lands>",
        "pacing": "<setup_punchline|immediate|slow_build>",
        "content_density": "<low|medium|high>",
        "where_value_lives": "<slides|caption|both>"
    }}
}}

Focus on what makes this meme/quote format effective and how the template could be reused."""

    def _build_infographic_prompt(self, visual_analysis: dict, caption: str, metrics: dict) -> str:
        """Data presentation strategy, visual hierarchy, information design."""
        context = self._format_visual_context(visual_analysis, caption, metrics)
        return f"""{context}

This is an INFOGRAPHIC post. Analyze the data presentation and information design.

Return JSON with this structure:
{{
    "format_description": "<free-form description, e.g. 'step-by-step process infographic with icons'>",
    "slide_structure": [
        {{
            "slide_number": 1,
            "role": "<title|data_point|comparison|process_step|summary|cta>",
            "pattern": "<chart|list|icons|numbers|diagram|table|timeline>",
            "text_template": "<abstracted template>",
            "word_count": <approximate words>
        }}
    ],
    "data_presentation": {{
        "visual_hierarchy": "<how information is prioritized visually>",
        "data_types": ["<statistics|comparisons|processes|lists|timelines>"],
        "design_strategy": "<how data is made digestible>"
    }},
    "information_architecture": {{
        "flow": "<sequence description>",
        "pacing": "<even|front_loaded|back_loaded|variable>",
        "content_density": "<low|medium|high>",
        "where_value_lives": "<slides|caption|both>"
    }}
}}

Focus on how information is structured, visualized, and made digestible."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_visual_context(self, visual_analysis: dict, caption: str, metrics: dict) -> str:
        """Build context string from visual analysis, caption, and metrics."""
        parts = ["=== POST CONTEXT ==="]

        # Visual analysis details
        parts.append(f"\nPost type: {visual_analysis.get('post_type', 'unknown')}")
        parts.append(f"Slide count: {visual_analysis.get('slide_count', 'unknown')}")
        parts.append(f"Text density: {visual_analysis.get('text_density', 'unknown')}")

        # Slide details
        slides = visual_analysis.get("slides", [])
        if slides:
            parts.append("\n--- Slide Details ---")
            for slide in slides:
                slide_num = slide.get("slide_number", "?")
                parts.append(f"\nSlide {slide_num}:")
                if slide.get("visual_description"):
                    parts.append(f"  Visual: {slide['visual_description']}")
                overlays = slide.get("text_overlays", [])
                if overlays:
                    parts.append(f"  Text overlays: {' | '.join(overlays)}")

        # All text overlays summary from slides
        all_overlays = []
        for slide in slides:
            all_overlays.extend(slide.get("text_overlays", []))
        if all_overlays:
            parts.append("\n--- All Text Overlays ---")
            for i, overlay in enumerate(all_overlays, 1):
                parts.append(f"  {i}. {overlay}")

        # Caption
        if caption:
            parts.append(f"\n--- Caption ---\n{caption}")

        # Metrics
        if metrics:
            parts.append("\n--- Engagement Metrics ---")
            for key, val in metrics.items():
                parts.append(f"  {key}: {val}")

        return "\n".join(parts)

    def _parse_response(self, raw: str, post_type: str) -> dict:
        """Parse LLM JSON response, handling common formatting issues."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_newline + 1:last_fence].strip()

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed: {e}. Raw response: {raw[:500]}")
            return self._empty_result(post_type)

        # Ensure information_architecture exists
        if "information_architecture" not in parsed:
            parsed["information_architecture"] = {
                "flow": "unknown",
                "pacing": "unknown",
                "content_density": "unknown",
                "where_value_lives": "unknown",
            }

        # Null out fields that don't apply
        if post_type in ("visual_first", "photo_dump"):
            parsed.setdefault("slide_structure", None)
        elif post_type == "text_heavy":
            parsed.setdefault("visual_sequence", None)

        return parsed

    def _empty_result(self, post_type: str) -> dict:
        """Return a safe empty result on failure."""
        result = {
            "format_description": "Analysis failed",
            "slide_structure": None,
            "visual_sequence": None,
            "information_architecture": {
                "flow": "unknown",
                "pacing": "unknown",
                "content_density": "unknown",
                "where_value_lives": "unknown",
            },
        }
        return result
