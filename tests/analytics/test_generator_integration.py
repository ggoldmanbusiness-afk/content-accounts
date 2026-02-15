import json
import pytest
from pathlib import Path
from core.analytics.generator_integration import (
    load_performance_context, weighted_format_choice,
    get_visual_guidance, get_explore_visual_guidance, should_explore,
)


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


@pytest.fixture
def context_with_visuals():
    return {
        "visual_insights": {
            "top_performing": {
                "photography_style": "iphone_authentic",
                "lighting": "golden_hour",
                "composition": "wide",
                "scene_setting": "outdoor",
                "subject_focus": "child_solo",
                "mood": "energetic",
            },
            "hook_recipe": {
                "composition": "wide",
                "photography_style": "iphone_authentic",
                "lighting": "golden_hour",
                "mood": "energetic",
                "subject_focus": "child_solo",
            },
            "sample_size": 15,
        },
        "explore_targets": {
            "photography_style": ["cinematic", "studio"],
            "lighting": ["moody"],
            "scene_setting": ["kitchen", "car"],
        },
        "exploration_ratio": 0.30,
    }


def test_get_visual_guidance(context_with_visuals):
    result = get_visual_guidance(context_with_visuals)
    assert result is not None
    assert "Data shows best performance with:" in result
    assert "golden hour" in result
    assert "iphone authentic" in result


def test_get_visual_guidance_empty():
    assert get_visual_guidance({}) is None
    assert get_visual_guidance({"visual_insights": {}}) is None


def test_get_explore_visual_guidance(context_with_visuals):
    result = get_explore_visual_guidance(context_with_visuals)
    assert result is not None
    assert "Testing new visual approach:" in result


def test_get_explore_visual_guidance_empty():
    assert get_explore_visual_guidance({}) is None
    assert get_explore_visual_guidance({"explore_targets": {}}) is None


def test_should_explore_respects_ratio():
    # With ratio=1.0, should always explore
    assert should_explore({"exploration_ratio": 1.0}) is True
    # With ratio=0.0, should never explore
    assert should_explore({"exploration_ratio": 0.0}) is False


def test_should_explore_default_ratio():
    """Without exploration_ratio, defaults to 0.40."""
    # Run many times — with 0.40 ratio, should get some True and some False
    results = [should_explore({}) for _ in range(100)]
    assert any(results)  # At least one True
    assert not all(results)  # At least one False
