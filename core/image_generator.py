"""
Gemini Image Generator for Dreamtime Lullabies
Direct integration with Google's Gemini API for image generation (Nano Banana)
"""

import logging
import requests
import base64
import os
from pathlib import Path
from typing import Optional
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
