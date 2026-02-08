"""
Visual Analyzer module.

Downloads images from scraped posts and analyzes them with GPT-4o via OpenRouter.
Classifies post type and extracts visual details per slide.
"""

import base64
import json
import logging
import os
from typing import Optional

import httpx
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)

MAX_IMAGES = 10


class VisualAnalyzer:
    """Analyzes post images with GPT-4o to classify post type and extract visual details."""

    def __init__(self, openrouter_key: str = None):
        """Initialize OpenRouter client.

        Args:
            openrouter_key: OpenRouter API key. Falls back to OPENROUTER_API_KEY env var.
        """
        self.api_key = openrouter_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Pass openrouter_key or set OPENROUTER_API_KEY."
            )

        http_client = httpx.Client(timeout=60.0, follow_redirects=True)
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
            http_client=http_client,
        )

    def analyze_post(self, image_urls: list, caption: str) -> dict:
        """Main entry: download images, analyze with GPT-4o, classify post type.

        Handles both carousel (multiple images) and single image posts.
        Caps at MAX_IMAGES images.

        Args:
            image_urls: List of image URLs to analyze.
            caption: The post caption text.

        Returns:
            Dict matching the VisualAnalysisResult schema structure.
        """
        if not image_urls:
            logger.warning("No image URLs provided, returning empty analysis")
            return self._empty_result()

        # Cap carousel size
        urls_to_process = image_urls[:MAX_IMAGES]
        if len(image_urls) > MAX_IMAGES:
            logger.info(
                "Capping image count from %d to %d", len(image_urls), MAX_IMAGES
            )

        # Download all images
        images_base64 = []
        for url in urls_to_process:
            img_data = self._download_image(url)
            if img_data:
                img_b64 = base64.b64encode(img_data).decode("utf-8")
                images_base64.append(img_b64)
            else:
                logger.warning("Failed to download image: %s", url)

        if not images_base64:
            logger.error("No images downloaded successfully")
            return self._empty_result()

        logger.info(
            "Downloaded %d/%d images, sending to GPT-4o",
            len(images_base64),
            len(urls_to_process),
        )

        # Analyze with GPT-4o
        result = self._analyze_with_gpt4o(images_base64, caption)
        return result

    def _download_image(self, url: str) -> Optional[bytes]:
        """Download image bytes from URL.

        Args:
            url: Image URL to download.

        Returns:
            Raw image bytes, or None on failure.
        """
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error("Image download failed for %s: %s", url, e)
            return None

    def _analyze_with_gpt4o(self, images_base64: list, caption: str) -> dict:
        """Send images to GPT-4o for analysis.

        Args:
            images_base64: List of base64-encoded image strings.
            caption: The post caption text.

        Returns:
            Analysis dict matching VisualAnalysisResult schema.
        """
        prompt_text = self._build_analysis_prompt(caption, len(images_base64))

        # Build content array: prompt text + all images
        content = [{"type": "text", "text": prompt_text}]
        for img_b64 in images_base64:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                }
            )

        try:
            response = self.client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": content}],
                response_format={"type": "json_object"},
                max_tokens=4000,
            )
            raw = response.choices[0].message.content
            result = json.loads(raw)
            logger.info("GPT-4o analysis complete, post_type=%s", result.get("post_type"))
            return self._normalize_result(result)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse GPT-4o JSON response: %s", e)
            return self._empty_result()
        except Exception as e:
            logger.error("GPT-4o analysis failed: %s", e)
            return self._empty_result()

    def _build_analysis_prompt(self, caption: str, num_images: int) -> str:
        """Build the GPT-4o prompt for format-focused visual analysis.

        Args:
            caption: The post caption text.
            num_images: Number of images being analyzed.

        Returns:
            The full prompt string.
        """
        return f"""Analyze these {num_images} image(s) from a social media post and return a JSON object with the following structure.

POST CAPTION (for context):
\"\"\"{caption}\"\"\"

INSTRUCTIONS:
1. Extract ALL text overlays exactly as written (verbatim) from each slide.
2. Describe what each image actually shows (subjects, actions, setting).
3. Classify the post type based on the balance of text vs visuals.
4. Identify the visual style (colors, fonts, layout patterns).
5. For visual-first posts: describe the visual narrative/progression across slides.

POST TYPE CLASSIFICATION CRITERIA:
- "text_heavy": Text IS the content, images are backgrounds/decoration. Most slides have text overlays.
- "hybrid": Text and visuals work together. Some slides have text, visuals support/illustrate.
- "visual_first": Visuals ARE the content. Little or no text on slides.
- "photo_dump": Curated photo collection. No text on slides, photos tell the story.
- "meme_quote": Single text block per slide on aesthetic background. Quote or meme format.
- "infographic": Data, charts, or diagrams. Information design focused.

REQUIRED JSON OUTPUT:
{{
    "post_type": "text_heavy|hybrid|visual_first|photo_dump|meme_quote|infographic",
    "text_density": "high|medium|low|none",
    "slide_count": {num_images},
    "slides": [
        {{
            "slide_number": 1,
            "text_overlays": ["exact text on this slide"],
            "visual_description": "what the image actually shows",
            "subjects": ["people", "objects", "scenes depicted"],
            "mood": "emotional tone",
            "layout": "how elements are arranged (e.g. centered_text_over_photo, text_on_solid_bg, full_photo, split_layout)",
            "dominant_colors": ["#hex1", "#hex2"],
            "font_style": "bold_sans_serif|handwritten|serif|null if no text",
            "text_position": "center|top|bottom|left|right|null if no text",
            "text_styling": {{
                "headline_size": "large|medium|small|null if no headline",
                "body_size": "large|medium|small|null if no body text",
                "text_color": "#hex color of main text",
                "headline_color": "#hex color of headline if different from body, else null",
                "text_weight": "bold|regular|light|mixed",
                "text_case": "uppercase|lowercase|title_case|sentence_case|mixed",
                "text_effects": ["shadow", "outline", "glow", "none"],
                "background_treatment": "semi_transparent_overlay|solid_color_block|gradient|none|blurred_photo",
                "text_to_image_ratio": 0.5,
                "text_hierarchy": "describe how text sizes/weights create visual hierarchy (e.g. 'large bold header, smaller regular body below')"
            }}
        }}
    ],
    "overall_visual_style": {{
        "aesthetic": "free-form description of the visual aesthetic",
        "color_palette": ["#hex1", "#hex2", "#hex3"],
        "consistency": "how slides relate visually to each other",
        "visual_narrative": "for visual-first posts: how the image sequence tells a story",
        "brand_elements": "logos, watermarks, recurring visual motifs"
    }}
}}

Return one slide object per image, numbered sequentially. Be precise with text overlays and hex color codes."""

    def _normalize_result(self, result: dict) -> dict:
        """Normalize GPT-4o output to match VisualAnalysisResult schema.

        Ensures all expected fields are present with correct defaults.

        Args:
            result: Raw parsed JSON from GPT-4o.

        Returns:
            Normalized dict matching the schema.
        """
        valid_post_types = {
            "text_heavy",
            "hybrid",
            "visual_first",
            "photo_dump",
            "meme_quote",
            "infographic",
        }

        post_type = result.get("post_type", "visual_first")
        if post_type not in valid_post_types:
            logger.warning("Unknown post_type '%s', defaulting to 'visual_first'", post_type)
            post_type = "visual_first"

        # Normalize slides
        slides = []
        for s in result.get("slides", []):
            ts = s.get("text_styling") or {}
            text_styling = {
                "headline_size": ts.get("headline_size"),
                "body_size": ts.get("body_size"),
                "text_color": ts.get("text_color"),
                "headline_color": ts.get("headline_color"),
                "text_weight": ts.get("text_weight"),
                "text_case": ts.get("text_case"),
                "text_effects": ts.get("text_effects", ["none"]),
                "background_treatment": ts.get("background_treatment", "none"),
                "text_to_image_ratio": ts.get("text_to_image_ratio", 0.0),
                "text_hierarchy": ts.get("text_hierarchy", ""),
            }
            slides.append(
                {
                    "slide_number": s.get("slide_number", len(slides) + 1),
                    "text_overlays": s.get("text_overlays", []),
                    "visual_description": s.get("visual_description", ""),
                    "subjects": s.get("subjects", []),
                    "mood": s.get("mood", ""),
                    "layout": s.get("layout", ""),
                    "dominant_colors": s.get("dominant_colors", []),
                    "font_style": s.get("font_style"),
                    "text_position": s.get("text_position"),
                    "text_styling": text_styling,
                }
            )

        # Normalize overall_visual_style
        ovs = result.get("overall_visual_style", {})
        overall_visual_style = {
            "aesthetic": ovs.get("aesthetic", ""),
            "color_palette": ovs.get("color_palette", []),
            "consistency": ovs.get("consistency", ""),
            "visual_narrative": ovs.get("visual_narrative", ""),
            "brand_elements": ovs.get("brand_elements", ""),
        }

        return {
            "post_type": post_type,
            "text_density": result.get("text_density", "none"),
            "slide_count": result.get("slide_count", len(slides)),
            "slides": slides,
            "overall_visual_style": overall_visual_style,
        }

    def _empty_result(self) -> dict:
        """Return an empty result matching the VisualAnalysisResult schema."""
        return {
            "post_type": "visual_first",
            "text_density": "none",
            "slide_count": 0,
            "slides": [],
            "overall_visual_style": {
                "aesthetic": "",
                "color_palette": [],
                "consistency": "",
                "visual_narrative": "",
                "brand_elements": "",
            },
        }
