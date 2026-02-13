import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.analytics.db import AnalyticsDB

logger = logging.getLogger(__name__)


class BackfillMatcher:
    """Match scraped posts to generated content in output directories."""

    def __init__(self, db: AnalyticsDB, output_base: Path):
        self.db = db
        self.output_base = output_base

    def backfill_account(self, account_name: str) -> int:
        """Try to match unmatched posts to generated content. Returns count of matched posts."""
        posts = self.db.get_posts_for_account(account_name)
        unmatched = [p for p in posts if p["format"] is None]

        if not unmatched:
            return 0

        # Index all generated content by scanning output dirs
        generated = self._index_generated_content()

        matched_count = 0
        for post in unmatched:
            match = self._find_match(post, generated)
            if match:
                self.db.upsert_post(
                    account_name=account_name,
                    platform=post["platform"],
                    post_id=post["post_id"],
                    topic=match.get("topic"),
                    format=match.get("format"),
                    hook_score=match.get("hook_score"),
                    slide_count=match.get("num_items"),
                )
                matched_count += 1
                logger.info(f"Matched post {post['post_id']} to {match.get('topic')}")

        logger.info(f"Backfill: {matched_count}/{len(unmatched)} posts matched for {account_name}")
        return matched_count

    def _index_generated_content(self) -> list[dict]:
        """Scan output directories for carousel_data.json files."""
        generated = []
        for meta_path in self.output_base.rglob("meta.json"):
            try:
                meta = json.loads(meta_path.read_text())
                carousel_path = meta_path.parent / "carousel_data.json"
                if carousel_path.exists():
                    carousel = json.loads(carousel_path.read_text())
                    hook_text = carousel.get("slides", [{}])[0].get("text", "")
                    meta["hook_text"] = hook_text
                generated.append(meta)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse {meta_path}: {e}")
        return generated

    def _find_match(self, post: dict, generated: list[dict]) -> Optional[dict]:
        """Match a post to generated content by hook text similarity."""
        post_hook = (post.get("hook_text") or "").lower().strip()
        if not post_hook:
            return None

        best_match = None
        best_score = 0.0

        for gen in generated:
            gen_hook = (gen.get("hook_text") or "").lower().strip()
            if not gen_hook:
                continue
            score = self._jaccard_similarity(post_hook, gen_hook)
            if score > best_score and score >= 0.4:
                best_score = score
                best_match = gen

        return best_match

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        stopwords = {"the", "a", "an", "is", "to", "and", "of", "in", "for", "that", "this", "my", "your"}
        words_a = {w for w in a.split() if w not in stopwords}
        words_b = {w for w in b.split() if w not in stopwords}
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
