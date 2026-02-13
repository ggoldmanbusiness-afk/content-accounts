import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from apify_client import ApifyClient

from core.analytics.db import AnalyticsDB

logger = logging.getLogger(__name__)

# Same actors used in core/post_scraper.py
TIKTOK_ACTOR = "clockworks~tiktok-scraper"
INSTAGRAM_ACTOR = "apify~instagram-scraper"


class AccountScraper:
    def __init__(self, db: AnalyticsDB, apify_token: str = None):
        self.db = db
        self.apify_token = apify_token or os.environ.get("APIFY_API_TOKEN")
        if not self.apify_token:
            raise ValueError("Apify token required. Set APIFY_API_TOKEN env var or pass apify_token.")
        self.client = ApifyClient(self.apify_token)

    def scrape_account(self, account_name: str, platform: str, username: str) -> dict:
        """Scrape a single account's posts and store metrics."""
        logger.info(f"Scraping {platform}/@{username} for account {account_name}")

        if platform == "tiktok":
            posts_data = self._scrape_tiktok(username)
        elif platform == "instagram":
            posts_data = self._scrape_instagram(username)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        new_posts = 0
        updated_posts = 0

        for post in posts_data:
            post_id = post["post_id"]
            existing = self.db.get_post(post_id)

            if existing:
                updated_posts += 1
            else:
                new_posts += 1
                self.db.upsert_post(
                    account_name=account_name,
                    platform=platform,
                    post_id=post_id,
                    post_url=post.get("url"),
                    hook_text=post.get("caption", "")[:200],
                    published_at=post.get("published_at"),
                )

            # Always insert a fresh metrics snapshot
            self.db.insert_snapshot(
                post_id=post_id,
                views=post.get("views", 0),
                likes=post.get("likes", 0),
                comments=post.get("comments", 0),
                shares=post.get("shares", 0),
                saves=post.get("saves", 0),
            )

        result = {"new_posts": new_posts, "updated_posts": updated_posts}
        logger.info(f"Done: {new_posts} new, {updated_posts} updated for {account_name}/{platform}")
        return result

    def scrape_all(self, platform_profiles: dict[str, dict[str, str]]) -> dict:
        """Scrape all accounts. platform_profiles: {account_name: {platform: username}}"""
        results = {}
        for account_name, profiles in platform_profiles.items():
            results[account_name] = {}
            for platform, username in profiles.items():
                try:
                    results[account_name][platform] = self.scrape_account(account_name, platform, username)
                except Exception as e:
                    logger.error(f"Failed to scrape {account_name}/{platform}: {e}")
                    results[account_name][platform] = {"error": str(e)}
        return results

    def _scrape_tiktok(self, username: str) -> list[dict]:
        run = self.client.actor(TIKTOK_ACTOR).call(
            run_input={
                "profiles": [username],
                "resultsPerPage": 30,
                "shouldDownloadVideos": False,
            }
        )
        dataset = self.client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())

        posts = []
        for item in items:
            # Stats can be top-level or nested under statsV2 depending on actor version
            stats = item.get("statsV2", {})
            posts.append({
                "post_id": str(item.get("id", "")),
                "url": item.get("webVideoUrl", ""),
                "caption": item.get("text", ""),
                "published_at": item.get("createTimeISO"),
                "views": item.get("playCount") or stats.get("playCount", 0),
                "likes": item.get("diggCount") or stats.get("diggCount", 0),
                "comments": item.get("commentCount") or stats.get("commentCount", 0),
                "shares": item.get("shareCount") or stats.get("shareCount", 0),
                "saves": item.get("collectCount") or stats.get("collectCount", 0),
            })
        return posts

    def _scrape_instagram(self, username: str) -> list[dict]:
        run = self.client.actor(INSTAGRAM_ACTOR).call(
            run_input={
                "usernames": [username],
                "resultsLimit": 30,
            }
        )
        dataset = self.client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())

        posts = []
        for item in items:
            posts.append({
                "post_id": str(item.get("id", "")),
                "url": item.get("url", ""),
                "caption": item.get("caption", ""),
                "published_at": item.get("timestamp"),
                "views": item.get("videoViewCount", 0) or item.get("playCount", 0),
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "shares": 0,  # Instagram doesn't expose shares via scraping
                "saves": 0,   # Instagram doesn't expose saves via scraping
            })
        return posts
