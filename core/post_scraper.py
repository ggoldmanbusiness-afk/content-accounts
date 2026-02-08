"""
Scrape a single social media post URL via Apify and return standardized data.

Supports TikTok and Instagram posts, including carousels, reels, and single images.
"""

import logging
import os
import re
from typing import List, Optional

from apify_client import ApifyClient

logger = logging.getLogger(__name__)

TIKTOK_ACTOR_ID = "clockworks~tiktok-scraper"
INSTAGRAM_ACTOR_ID = "apify~instagram-scraper"

# Default timeout for Apify actor runs (seconds)
DEFAULT_TIMEOUT_SECS = 120


class PostScraper:
    """Scrapes a single social media post URL via Apify and returns standardized data."""

    def __init__(self, apify_token: str = None):
        """Initialize Apify client.

        Args:
            apify_token: Apify API token. Falls back to APIFY_API_TOKEN env var.
        """
        self.api_token = apify_token or os.environ.get("APIFY_API_TOKEN")
        if not self.api_token:
            raise ValueError(
                "Apify API token required. Pass apify_token or set APIFY_API_TOKEN env var."
            )
        self.client = ApifyClient(self.api_token)

    def scrape_url(self, url: str) -> dict:
        """Scrape a single post URL and return standardized data.

        Args:
            url: The full URL of the social media post.

        Returns:
            Standardized post data dict.

        Raises:
            ValueError: If the platform cannot be detected or URL is invalid.
            RuntimeError: If the Apify actor run fails or returns no results.
        """
        platform = self._detect_platform(url)
        logger.info("Scraping %s post: %s", platform, url)

        if platform == "tiktok":
            raw = self._scrape_tiktok_post(url)
            return self._standardize_tiktok_data(raw, url)
        elif platform == "instagram":
            raw = self._scrape_instagram_post(url)
            return self._standardize_instagram_data(raw, url)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

    def _detect_platform(self, url: str) -> str:
        """Detect platform from URL.

        Args:
            url: Post URL.

        Returns:
            'tiktok' or 'instagram'.

        Raises:
            ValueError: If the platform cannot be determined.
        """
        url_lower = url.lower()
        if "tiktok.com" in url_lower:
            return "tiktok"
        elif "instagram.com" in url_lower or "instagr.am" in url_lower:
            return "instagram"
        else:
            raise ValueError(
                f"Cannot detect platform from URL: {url}. "
                "Supported: tiktok.com, instagram.com"
            )

    def _detect_content_type(self, raw_data: dict, platform: str) -> str:
        """Detect content type from raw Apify data.

        Args:
            raw_data: Raw item data from Apify.
            platform: 'tiktok' or 'instagram'.

        Returns:
            'carousel', 'single_image', or 'video'.
        """
        if platform == "tiktok":
            if (
                raw_data.get("imagePost")
                or raw_data.get("isSlideshow")
                or raw_data.get("photoMode")
                or raw_data.get("images")
                or raw_data.get("slideshowImageLinks")
            ):
                return "carousel"
            return "video"

        elif platform == "instagram":
            post_type = raw_data.get("type", "")
            if post_type == "Sidecar":
                return "carousel"
            elif post_type in ("Video", "GraphVideo"):
                return "video"
            elif post_type in ("Image", "GraphImage"):
                return "single_image"
            # Fallback heuristics
            if raw_data.get("childPosts"):
                return "carousel"
            if raw_data.get("videoUrl") or raw_data.get("videoViewCount"):
                return "video"
            return "single_image"

        return "video"

    def _scrape_tiktok_post(self, url: str) -> dict:
        """Scrape a TikTok post via Apify.

        Args:
            url: TikTok post URL.

        Returns:
            Raw item dict from Apify.

        Raises:
            RuntimeError: If the run fails or returns no data.
        """
        run_input = {
            "postURLs": [url],
            "shouldDownloadCovers": True,
        }
        logger.debug("Running TikTok scraper with input: %s", run_input)

        try:
            run = self.client.actor(TIKTOK_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=DEFAULT_TIMEOUT_SECS,
            )
        except Exception as e:
            raise RuntimeError(f"TikTok Apify actor run failed: {e}") from e

        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        if not items:
            raise RuntimeError(f"TikTok scraper returned no results for: {url}")

        logger.info("TikTok scraper returned %d item(s)", len(items))
        return items[0]

    def _scrape_instagram_post(self, url: str) -> dict:
        """Scrape an Instagram post via Apify.

        Args:
            url: Instagram post URL.

        Returns:
            Raw item dict from Apify.

        Raises:
            RuntimeError: If the run fails or returns no data.
        """
        run_input = {
            "directUrls": [url],
            "resultsLimit": 1,
            "resultsType": "posts",
        }
        logger.debug("Running Instagram scraper with input: %s", run_input)

        try:
            run = self.client.actor(INSTAGRAM_ACTOR_ID).call(
                run_input=run_input,
                timeout_secs=DEFAULT_TIMEOUT_SECS,
            )
        except Exception as e:
            raise RuntimeError(f"Instagram Apify actor run failed: {e}") from e

        items = list(self.client.dataset(run["defaultDatasetId"]).iterate_items())

        if not items:
            raise RuntimeError(f"Instagram scraper returned no results for: {url}")

        logger.info("Instagram scraper returned %d item(s)", len(items))
        return items[0]

    def _standardize_tiktok_data(self, raw: dict, url: str) -> dict:
        """Normalize TikTok data to the standard output format.

        Args:
            raw: Raw TikTok item from Apify.
            url: Original post URL.

        Returns:
            Standardized post data dict.
        """
        content_type = self._detect_content_type(raw, "tiktok")

        views = raw.get("playCount", 0) or raw.get("viewCount", 0) or raw.get("views", 0)
        likes = raw.get("diggCount", 0) or raw.get("likes", 0)
        comments = raw.get("commentCount", 0) or raw.get("comments", 0)
        shares = raw.get("shareCount", 0) or raw.get("shares", 0)
        saves = raw.get("collectCount", 0) or 0
        caption = raw.get("text", "") or raw.get("desc", "") or ""
        author_meta = raw.get("authorMeta", {}) or {}
        author = author_meta.get("name", "") or raw.get("author", "")
        post_id = raw.get("id", "")
        created_at = raw.get("createTime", "")
        raw_hashtags = raw.get("hashtags", [])

        total_engagement = likes + comments + shares + saves
        engagement_rate = (total_engagement / views) if views > 0 else 0.0

        media_urls = self._extract_media_urls(raw, "tiktok", content_type)
        hashtags = self._extract_hashtags(caption, raw_hashtags)

        return {
            "platform": "tiktok",
            "post_id": str(post_id),
            "url": url,
            "author": author,
            "caption": caption,
            "content_type": content_type,
            "metrics": {
                "views": int(views),
                "likes": int(likes),
                "comments": int(comments),
                "shares": int(shares),
                "saves": int(saves),
                "engagement_rate": round(engagement_rate, 6),
            },
            "media_urls": media_urls,
            "hashtags": hashtags,
            "created_at": str(created_at),
            "raw_data": raw,
        }

    def _standardize_instagram_data(self, raw: dict, url: str) -> dict:
        """Normalize Instagram data to the standard output format.

        Args:
            raw: Raw Instagram item from Apify.
            url: Original post URL.

        Returns:
            Standardized post data dict.
        """
        content_type = self._detect_content_type(raw, "instagram")

        likes = raw.get("likesCount", 0) or raw.get("likes", 0) or 0
        comments = raw.get("commentsCount", 0) or raw.get("comments", 0) or 0
        views = raw.get("videoViewCount", 0) or raw.get("views", 0) or (likes * 3)
        caption = raw.get("caption", "") or ""
        author = raw.get("ownerUsername", "") or ""
        post_id = raw.get("id", "") or raw.get("shortCode", "") or ""
        short_code = raw.get("shortCode", "")
        url_field = raw.get("url", "") or (
            f"https://www.instagram.com/p/{short_code}" if short_code else url
        )
        created_at = raw.get("timestamp", "")

        # Instagram doesn't expose saves
        saves = 0
        shares = 0

        total_engagement = likes + comments + shares + saves
        engagement_rate = (total_engagement / views) if views > 0 else 0.0

        media_urls = self._extract_media_urls(raw, "instagram", content_type)
        hashtags = self._extract_hashtags(caption)

        return {
            "platform": "instagram",
            "post_id": str(post_id),
            "url": url_field,
            "author": author,
            "caption": caption,
            "content_type": content_type,
            "metrics": {
                "views": int(views),
                "likes": int(likes),
                "comments": int(comments),
                "shares": int(shares),
                "saves": int(saves),
                "engagement_rate": round(engagement_rate, 6),
            },
            "media_urls": media_urls,
            "hashtags": hashtags,
            "created_at": str(created_at),
            "raw_data": raw,
        }

    def _extract_media_urls(self, raw: dict, platform: str, content_type: str) -> List[str]:
        """Extract image/video URLs based on platform and content type.

        Args:
            raw: Raw item data from Apify.
            platform: 'tiktok' or 'instagram'.
            content_type: 'carousel', 'single_image', or 'video'.

        Returns:
            List of media URL strings.
        """
        urls: List[str] = []

        if platform == "tiktok":
            if content_type == "carousel":
                # Try slideshowImageLinks first (common Apify format)
                slideshow_links = raw.get("slideshowImageLinks", []) or []
                if slideshow_links:
                    for item in slideshow_links:
                        if isinstance(item, dict):
                            link = item.get("tiktokLink", "") or item.get("url", "")
                            if link:
                                urls.append(link)
                        elif isinstance(item, str):
                            urls.append(item)

                # Try mediaUrls field
                if not urls:
                    media_urls_field = raw.get("mediaUrls", [])
                    if media_urls_field:
                        urls.extend(media_urls_field)

                # Try imagePost.images[].imageURL.urlList[0]
                if not urls:
                    image_post = raw.get("imagePost", {}) or {}
                    images_list = image_post.get("images", []) or []
                    for img in images_list:
                        image_url = img.get("imageURL", {}) or {}
                        url_list = image_url.get("urlList", []) or []
                        if url_list:
                            urls.append(url_list[0])

                # Fallback to images field
                if not urls:
                    images_field = raw.get("images", []) or []
                    if isinstance(images_field, list):
                        for img in images_field:
                            if isinstance(img, str):
                                urls.append(img)
                            elif isinstance(img, dict):
                                img_url = img.get("url", "") or img.get("imageURL", "")
                                if img_url:
                                    urls.append(img_url)
            else:
                # Video: try videoUrl, then mediaUrls
                video_url = raw.get("videoUrl", "") or raw.get("video_url", "")
                if video_url:
                    urls.append(video_url)
                elif raw.get("mediaUrls"):
                    urls.extend(raw["mediaUrls"])

        elif platform == "instagram":
            if content_type == "carousel":
                child_posts = raw.get("childPosts", []) or []
                if child_posts:
                    for child in child_posts:
                        display_url = child.get("displayUrl", "")
                        if display_url:
                            urls.append(display_url)
                else:
                    # Fallback: use the main displayUrl as a single image
                    display_url = raw.get("displayUrl", "")
                    if display_url:
                        urls.append(display_url)
            elif content_type == "video":
                video_url = raw.get("videoUrl", "")
                if video_url:
                    urls.append(video_url)
                else:
                    display_url = raw.get("displayUrl", "")
                    if display_url:
                        urls.append(display_url)
            else:
                # single_image
                display_url = raw.get("displayUrl", "")
                if display_url:
                    urls.append(display_url)

        return urls

    def _extract_hashtags(self, caption: str, raw_hashtags: list = None) -> List[str]:
        """Extract hashtags from caption text and/or raw hashtag data.

        Returns a flat list of hashtag strings without the '#' prefix.

        Args:
            caption: Post caption text.
            raw_hashtags: Optional list of hashtag objects or strings from raw data.

        Returns:
            Deduplicated list of hashtag strings (no # prefix).
        """
        hashtags: List[str] = []
        seen: set = set()

        # Extract from raw hashtag data first (more reliable)
        if raw_hashtags:
            for tag in raw_hashtags:
                if isinstance(tag, str):
                    name = tag.lstrip("#").strip().lower()
                elif isinstance(tag, dict):
                    name = (tag.get("name", "") or tag.get("title", "") or "").lstrip("#").strip().lower()
                else:
                    continue
                if name and name not in seen:
                    hashtags.append(name)
                    seen.add(name)

        # Also extract from caption text
        if caption:
            found = re.findall(r"#(\w+)", caption)
            for tag in found:
                name = tag.lower()
                if name not in seen:
                    hashtags.append(name)
                    seen.add(name)

        return hashtags
