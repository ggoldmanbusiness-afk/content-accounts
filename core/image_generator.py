"""
Unified Image Generator
Supports both Gemini AI generation and Pexels stock photos
"""

import logging
import requests
import base64
import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class GeminiImageGenerator:
    """Generate images using Google's Gemini API (Nano Banana Pro/Flash)"""

    def __init__(self, model: str = "pro", api_key: Optional[str] = None):
        """
        Initialize Gemini image generator

        Args:
            model: "pro" (Nano Banana Pro, higher quality) or "flash" (faster)
            api_key: Optional API key override (defaults to env GEMINI_API_KEY)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")

        # Model configuration
        if model == "pro":
            self.model_id = "gemini-3-pro-image-preview"  # Nano Banana Pro
        elif model == "flash":
            self.model_id = "gemini-2.5-flash-image"  # Faster, lower quality
        else:
            raise ValueError(f"Invalid model: {model}. Must be 'pro' or 'flash'")

        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
        logger.info(f"Gemini Image Generator initialized with model: {self.model_id}")

    def generate_image(
        self,
        prompt: str,
        reference_image: Optional[bytes] = None
    ) -> Optional[bytes]:
        """
        Generate image from text prompt

        Args:
            prompt: Text description of image to generate
            reference_image: Optional reference image for visual consistency

        Returns:
            Image bytes (PNG format), or None if generation fails
        """
        try:
            logger.info(f"Generating image: {prompt[:80]}...")

            # Build request body
            parts = [{"text": prompt}]

            # Add reference image if provided (for visual consistency)
            if reference_image:
                # Encode as base64
                ref_base64 = base64.b64encode(reference_image).decode('utf-8')

                # Detect mime type
                mime_type = "image/png"
                if reference_image[:4] == b'\xff\xd8\xff\xe0' or reference_image[:4] == b'\xff\xd8\xff\xe1':
                    mime_type = "image/jpeg"

                parts.append({
                    "inlineData": {
                        "mimeType": mime_type,
                        "data": ref_base64
                    }
                })
                logger.info("Using reference image for visual consistency")

            request_body = {
                "contents": [{
                    "parts": parts
                }],
                "generationConfig": {
                    "responseModalities": ["IMAGE", "TEXT"]
                }
            }

            # Make API request
            url = f"{self.base_url}/models/{self.model_id}:generateContent"
            headers = {
                "x-goog-api-key": self.api_key,
                "Content-Type": "application/json"
            }

            response = requests.post(
                url,
                json=request_body,
                headers=headers,
                timeout=120
            )

            # Check for errors
            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return None

            # Parse response
            result = response.json()

            if "error" in result:
                logger.error(f"Gemini API error: {result['error'].get('message', 'Unknown error')}")
                return None

            # Extract image data
            candidates = result.get("candidates", [])
            if not candidates:
                logger.error("No candidates in Gemini response")
                return None

            content = candidates[0].get("content", {})
            parts_response = content.get("parts", [])

            # Find the image part
            image_data = None
            for part in parts_response:
                if "inlineData" in part:
                    image_data = part["inlineData"].get("data")
                    break

            if not image_data:
                logger.error("No image data in Gemini response")
                return None

            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            logger.info(f"Successfully generated image ({len(image_bytes)} bytes)")

            return image_bytes

        except requests.exceptions.Timeout:
            logger.error("Gemini API request timed out")
            return None
        except Exception as e:
            logger.error(f"Error generating image with Gemini: {e}")
            return None


class ImageGenerator:
    """Unified image generation supporting both Gemini and Pexels"""

    def __init__(self, mode: str = "gemini", gemini_key: str = None, pexels_key: str = None):
        """
        Initialize image generator

        Args:
            mode: "gemini" for AI generation or "pexels" for stock photos
            gemini_key: Optional Gemini API key
            pexels_key: Optional Pexels API key
        """
        self.mode = mode

        if mode == "gemini":
            self.gemini = GeminiImageGenerator(api_key=gemini_key)
            logger.info("ImageGenerator initialized in Gemini mode")
        elif mode == "pexels":
            # Lazy import to avoid circular dependency
            from core.pexels_client import PexelsClient
            self.pexels = PexelsClient(api_key=pexels_key)
            logger.info("ImageGenerator initialized in Pexels mode")
        else:
            raise ValueError(f"Invalid mode: {mode}. Use 'gemini' or 'pexels'")

    def generate_for_carousel(
        self,
        topic: str,
        num_slides: int,
        prompts: Optional[List[str]] = None,
        format_name: str = None
    ) -> List[bytes]:
        """
        Generate images for carousel using selected mode

        Args:
            topic: Content topic
            num_slides: Number of images needed
            prompts: Optional image prompts for Gemini mode
            format_name: Optional format name for Pexels query optimization

        Returns:
            List of image bytes
        """
        if self.mode == "pexels":
            return self._generate_pexels(topic, num_slides, format_name)
        else:
            return self._generate_gemini(prompts, num_slides)

    def _generate_gemini(self, prompts: List[str], num_slides: int) -> List[bytes]:
        """Generate images using Gemini AI"""
        if not prompts or len(prompts) < num_slides:
            logger.warning(f"Not enough prompts ({len(prompts) if prompts else 0}) for {num_slides} slides")
            return []

        images = []
        reference_image = None

        for i, prompt in enumerate(prompts[:num_slides]):
            img_bytes = self.gemini.generate_image(prompt, reference_image=reference_image)

            if img_bytes:
                images.append(img_bytes)
                # Use first image as reference for consistency
                if i == 0:
                    reference_image = img_bytes
            else:
                logger.error(f"Failed to generate image {i+1}/{num_slides}")

        return images

    def _generate_pexels(self, topic: str, num_slides: int, format_name: str = None) -> List[bytes]:
        """Fetch Pexels photos for topic with fallback strategies"""
        # Strategy 1: Try topic-specific query (request 2x for better selection)
        query = self._topic_to_pexels_query(topic, format_name)
        logger.info(f"Searching Pexels for: {query}")

        photos = self.pexels.search_photos(query, per_page=min(num_slides * 2, 80))  # Max 80 per Pexels API

        # Strategy 2: If not enough, try broader query
        if len(photos) < num_slides:
            logger.warning(f"Only found {len(photos)}/{num_slides} photos, trying broader query")
            broad_query = self._get_fallback_query(format_name)
            logger.info(f"Fallback search: {broad_query}")
            photos = self.pexels.search_photos(broad_query, per_page=min(num_slides * 2, 80))

        # Strategy 3: If STILL not enough, allow photo reuse by requesting more pages
        if len(photos) < num_slides:
            logger.warning(f"Still only {len(photos)}/{num_slides} photos, allowing reuse")
            # Get more results by not filtering history
            import requests
            headers = {"Authorization": self.pexels.api_key}
            params = {
                "query": "parent child cozy",  # Generic query
                "per_page": 80,  # Max allowed
                "orientation": "portrait"
            }
            response = requests.get(f"{self.pexels.BASE_URL}/search", headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                all_photos = data.get("photos", [])
                # Mix with what we have
                photos.extend([p for p in all_photos if p["id"] not in [x["id"] for x in photos]])

        if not photos:
            logger.error(f"No Pexels photos found even with fallbacks")
            return []

        # Download images
        images = []
        for photo in photos[:num_slides]:
            try:
                img_bytes = self.pexels.download_photo(photo, size="large2x")  # 1920px
                images.append(img_bytes)
                logger.info(f"Downloaded Pexels photo {photo['id']} by {photo['photographer']}")
            except Exception as e:
                logger.error(f"Failed to download Pexels photo {photo['id']}: {e}")

        if len(images) < num_slides:
            logger.warning(f"Only downloaded {len(images)}/{num_slides} images")

        return images

    def _topic_to_pexels_query(self, topic: str, format_name: str = None) -> str:
        """
        Convert topic to Pexels search keywords

        Args:
            topic: Content topic
            format_name: Optional format for query optimization

        Returns:
            Optimized Pexels search query
        """
        # If format specified, use format-specific query builder
        if format_name:
            try:
                from core.content_formats import get_pexels_query
                return get_pexels_query(format_name, topic)
            except Exception as e:
                logger.warning(f"Failed to get format-specific Pexels query: {e}")

        # Fallback: topic-specific mappings
        topic_mappings = {
            "sleep": "baby sleeping peaceful nursery",
            "tantrum": "parent comforting upset toddler calm",
            "feeding": "baby eating parent gentle",
            "bedtime": "parent child bedtime cozy",
            "routine": "parent child morning routine peaceful",
            "sibling": "parent children playing together",
            "picky eating": "toddler eating table parent",
        }

        # Find best match
        topic_lower = topic.lower()
        for key, query in topic_mappings.items():
            if key in topic_lower:
                return query

        # Default: generic parent-child query with topic
        return f"parent child {topic}"

    def _get_fallback_query(self, format_name: str = None) -> str:
        """
        Get a broad fallback query when specific topic yields few results

        Args:
            format_name: Optional format for context

        Returns:
            Broad Pexels search query
        """
        # Format-specific fallbacks
        if format_name == "scripts":
            return "parent comforting toddler calm gentle"
        elif format_name == "boring_habits":
            return "parent child routine peaceful home"
        elif format_name == "how_to":
            return "parent baby caring gentle nurturing"

        # Generic fallback
        return "parent child warm cozy intimate"
