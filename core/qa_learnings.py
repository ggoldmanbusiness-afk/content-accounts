"""
QA Learnings Storage

Manages per-account qa_learnings.json files that grow from user feedback.
Learnings feed into both QA checks and image generation prompts.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

VALID_CATEGORIES = {
    "scene_mismatch", "clothing", "child_count",
    "furniture", "text_issue", "other"
}


def load_learnings(account_dir: Path) -> list[dict]:
    """Load qa_learnings.json, return list of learning dicts."""
    learnings_path = account_dir / "qa_learnings.json"
    if not learnings_path.exists():
        return []
    with open(learnings_path) as f:
        return json.load(f)


def add_learning(
    account_dir: Path,
    category: str,
    description: str,
    carousel_dir: str = "",
    slide_num: int = 0
) -> dict:
    """Append a learning to qa_learnings.json. Returns the new entry."""
    if category not in VALID_CATEGORIES:
        category = "other"

    learnings = load_learnings(account_dir)

    entry = {
        "category": category,
        "description": description,
        "carousel_dir": carousel_dir,
        "slide_num": slide_num,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    learnings.append(entry)

    learnings_path = account_dir / "qa_learnings.json"
    with open(learnings_path, "w") as f:
        json.dump(learnings, f, indent=2)

    return entry
