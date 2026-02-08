"""
Virality Analyzer
Synthesizes all analyses into a "why it went viral" explanation.
"""

import json
import logging
import os
from typing import Dict

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)


class ViralityAnalyzer:
    """Synthesize format, visual, and copy analyses into virality insights."""

    def __init__(self, openrouter_key: str = None):
        key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OpenRouter API key required")
        self.llm = LLMClient(api_key=key, model="anthropic/claude-sonnet-4.5")

    def analyze_virality(
        self,
        metrics: Dict,
        format_analysis: Dict,
        visual_analysis: Dict,
        copy_analysis: Dict,
    ) -> Dict:
        """
        Synthesize all analyses into virality insights.

        Args:
            metrics: Post engagement metrics
            format_analysis: Output from FormatAnalyzer
            visual_analysis: Output from VisualAnalyzer
            copy_analysis: Output from CopyAnalyzer (visual_copy + caption)

        Returns:
            Dict matching ViralityInsight schema
        """
        prompt = self._build_prompt(metrics, format_analysis, visual_analysis, copy_analysis)

        try:
            response = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a viral content strategist. Analyze why content performs well on social media. Return valid JSON only."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            cleaned = self._strip_code_fences(response)
            result = json.loads(cleaned)
            return self._normalize_result(result)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse virality analysis JSON. Raw: {response[:500]}")
            return self._empty_result()
        except Exception as e:
            logger.error(f"Virality analysis failed: {e}")
            return self._empty_result()

    def _build_prompt(
        self,
        metrics: Dict,
        format_analysis: Dict,
        visual_analysis: Dict,
        copy_analysis: Dict,
    ) -> str:
        # Build metrics summary
        m = metrics
        metrics_text = (
            f"Views: {m.get('views', 0):,} | Likes: {m.get('likes', 0):,} | "
            f"Comments: {m.get('comments', 0):,} | Shares: {m.get('shares', 0):,} | "
            f"Engagement rate: {m.get('engagement_rate', 0):.2f}%"
        )

        # Build format summary
        format_desc = format_analysis.get("format_description", "Unknown format")
        info_arch = format_analysis.get("information_architecture", {})
        flow = info_arch.get("flow", "unknown")
        where_value = info_arch.get("where_value_lives", "unknown")

        # Build visual summary
        post_type = visual_analysis.get("post_type", "unknown")
        text_density = visual_analysis.get("text_density", "unknown")
        style = visual_analysis.get("overall_visual_style", {})
        aesthetic = style.get("aesthetic", "unknown")

        # Build copy summary
        visual_copy = copy_analysis.get("visual_copy") or {}
        caption_data = copy_analysis.get("caption", {})
        visual_framework = visual_copy.get("primary_framework", "none")
        caption_framework = caption_data.get("primary_framework", "none")
        copy_techniques = visual_copy.get("copy_techniques", [])
        caption_cta = caption_data.get("cta_type", "none")

        return f"""Analyze why this social media post went viral. Consider all dimensions.

METRICS:
{metrics_text}

FORMAT:
- Description: {format_desc}
- Information flow: {flow}
- Where value lives: {where_value}
- Post type: {post_type}

VISUAL STYLE:
- Aesthetic: {aesthetic}
- Text density: {text_density}
- Visual narrative: {style.get('visual_narrative', 'N/A')}
- Consistency: {style.get('consistency', 'N/A')}

COPY APPROACH:
- Visual copy framework: {visual_framework}
- Caption framework: {caption_framework}
- Copy techniques: {', '.join(copy_techniques) if copy_techniques else 'N/A'}
- CTA type: {caption_cta}
- Caption tone: {caption_data.get('tone', 'N/A')}

Return JSON:
{{
    "virality_score": <0-100 composite score based on engagement + format + replicability>,
    "key_factors": ["<3-6 specific reasons this went viral, each 1 sentence>"],
    "format_contribution": "<how the format/structure helped performance>",
    "visual_contribution": "<how the visual style/aesthetic helped performance>",
    "copy_contribution": "<how the copywriting approach helped performance>",
    "replicability": "high|medium|low",
    "replicability_notes": "<what's easy vs hard to replicate about this post>"
}}"""

    def _normalize_result(self, result: Dict) -> Dict:
        return {
            "virality_score": min(100, max(0, result.get("virality_score", 0))),
            "key_factors": result.get("key_factors", [])[:6],
            "format_contribution": result.get("format_contribution", ""),
            "visual_contribution": result.get("visual_contribution", ""),
            "copy_contribution": result.get("copy_contribution", ""),
            "replicability": result.get("replicability", "medium"),
            "replicability_notes": result.get("replicability_notes", ""),
        }

    def _strip_code_fences(self, raw: str) -> str:
        """Strip markdown code fences from LLM response."""
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n")
            last_fence = cleaned.rfind("```")
            cleaned = cleaned[first_newline + 1:last_fence].strip()
        return cleaned

    def _empty_result(self) -> Dict:
        return {
            "virality_score": 0,
            "key_factors": [],
            "format_contribution": "",
            "visual_contribution": "",
            "copy_contribution": "",
            "replicability": "unknown",
            "replicability_notes": "",
        }
