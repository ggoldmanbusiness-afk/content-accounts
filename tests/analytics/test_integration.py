"""End-to-end integration test for the analytics pipeline."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.analytics.db import AnalyticsDB
from core.analytics.analyzer import AccountAnalyzer
from core.analytics.recommender import Recommender
from core.analytics.dashboard import generate_dashboard
from core.analytics.generator_integration import load_performance_context, weighted_format_choice


@pytest.fixture
def full_pipeline(tmp_path):
    """Set up a complete pipeline with test data."""
    db = AnalyticsDB(tmp_path / "test.db")

    for i in range(10):
        db.upsert_post(
            account_name="testaccount", platform="tiktok",
            post_id=f"sg_{i}", format="step_guide",
            hook_text=f"5 boring habits #{i}", hook_score=16.0,
            slide_count=5, content_pillar="sleep_routines"
        )
        db.insert_snapshot(post_id=f"sg_{i}", views=10000 + i * 1000,
                          likes=500 + i * 50, comments=50, shares=30, saves=200 + i * 20)

    for i in range(10):
        db.upsert_post(
            account_name="testaccount", platform="tiktok",
            post_id=f"hl_{i}", format="habit_list",
            hook_text=f"Stop doing this #{i}", hook_score=13.0,
            slide_count=7, content_pillar="tantrum_management"
        )
        db.insert_snapshot(post_id=f"hl_{i}", views=2000 + i * 100,
                          likes=80 + i * 5, comments=10, shares=3, saves=15)

    return db, tmp_path


class TestFullPipeline:
    def test_analyze_generates_report(self, full_pipeline):
        db, tmp_path = full_pipeline
        analyzer = AccountAnalyzer(db=db)
        report = analyzer.full_report("testaccount")

        assert report["summary"]["total_posts"] == 20
        assert "step_guide" in report["formats"]
        assert report["formats"]["step_guide"]["avg_views"] > report["formats"]["habit_list"]["avg_views"]

    @patch("core.analytics.recommender.LLMClient")
    def test_recommend_stores_in_db(self, mock_llm_cls, full_pipeline):
        db, tmp_path = full_pipeline
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.chat_completion.return_value = json.dumps([{
            "category": "format_weight",
            "insight": "step_guide 5x better",
            "proposed_change": {"format_weights": {"step_guide": 1.5}},
            "confidence": "high"
        }])

        recommender = Recommender(db=db, api_key="test_key")
        recommender.llm = mock_llm
        recs = recommender.generate_recommendations("testaccount")
        assert len(recs) == 1

        pending = db.get_pending_recommendations("testaccount")
        assert len(pending) == 1

    def test_approve_and_apply(self, full_pipeline):
        db, tmp_path = full_pipeline
        rec_id = db.create_recommendation(
            account_name="testaccount", category="format_weight",
            insight="test", proposed_change=json.dumps({"format_weights": {"step_guide": 1.5}}),
            confidence="high"
        )
        db.update_recommendation_status(rec_id, "approved")

        recommender = Recommender(db=db, api_key="test")
        context_path = tmp_path / "performance_context.json"
        recommender.apply_approved("testaccount", context_path)

        ctx = load_performance_context(context_path)
        assert ctx["format_weights"]["step_guide"] == 1.5

    def test_dashboard_generates(self, full_pipeline):
        db, tmp_path = full_pipeline
        analyzer = AccountAnalyzer(db=db)
        report = analyzer.full_report("testaccount")
        output = generate_dashboard({"testaccount": report}, output_dir=tmp_path)
        assert output.exists()
        assert "testaccount" in output.read_text()

    def test_weighted_choice_uses_context(self, full_pipeline):
        db, tmp_path = full_pipeline
        context = {"format_weights": {"step_guide": 10.0, "habit_list": 0.1}}
        counts = {}
        for _ in range(100):
            choice = weighted_format_choice(["step_guide", "habit_list"], context["format_weights"])
            counts[choice] = counts.get(choice, 0) + 1
        assert counts.get("step_guide", 0) > 80
