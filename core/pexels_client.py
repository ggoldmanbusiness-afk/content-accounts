"""
Pexels API Client for Stock Photos
Implements video/image history tracking to avoid duplicates
"""

import os
import requests
from typing import List, Dict, Optional
import json
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class PexelsClient:
    """Fetch stock photos from Pexels API"""

    BASE_URL = "https://api.pexels.com/v1"

    def __init__(self, api_key: str = None, history_file: Path = None):
        """
        Initialize Pexels client

        Args:
            api_key: Pexels API key (defaults to env var)
            history_file: Path to track used images
        """
        self.api_key = api_key or os.getenv("PEXELS_API_KEY")
        if not self.api_key:
            raise ValueError("PEXELS_API_KEY not found in environment or constructor")

        self.history_file = history_file or Path("output/pexels_history.json")
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load history of previously used images"""
        if self.history_file.exists():
            try:
                with open(self.history_file) as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load Pexels history: {e}")
                return {"used_ids": [], "max_history": 50}
        return {"used_ids": [], "max_history": 50}

    def _save_history(self):
        """Save updated history"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w') as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save Pexels history: {e}")

    def search_photos(
        self,
        query: str,
        per_page: int = 10,
        orientation: str = "portrait"
    ) -> List[Dict]:
        """
        Search Pexels for photos

        Args:
            query: Search keywords (e.g., "parent child bedtime")
            per_page: Results to return (max 80)
            orientation: "portrait" for 9:16 ratio

        Returns:
            List of photo dicts with id, url, photographer info
        """
        headers = {"Authorization": self.api_key}
        params = {
            "query": query,
            "per_page": per_page,
            "orientation": orientation
        }

        response = requests.get(
            f"{self.BASE_URL}/search",
            headers=headers,
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            raise RuntimeError(f"Pexels API error: {response.status_code} - {response.text}")

        data = response.json()
        photos = data.get("photos", [])

        # Filter out previously used photos
        used_ids = set(self.history["used_ids"])
        fresh_photos = [p for p in photos if p["id"] not in used_ids]

        if fresh_photos:
            logger.info(f"Found {len(fresh_photos)} fresh photos for '{query}'")
            return fresh_photos
        else:
            logger.warning(f"All photos for '{query}' were previously used, returning all")
            return photos  # Fallback if all used

    def download_photo(self, photo: Dict, size: str = "large2x") -> bytes:
        """
        Download photo at specified size

        Args:
            photo: Photo dict from search_photos()
            size: "large2x" (1920px), "large" (940px), "medium" (350px)

        Returns:
            Image bytes
        """
        url = photo["src"][size]
        response = requests.get(url, timeout=30)

        if response.status_code != 200:
            raise RuntimeError(f"Failed to download photo: {response.status_code}")

        # Track this photo as used
        photo_id = photo["id"]
        if photo_id not in self.history["used_ids"]:
            self.history["used_ids"].append(photo_id)

            # Keep only last 50
            if len(self.history["used_ids"]) > self.history["max_history"]:
                self.history["used_ids"] = self.history["used_ids"][-50:]

            self._save_history()
            logger.info(f"Downloaded and tracked Pexels photo {photo_id}")

        return response.content

    def get_photographer_credit(self, photo: Dict) -> str:
        """Get photographer attribution text"""
        return f"Photo by {photo['photographer']} on Pexels"
