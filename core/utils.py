"""
Utilities for Dreamtime Lullabies
Copied from automation repo for standalone operation
"""

import re
import unicodedata
import json
from pathlib import Path
from typing import Set, List, Dict
from datetime import datetime


class SlugGenerator:
    """Generates URL-friendly slugs from text"""

    def __init__(self, max_length: int = 60):
        """
        Initialize slug generator

        Args:
            max_length: Maximum length for generated slugs
        """
        self.max_length = max_length
        self.used_slugs: Set[str] = set()

    def generate(self, text: str, ensure_unique: bool = False) -> str:
        """
        Generate slug from text

        Args:
            text: Input text to convert to slug
            ensure_unique: If True, adds number suffix for duplicates

        Returns:
            URL-friendly slug

        Examples:
            >>> gen = SlugGenerator()
            >>> gen.generate("Bedtime routines for 6 month old")
            'bedtime-routines-for-6-month-old'
        """
        # Lowercase
        slug = text.lower()

        # Remove unicode accents
        slug = unicodedata.normalize('NFKD', slug)
        slug = slug.encode('ascii', 'ignore').decode('ascii')

        # Remove special characters (keep alphanumeric, spaces, hyphens)
        slug = re.sub(r'[^\w\s-]', '', slug)

        # Replace whitespace and multiple spaces with single hyphen
        slug = re.sub(r'[-\s]+', '-', slug)

        # Remove leading/trailing hyphens
        slug = slug.strip('-')

        # Truncate to max length (break at word boundary)
        if len(slug) > self.max_length:
            slug = slug[:self.max_length]
            # Break at last hyphen to avoid cutting mid-word
            last_hyphen = slug.rfind('-')
            if last_hyphen > self.max_length // 2:
                slug = slug[:last_hyphen]

        # Ensure uniqueness if requested
        if ensure_unique:
            slug = self._ensure_unique(slug)

        return slug

    def _ensure_unique(self, slug: str) -> str:
        """
        Ensure slug is unique by adding number suffix if needed

        Args:
            slug: Base slug

        Returns:
            Unique slug
        """
        if slug not in self.used_slugs:
            self.used_slugs.add(slug)
            return slug

        # Add number suffix
        counter = 2
        while True:
            numbered_slug = f"{slug}-{counter}"
            if numbered_slug not in self.used_slugs:
                self.used_slugs.add(numbered_slug)
                return numbered_slug
            counter += 1

    def reset(self):
        """Clear tracking of used slugs"""
        self.used_slugs.clear()


