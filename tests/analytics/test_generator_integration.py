import json
import pytest
from pathlib import Path
from core.analytics.generator_integration import load_performance_context, weighted_format_choice


@pytest.fixture
def context_file(tmp_path):
    context = {
        "format_weights": {"step_guide": 1.5, "habit_list": 0.6, "scripts": 1.2, "boring_habits": 1.0},
        "top_pillars": ["sleep_routines", "tantrum_management"],
        "optimal_slide_count": 5,
        "hook_insights": {"reference_hooks": ["5 boring habits...", "Stop doing this..."]},
        "experiment_suggestions": ["how_to format untested"]
    }
    path = tmp_path / "performance_context.json"
    path.write_text(json.dumps(context))
    return path


def test_load_performance_context(context_file):
    ctx = load_performance_context(context_file)
    assert ctx["format_weights"]["step_guide"] == 1.5


def test_load_missing_context_returns_none(tmp_path):
    ctx = load_performance_context(tmp_path / "nonexistent.json")
    assert ctx is None


def test_weighted_format_choice(context_file):
    ctx = load_performance_context(context_file)
    available_formats = ["step_guide", "habit_list", "scripts", "boring_habits"]
    counts = {}
    for _ in range(1000):
        choice = weighted_format_choice(available_formats, ctx["format_weights"])
        counts[choice] = counts.get(choice, 0) + 1
    # step_guide (weight 1.5) should be chosen more than habit_list (weight 0.6)
    assert counts.get("step_guide", 0) > counts.get("habit_list", 0)
