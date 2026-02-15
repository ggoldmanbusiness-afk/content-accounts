import json
import pytest
from core.analytics.db import AnalyticsDB
from core.analytics.analyzer import AccountAnalyzer


@pytest.fixture
def db_with_data(tmp_path):
    db = AnalyticsDB(tmp_path / "test.db")
    # Insert posts across 2 formats
    for i in range(5):
        db.upsert_post(account_name="test", platform="tiktok", post_id=f"sg_{i}",
                        format="step_guide", hook_score=16.0, slide_count=5,
                        content_pillar="sleep_routines", published_at=f"2026-02-0{i+1}T10:00:00")
        db.insert_snapshot(post_id=f"sg_{i}", views=10000, likes=500, comments=50, shares=30, saves=200)

    for i in range(5):
        db.upsert_post(account_name="test", platform="tiktok", post_id=f"hl_{i}",
                        format="habit_list", hook_score=14.0, slide_count=7,
                        content_pillar="tantrum_management", published_at=f"2026-02-0{i+1}T14:00:00")
        db.insert_snapshot(post_id=f"hl_{i}", views=4000, likes=100, comments=10, shares=5, saves=30)
    return db


class TestAccountAnalyzer:
    def test_format_performance(self, db_with_data):
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.analyze_formats("test")
        assert "step_guide" in result
        assert "habit_list" in result
        assert result["step_guide"]["avg_views"] > result["habit_list"]["avg_views"]

    def test_pillar_performance(self, db_with_data):
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.analyze_pillars("test")
        # Pillars are now grouped into broad categories
        assert "Sleep & Routines" in result
        assert "Behavior & Discipline" in result
        assert result["Sleep & Routines"]["post_count"] == 5
        assert result["Behavior & Discipline"]["post_count"] == 5

    def test_top_and_bottom_posts(self, db_with_data):
        analyzer = AccountAnalyzer(db=db_with_data)
        top = analyzer.top_posts("test", n=3)
        bottom = analyzer.bottom_posts("test", n=3)
        assert len(top) == 3
        assert len(bottom) == 3
        assert top[0]["views"] >= top[1]["views"]
        assert bottom[0]["views"] <= bottom[1]["views"]

    def test_pareto_analysis(self, db_with_data):
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.pareto_analysis("test")
        assert "top_formats" in result
        assert "top_pillars" in result
        assert result["top_formats"][0]["format"] == "step_guide"

    def test_full_report(self, db_with_data):
        analyzer = AccountAnalyzer(db=db_with_data)
        report = analyzer.full_report("test")
        assert "formats" in report
        assert "pillars" in report
        assert "top_posts" in report
        assert "bottom_posts" in report
        assert "pareto" in report
        assert "summary" in report
        assert "timeline" in report
        assert "save_rate" in report
        assert "cadence" in report
        assert "recommendations" in report
        assert "visuals" in report
        assert "hook_visuals" in report
        # Save rate should have overall and by_format
        assert "overall_save_rate" in report["save_rate"]
        assert "by_format" in report["save_rate"]
        # Cadence should have posts_per_week
        assert report["cadence"]["posts_per_week"] is not None

    def test_visual_analysis_empty(self, db_with_data):
        """Visual analysis returns empty dict when no visual data exists."""
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.analyze_visuals("test")
        assert result == {}

    def test_visual_analysis_with_data(self, db_with_data):
        """Visual analysis returns attribute breakdowns when visual data exists."""
        # Add visual data for some posts
        db_with_data.upsert_post_visuals(
            post_id="sg_0",
            dominant={"photography_style": "iphone_authentic", "lighting": "golden_hour",
                      "composition": "closeup", "scene_setting": "bedroom", "mood": "warm_cozy"},
            hook={"composition": "closeup", "photography_style": "iphone_authentic",
                  "lighting": "golden_hour", "mood": "warm_cozy"},
            all_attributes={},
        )
        db_with_data.upsert_post_visuals(
            post_id="sg_1",
            dominant={"photography_style": "iphone_authentic", "lighting": "natural",
                      "composition": "wide", "scene_setting": "outdoor", "mood": "energetic"},
            hook={"composition": "wide", "photography_style": "iphone_authentic",
                  "lighting": "natural", "mood": "energetic"},
            all_attributes={},
        )
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.analyze_visuals("test")
        assert "photography_style" in result
        assert "iphone_authentic" in result["photography_style"]
        assert result["photography_style"]["iphone_authentic"]["post_count"] == 2

    def test_hook_visual_analysis(self, db_with_data):
        """Hook visual analysis returns hook-specific attribute breakdowns."""
        db_with_data.upsert_post_visuals(
            post_id="sg_0",
            dominant={"photography_style": "iphone_authentic"},
            hook={"composition": "closeup", "photography_style": "iphone_authentic",
                  "lighting": "golden_hour", "mood": "warm_cozy"},
            all_attributes={},
        )
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.analyze_hook_visuals("test")
        assert "composition" in result
        assert "closeup" in result["composition"]

    def test_refresh_context_writes_visual_insights(self, db_with_data, tmp_path):
        """refresh_context writes visual_insights and explore_targets to file."""
        # Add visual data for multiple posts so we hit the min 2 threshold
        for post_id in ["sg_0", "sg_1", "sg_2"]:
            db_with_data.upsert_post_visuals(
                post_id=post_id,
                dominant={"photography_style": "iphone_authentic", "lighting": "golden_hour",
                          "composition": "wide", "scene_setting": "outdoor",
                          "subject_focus": "child_solo", "mood": "energetic"},
                hook={"composition": "wide", "photography_style": "iphone_authentic",
                      "lighting": "golden_hour", "mood": "energetic",
                      "subject_focus": "child_solo"},
                all_attributes={},
            )

        # One post with a different style (will be <2 so goes to explore_targets)
        db_with_data.upsert_post_visuals(
            post_id="sg_3",
            dominant={"photography_style": "cinematic", "lighting": "moody",
                      "composition": "closeup", "scene_setting": "bedroom",
                      "subject_focus": "hands_detail", "mood": "warm_cozy"},
            hook={"composition": "closeup", "photography_style": "cinematic",
                  "lighting": "moody", "mood": "warm_cozy",
                  "subject_focus": "hands_detail"},
            all_attributes={},
        )

        context_path = tmp_path / "performance_context.json"
        # Pre-populate with existing data to verify merge
        context_path.write_text(json.dumps({"format_weights": {"habit_list": 1.5}, "sample_size": 10}))

        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.refresh_context("test", context_path)

        # Verify return value
        assert "top_performing" in result
        assert result["top_performing"].get("photography_style") == "iphone_authentic"
        assert result["top_performing"].get("lighting") == "golden_hour"

        # Verify file was written and merged
        written = json.loads(context_path.read_text())
        assert "visual_insights" in written
        assert "explore_targets" in written
        assert "exploration_ratio" in written
        assert "last_updated" in written
        # Existing data preserved
        assert written["format_weights"] == {"habit_list": 1.5}

    def test_refresh_context_empty_visuals(self, db_with_data, tmp_path):
        """refresh_context handles accounts with no visual data gracefully."""
        context_path = tmp_path / "performance_context.json"
        analyzer = AccountAnalyzer(db=db_with_data)
        result = analyzer.refresh_context("test", context_path)

        assert result["top_performing"] == {}
        assert result["sample_size"] == 0

        written = json.loads(context_path.read_text())
        assert written["exploration_ratio"] == 0.40  # <20 posts default
