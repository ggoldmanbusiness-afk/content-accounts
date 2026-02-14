import json
import logging
from pathlib import Path
from typing import Optional

from core.analytics.db import AnalyticsDB
from core.analytics.visual_extractor import extract_from_post

logger = logging.getLogger(__name__)

# Minimum similarity thresholds
CAPTION_MATCH_THRESHOLD = 0.5   # High bar for caption-to-caption matching
JACCARD_FALLBACK_THRESHOLD = 0.3  # Raised from 0.15 — must be a strong match
TOPIC_KEYWORD_MIN_OVERLAP = 3     # Raised from 2 — need more keyword evidence


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

        generated = self._index_generated_content()

        matched_count = 0
        for post in unmatched:
            match, confidence = self._find_match(post, generated)
            if match:
                self.db.upsert_post(
                    account_name=account_name,
                    platform=post["platform"],
                    post_id=post["post_id"],
                    topic=match.get("topic"),
                    format=match.get("format"),
                    hook_score=match.get("hook_score"),
                    slide_count=match.get("num_items"),
                    content_pillar=match.get("topic"),
                )
                # Extract and store visual attributes if image_prompts available
                image_prompts = match.get("image_prompts", [])
                if image_prompts:
                    visuals = extract_from_post(image_prompts)
                    self.db.upsert_post_visuals(
                        post_id=post["post_id"],
                        dominant=visuals["dominant"],
                        hook=visuals["hook"],
                        all_attributes=visuals["all_attributes"],
                    )
                matched_count += 1
                logger.info(
                    f"Matched post {post['post_id']} -> "
                    f"{match.get('topic')} ({match.get('format')}) "
                    f"[confidence={confidence}]"
                )

        logger.info(f"Backfill: {matched_count}/{len(unmatched)} posts matched for {account_name}")
        return matched_count

    def backfill_visuals(self, account_name: str) -> int:
        """Extract visual attributes for already-matched posts that are missing visual data."""
        posts = self.db.get_posts_for_account(account_name)
        matched = [p for p in posts if p["format"] is not None]

        generated = self._index_generated_content()
        # Build lookup from generated content by topic+format for re-matching
        gen_by_key = {}
        for gen in generated:
            key = (gen.get("topic", ""), gen.get("format", ""))
            gen_by_key[key] = gen

        extracted_count = 0
        for post in matched:
            # Skip if visuals already exist
            if self.db.get_post_visuals(post["post_id"]):
                continue

            # Find matching generated content to get image_prompts
            match, _ = self._find_match(post, generated)
            image_prompts = match.get("image_prompts", []) if match else []

            if image_prompts:
                visuals = extract_from_post(image_prompts)
                self.db.upsert_post_visuals(
                    post_id=post["post_id"],
                    dominant=visuals["dominant"],
                    hook=visuals["hook"],
                    all_attributes=visuals["all_attributes"],
                )
                extracted_count += 1
                logger.info(f"Extracted visuals for {post['post_id']} ({post.get('topic')})")

        logger.info(f"Visual backfill: {extracted_count}/{len(matched)} posts for {account_name}")
        return extracted_count

    def _index_generated_content(self) -> list[dict]:
        """Scan output directories for meta.json and carousel_data.json files."""
        generated = []
        for meta_path in self.output_base.rglob("meta.json"):
            try:
                meta = json.loads(meta_path.read_text())
                carousel_path = meta_path.parent / "carousel_data.json"

                # Collect all text for fallback matching
                all_text = [meta.get("topic", "")]
                if carousel_path.exists():
                    carousel = json.loads(carousel_path.read_text())
                    slides = carousel.get("slides", [])
                    for slide in slides:
                        all_text.append(slide.get("text", ""))
                    # Use hook_text from meta.json if available (new format),
                    # otherwise fall back to slide 1
                    if "hook_text" not in meta:
                        meta["hook_text"] = slides[0].get("text", "") if slides else ""
                    # Capture image prompts for visual extraction
                    image_prompts = carousel.get("image_prompts", [])
                    if image_prompts:
                        meta["image_prompts"] = image_prompts

                meta["all_text"] = " ".join(all_text).lower()

                # Store caption for exact matching (new meta.json format has it)
                if "caption" not in meta:
                    caption_path = meta_path.parent / "caption.txt"
                    if caption_path.exists():
                        meta["caption"] = caption_path.read_text().strip()

                generated.append(meta)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse {meta_path}: {e}")
        return generated

    def _find_match(self, post: dict, generated: list[dict]) -> tuple[Optional[dict], str]:
        """Match a post to generated content using tiered strategies.

        Returns (matched_content, confidence_level) where confidence is
        'exact', 'caption', 'topic', or 'fuzzy'.
        """
        post_caption = (post.get("hook_text") or "").lower().strip()
        if not post_caption:
            return None, ""

        # Strategy 1: Exact caption match (highest confidence)
        # Compare post caption against stored caption.txt content
        for gen in generated:
            gen_caption = (gen.get("caption") or "").lower().strip()
            if gen_caption and post_caption in gen_caption:
                return gen, "exact"

        # Strategy 2: Content ID match (for new-format meta.json)
        # Not applicable to existing content yet, but future-proof
        post_content_id = post.get("content_id")
        if post_content_id:
            for gen in generated:
                if gen.get("content_id") == post_content_id:
                    return gen, "exact"

        best_match = None
        best_score = 0.0
        best_confidence = ""

        for gen in generated:
            # Strategy 3: Caption-to-caption similarity
            gen_caption = (gen.get("caption") or "").lower()
            if gen_caption:
                score = self._jaccard_similarity(post_caption, gen_caption)
                if score > best_score and score >= CAPTION_MATCH_THRESHOLD:
                    best_score = score
                    best_match = gen
                    best_confidence = "caption"
                    continue

            # Strategy 4: Topic keywords in caption (need strong overlap)
            topic = (gen.get("topic") or "").lower()
            topic_words = self._extract_keywords(topic)
            caption_words = self._extract_keywords(post_caption)

            if topic_words and caption_words:
                overlap = topic_words & caption_words
                if len(overlap) >= TOPIC_KEYWORD_MIN_OVERLAP:
                    score = len(overlap) / len(topic_words)
                    if score > best_score:
                        best_score = score
                        best_match = gen
                        best_confidence = "topic"
                        continue

            # Strategy 5: Slide content similarity (lowest confidence, high bar)
            all_text = gen.get("all_text", "")
            if all_text:
                score = self._jaccard_similarity(post_caption, all_text)
                if score > best_score and score >= JACCARD_FALLBACK_THRESHOLD:
                    best_score = score
                    best_match = gen
                    best_confidence = "fuzzy"

        return best_match, best_confidence

    @staticmethod
    def _extract_keywords(text: str) -> set[str]:
        stopwords = {
            "the", "a", "an", "is", "to", "and", "of", "in", "for", "that", "this",
            "my", "your", "you", "i", "we", "they", "it", "are", "was", "were", "be",
            "been", "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "can", "just", "not", "no", "so", "but", "or", "if", "from",
            "with", "at", "by", "on", "about", "up", "out", "how", "what", "when",
            "why", "all", "each", "every", "these", "those", "them", "their", "our",
            "its", "than", "then", "too", "very", "even", "more", "most", "some",
        }
        words = set()
        for w in text.replace("-", " ").replace("_", " ").split():
            w = w.strip(".,!?#@()[]{}\"'")
            if len(w) > 2 and w not in stopwords:
                words.add(w)
        return words

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        stopwords = {"the", "a", "an", "is", "to", "and", "of", "in", "for", "that", "this", "my", "your"}
        words_a = {w for w in a.split() if w not in stopwords and len(w) > 2}
        words_b = {w for w in b.split() if w not in stopwords and len(w) > 2}
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
