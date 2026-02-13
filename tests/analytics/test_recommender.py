import json
import pytest
from unittest.mock import patch, MagicMock
from core.analytics.db import AnalyticsDB
from core.analytics.analyzer import AccountAnalyzer
from core.analytics.recommender import Recommender


@pytest.fixture
def db_with_data(tmp_path):
    db = AnalyticsDB(tmp_path / "test.db")
    for i in range(10):
        db.upsert_post(account_name="test", platform="tiktok", post_id=f"sg_{i}",
                        format="step_guide", hook_score=16.0, slide_count=5,
                        content_pillar="sleep_routines")
        db.insert_snapshot(post_id=f"sg_{i}", views=10000, likes=500, comments=50, shares=30, saves=200)
    for i in range(10):
        db.upsert_post(account_name="test", platform="tiktok", post_id=f"hl_{i}",
                        format="habit_list", hook_score=14.0, slide_count=7,
                        content_pillar="tantrum_management")
        db.insert_snapshot(post_id=f"hl_{i}", views=2000, likes=50, comments=5, shares=2, saves=10)
    return db


class TestRecommender:
    @patch("core.analytics.recommender.LLMClient")
    def test_generate_recommendations(self, mock_llm_cls, db_with_data):
        mock_llm = MagicMock()
        mock_llm_cls.return_value = mock_llm
        mock_llm.chat_completion.return_value = json.dumps([
            {
                "category": "format_weight",
                "insight": "step_guide outperforms habit_list by 5x on views",
                "proposed_change": {"format_weights": {"step_guide": 1.5, "habit_list": 0.6}},
                "confidence": "high"
            }
        ])

        recommender = Recommender(db=db_with_data, api_key="test_key")
        # Manually set the mocked llm
        recommender.llm = mock_llm
        recs = recommender.generate_recommendations("test")
        assert len(recs) >= 1

        pending = db_with_data.get_pending_recommendations("test")
        assert len(pending) >= 1

    def test_apply_approved_recommendation(self, db_with_data, tmp_path):
        rec_id = db_with_data.create_recommendation(
            account_name="test",
            category="format_weight",
            insight="step_guide outperforms habit_list",
            proposed_change=json.dumps({"format_weights": {"step_guide": 1.5}}),
            confidence="high"
        )
        db_with_data.update_recommendation_status(rec_id, "approved")

        recommender = Recommender(db=db_with_data, api_key="test")
        context_path = tmp_path / "performance_context.json"
        recommender.apply_approved(account_name="test", context_path=context_path)

        context = json.loads(context_path.read_text())
        assert context["format_weights"]["step_guide"] == 1.5
