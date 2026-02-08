"""
Adaptive Copy Analyzer
Analyzes copywriting frameworks and techniques in both visual text and captions.
Adapts depth based on text_density from visual analysis.
"""

import json
import logging
import os
from typing import Dict, Optional

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

# The 7 copywriting frameworks
FRAMEWORKS = [
    "PAS",   # Problem -> Agitate -> Solution
    "AIDA",  # Attention -> Interest -> Desire -> Action
    "BAB",   # Before -> After -> Bridge
    "FAB",   # Features -> Advantages -> Benefits
    "4Ps",   # Promise -> Picture -> Proof -> Push
    "SCQA",  # Situation -> Complication -> Question -> Answer
    "4Cs",   # Clear -> Concise -> Compelling -> Credible (quality checklist)
]


class CopyAnalyzer:
    """Analyzes copy using copywriting frameworks. Adapts depth based on text_density."""

    def __init__(self, openrouter_key: str = None):
        """Initialize using LLMClient."""
        api_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OpenRouter API key required (pass directly or set OPENROUTER_API_KEY)")
        self.llm = LLMClient(api_key=api_key)
        logger.info("CopyAnalyzer initialized")

    def analyze_copy(self, visual_analysis: dict, caption: str) -> dict:
        """
        Single entry point. Adapts analysis based on text_density.

        Args:
            visual_analysis: Output from visual analyzer (text_density, text_overlays, slides, etc.)
            caption: Post caption text

        Returns:
            Copy analysis dict with visual_copy and caption sections.
        """
        text_density = visual_analysis.get("text_density", "none")
        logger.info(f"Analyzing copy with text_density: {text_density}")

        result = {
            "visual_copy": None,
            "caption": None,
        }

        # Visual copy analysis — depth based on text_density
        if text_density == "high":
            result["visual_copy"] = self._analyze_visual_copy(visual_analysis, depth="full")
        elif text_density == "medium":
            result["visual_copy"] = self._analyze_visual_copy(visual_analysis, depth="moderate")
        # low/none: skip visual copy analysis entirely

        # Caption analysis — always run, deeper when visual copy is skipped
        caption_depth = "deep" if text_density in ("low", "none") else "full" if text_density == "high" else "full"
        result["caption"] = self._analyze_caption(caption, caption_depth)

        logger.info("Copy analysis complete")
        return result

    # ------------------------------------------------------------------
    # Visual copy analysis
    # ------------------------------------------------------------------

    def _analyze_visual_copy(self, visual_analysis: dict, depth: str = "full") -> Optional[dict]:
        """Analyze copywriting in slide text overlays."""
        text_overlays = self._extract_text_overlays(visual_analysis)
        if not text_overlays:
            logger.info("No text overlays found, skipping visual copy analysis")
            return None

        prompt = self._build_visual_copy_prompt(text_overlays, depth)
        messages = [
            {"role": "system", "content": "You are a copywriting analyst. Respond ONLY with valid JSON. No markdown, no explanation."},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self.llm.chat_completion(messages, temperature=0.3, max_tokens=1500)
            return self._parse_visual_copy_response(raw)
        except Exception as e:
            logger.error(f"Visual copy analysis failed: {e}")
            return None

    def _build_visual_copy_prompt(self, text_overlays: list, depth: str) -> str:
        """Build prompt for visual copy analysis."""
        overlay_text = "\n".join(f"  Slide {i+1}: {t}" for i, t in enumerate(text_overlays))

        depth_instruction = ""
        if depth == "full":
            depth_instruction = "Perform a THOROUGH analysis. Identify per-slide techniques and the overall framework."
        else:
            depth_instruction = "Perform a MODERATE analysis. Focus on the overall framework and key techniques."

        frameworks_desc = """The 7 copywriting frameworks to consider:
1. PAS (Problem -> Agitate -> Solution) - short-form, emotional
2. AIDA (Attention -> Interest -> Desire -> Action) - long-form
3. BAB (Before -> After -> Bridge) - transformation-focused
4. FAB (Features -> Advantages -> Benefits) - product descriptions
5. 4Ps (Promise -> Picture -> Proof -> Push) - sales-heavy
6. SCQA (Situation -> Complication -> Question -> Answer) - B2B/LinkedIn
7. 4Cs (Clear -> Concise -> Compelling -> Credible) - quality checklist"""

        return f"""Analyze the copywriting in these slide text overlays:

{overlay_text}

{frameworks_desc}

{depth_instruction}

Return JSON with this structure:
{{
    "primary_framework": "<PAS|AIDA|BAB|FAB|4Ps|SCQA|4Cs|null if none/custom>",
    "framework_confidence": <0.0-1.0>,
    "tone": "<conversational|authoritative|emotional|humorous|professional|casual>",
    "copy_techniques": ["<curiosity_gap|social_proof|specificity|urgency|emotional_trigger|number_promise|question_hook|bold_claim|scarcity|authority|storytelling|contrast>"],
    "power_words": ["<specific impactful words used in the copy>"]
}}

Be precise about which techniques are actually present. Only list power words that genuinely carry emotional weight."""

    def _parse_visual_copy_response(self, raw: str) -> Optional[dict]:
        """Parse the visual copy LLM response."""
        cleaned = self._strip_code_fences(raw)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Visual copy JSON parse failed: {e}. Raw: {raw[:500]}")
            return None

        # Normalize fields
        parsed.setdefault("primary_framework", None)
        parsed.setdefault("framework_confidence", 0.0)
        parsed.setdefault("tone", "unknown")
        parsed.setdefault("copy_techniques", [])
        parsed.setdefault("power_words", [])

        # Validate framework
        if parsed["primary_framework"] and parsed["primary_framework"] not in FRAMEWORKS:
            logger.warning(f"Unknown framework '{parsed['primary_framework']}', setting to None")
            parsed["primary_framework"] = None

        return parsed

    # ------------------------------------------------------------------
    # Caption analysis
    # ------------------------------------------------------------------

    def _analyze_caption(self, caption: str, depth: str) -> dict:
        """Analyze copywriting in the caption."""
        if not caption or not caption.strip():
            logger.info("Empty caption, returning defaults")
            return self._empty_caption_result("")

        prompt = self._build_caption_prompt(caption, depth)
        messages = [
            {"role": "system", "content": "You are a copywriting analyst. Respond ONLY with valid JSON. No markdown, no explanation."},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = self.llm.chat_completion(messages, temperature=0.3, max_tokens=1500)
            result = self._parse_caption_response(raw)
            result["original_caption"] = caption
            return result
        except Exception as e:
            logger.error(f"Caption analysis failed: {e}")
            return self._empty_caption_result(caption)

    def _build_caption_prompt(self, caption: str, depth: str) -> str:
        """Build prompt for caption analysis."""
        frameworks_desc = """The 7 copywriting frameworks:
1. PAS (Problem -> Agitate -> Solution)
2. AIDA (Attention -> Interest -> Desire -> Action)
3. BAB (Before -> After -> Bridge)
4. FAB (Features -> Advantages -> Benefits)
5. 4Ps (Promise -> Picture -> Proof -> Push)
6. SCQA (Situation -> Complication -> Question -> Answer)
7. 4Cs (Clear -> Concise -> Compelling -> Credible)"""

        depth_instruction = ""
        if depth == "deep":
            depth_instruction = "This is the PRIMARY text content for this post (minimal visual text). Perform an EXHAUSTIVE caption analysis."
        else:
            depth_instruction = "Analyze this caption thoroughly."

        return f"""Analyze this Instagram/social media caption:

---
{caption}
---

{frameworks_desc}

{depth_instruction}

Return JSON with this structure:
{{
    "primary_framework": "<PAS|AIDA|BAB|FAB|4Ps|SCQA|4Cs|null if none/custom>",
    "hook_technique": "<question|bold_claim|story_opener|soft_command|statistic|none>",
    "cta_type": "<save|follow|comment|share|link|none>",
    "hashtag_strategy": "<none|minimal|moderate|heavy>",
    "hashtag_count": <integer count of hashtags>,
    "caption_length": "<micro|short|medium|long>",
    "tone": "<conversational|authoritative|emotional|humorous|professional|casual>"
}}

Caption length guide: micro (<20 words), short (20-50), medium (50-150), long (150+). Count only caption words, not hashtags.
Hashtag strategy: none (0), minimal (1-5), moderate (6-15), heavy (16+)."""

    def _parse_caption_response(self, raw: str) -> dict:
        """Parse the caption LLM response."""
        cleaned = self._strip_code_fences(raw)
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning(f"Caption JSON parse failed: {e}. Raw: {raw[:500]}")
            return self._empty_caption_result("")

        # Normalize fields
        parsed.setdefault("primary_framework", None)
        parsed.setdefault("hook_technique", "none")
        parsed.setdefault("cta_type", "none")
        parsed.setdefault("hashtag_strategy", "none")
        parsed.setdefault("hashtag_count", 0)
        parsed.setdefault("caption_length", "unknown")
        parsed.setdefault("tone", "unknown")

        # Validate framework
        if parsed["primary_framework"] and parsed["primary_framework"] not in FRAMEWORKS:
            logger.warning(f"Unknown caption framework '{parsed['primary_framework']}', setting to None")
            parsed["primary_framework"] = None

        return parsed

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _extract_text_overlays(self, visual_analysis: dict) -> list:
        """Extract text overlays from visual analysis slides.

        Each slide has a text_overlays list. We join each slide's overlays
        into a single string per slide for copy analysis.
        """
        slides = visual_analysis.get("slides", [])
        result = []
        for slide in slides:
            # text_overlays is a list of strings per slide
            overlays = slide.get("text_overlays", [])
            if overlays:
                combined = " ".join(overlays)
                result.append(combined)
        return result

    def _strip_code_fences(self, raw: str) -> str:
        """Strip markdown code fences from LLM response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_newline + 1:last_fence].strip()
        return cleaned

    def _empty_caption_result(self, caption: str) -> dict:
        """Safe empty caption result."""
        return {
            "original_caption": caption,
            "primary_framework": None,
            "hook_technique": "none",
            "cta_type": "none",
            "hashtag_strategy": "none",
            "hashtag_count": 0,
            "caption_length": "unknown",
            "tone": "unknown",
        }
