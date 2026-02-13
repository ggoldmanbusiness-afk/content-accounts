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
        assert "sleep_routines" in result
        assert "tantrum_management" in result

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
