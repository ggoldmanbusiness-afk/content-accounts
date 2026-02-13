"""Functions for integrating performance context into the content generator."""
import json
import random
from pathlib import Path
from typing import Optional


def load_performance_context(context_path: Path) -> Optional[dict]:
    """Load performance_context.json if it exists."""
    if not context_path.exists():
        return None
    try:
        return json.loads(context_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def weighted_format_choice(available_formats: list[str], format_weights: dict[str, float]) -> str:
    """Choose a format weighted by performance data."""
    weights = [format_weights.get(fmt, 1.0) for fmt in available_formats]
    return random.choices(available_formats, weights=weights, k=1)[0]


def get_reference_hooks(context: dict) -> list[str]:
    """Get high-performing hooks to use as reference examples in the semantic scorer."""
    return context.get("hook_insights", {}).get("reference_hooks", [])


def get_top_pillars(context: dict) -> list[str]:
    """Get top-performing content pillars."""
    return context.get("top_pillars", [])


def get_experiment_suggestion(context: dict) -> Optional[str]:
    """Get an experiment suggestion (exploration)."""
    suggestions = context.get("experiment_suggestions", [])
    return random.choice(suggestions) if suggestions else None