class TopicTracker:
    """Tracks generated topics to prevent duplicates"""

    def __init__(self, account_name: str, max_history: int = 10):
        """
        Initialize topic tracker

        Args:
            account_name: Account name for history file
            max_history: Maximum number of topics to track
        """
        self.account_name = account_name
        self.max_history = max_history

        # Store history in output directory
        history_dir = Path("output") / account_name / "history"
        history_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = history_dir / "topic_history.json"

        self._ensure_history_file()

    def _ensure_history_file(self):
        """Create history file if it doesn't exist"""
        if not self.history_file.exists():
            self.save_history({
                "version": "1.0",
                "account": self.account_name,
                "max_history_size": self.max_history,
                "topics": []
            })

    def load_history(self) -> Dict:
        """Load topic history from file"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            # Corrupted or missing - recreate
            return {
                "version": "1.0",
                "account": self.account_name,
                "max_history_size": self.max_history,
                "topics": []
            }

    def save_history(self, history: Dict):
        """Save topic history to file"""
        with open(self.history_file, 'w') as f:
            json.dump(history, f, indent=2)

    def add_topic(self, topic: str, output_dir: str):
        """
        Add a new topic to history (rolling window)

        Args:
            topic: Topic string
            output_dir: Path to output directory
        """
        history = self.load_history()
        history["topics"].insert(0, {
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "output_dir": str(output_dir)
        })
        # Keep only most recent N topics
        history["topics"] = history["topics"][:self.max_history]
        self.save_history(history)

    def get_recent_topics(self, n: int = None) -> List[str]:
        """
        Get list of recent topic strings

        Args:
            n: Number of recent topics to return (None = all)

        Returns:
            List of topic strings
        """
        history = self.load_history()
        topics = history.get("topics", [])
        if n:
            topics = topics[:n]
        return [t["topic"] for t in topics]

    def is_duplicate(self, new_topic: str, similarity_threshold: float = 0.6) -> bool:
        """
        Check if new topic is too similar to recent topics

        Args:
            new_topic: Topic to check
            similarity_threshold: 0-1, higher = more strict

        Returns:
            True if duplicate/too similar, False otherwise
        """
        is_similar, _ = self.is_topic_too_similar(new_topic, similarity_threshold)
        return is_similar

    def is_topic_too_similar(self, new_topic: str, similarity_threshold: float = 0.6) -> tuple:
        """
        Check if new topic is too similar to recent topics

        Args:
            new_topic: Topic to check
            similarity_threshold: 0-1, higher = more strict

        Returns:
            (is_similar, similar_topic_found)
        """
        recent_topics = self.get_recent_topics(n=5)  # Check last 5 topics

        # Extract key terms from new topic
        new_terms = set(self._extract_key_terms(new_topic.lower()))

        for recent in recent_topics:
            recent_terms = set(self._extract_key_terms(recent.lower()))

            # Calculate Jaccard similarity
            if len(new_terms) == 0 or len(recent_terms) == 0:
                continue

            intersection = len(new_terms & recent_terms)
            union = len(new_terms | recent_terms)
            similarity = intersection / union if union > 0 else 0

            if similarity >= similarity_threshold:
                return (True, recent)

        return (False, None)

    def _extract_key_terms(self, text: str) -> List[str]:
        """Extract key terms from topic (remove stopwords)"""
        # Common stopwords to ignore
        stopwords = {
            'when', 'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'your', 'their', 'about',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had'
        }

        # Split and clean
        words = text.replace("'", " ").split()
        key_terms = [
            w.strip('.,!?()[]{}";:')
            for w in words
            if w.lower() not in stopwords and len(w) > 2
        ]

        return key_terms


def determine_content_format(topic: str) -> str:
    """
    Intelligently select format based on topic keywords.

    Returns 'step_guide' for sequential/procedural topics (guides, methods, schedules).
    Returns 'habit_list' for tips/collections (tips, ideas, activities, checklists).

    Args:
        topic: The topic string to analyze

    Returns:
        'step_guide' or 'habit_list'

    Examples:
        >>> determine_content_format("nap transition guide")
        'step_guide'
        >>> determine_content_format("breastfeeding tips for new moms")
        'habit_list'
        >>> determine_content_format("gentle sleep training methods")
        'step_guide'
        >>> determine_content_format("sensory play activities for babies")
        'habit_list'
    """

    # Keywords that suggest step-by-step sequential content
    STEP_GUIDE_KEYWORDS = {
        'guide', 'how to', 'method', 'methods', 'schedule', 'timeline',
        'building', 'training', 'process', 'steps', 'order', 'sequence',
        'introduction', 'transition', 'first'
    }

    # Keywords that suggest list-based tips/collection content
    HABIT_LIST_KEYWORDS = {
        'tips', 'ideas', 'activities', 'milestones', 'checklist',
        'strategies', 'solutions', 'relief', 'by age', 'by month',
        'dynamics', 'development', 'gear', 'items', 'essentials'
    }

    topic_lower = topic.lower()
    topic_tokens = set(topic_lower.replace('-', ' ').split())

    # Score both formats by counting keyword matches
    step_guide_score = sum(1 for keyword in STEP_GUIDE_KEYWORDS
                           if keyword in topic_lower)
    habit_list_score = sum(1 for keyword in HABIT_LIST_KEYWORDS
                           if keyword in topic_lower)

    # Tie-breakers for ambiguous cases
    if step_guide_score == habit_list_score:
        # Comparison topics (by age/month) should be habit_list
        if 'by age' in topic_lower or 'by month' in topic_lower:
            return 'habit_list'
        # Procedural topics should be step_guide
        if 'how to' in topic_lower:
            return 'step_guide'

    # Return winner
    if step_guide_score > habit_list_score:
        return 'step_guide'
    else:
        return 'habit_list'  # Default to habit_list