import pytest
import sqlite3
from pathlib import Path
from core.analytics.db import AnalyticsDB


@pytest.fixture
def db(tmp_path):
    """Create a test database in a temp directory."""
    db_path = tmp_path / "test_analytics.db"
    return AnalyticsDB(db_path)


class TestSchema:
    def test_creates_tables(self, db):
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = {t[0] for t in tables}
        assert "posts" in table_names
        assert "metrics_snapshots" in table_names
        assert "recommendations" in table_names

    def test_creates_views(self, db):
        views = db.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
        view_names = {v[0] for v in views}
        assert "v_post_performance" in view_names
        assert "v_format_comparison" in view_names
        assert "v_account_summary" in view_names


class TestPostCRUD:
    def test_upsert_post(self, db):
        db.upsert_post(
            account_name="dreamtimelullabies",
            platform="tiktok",
            post_id="tt_123",
            post_url="https://tiktok.com/@test/123",
            topic="sleep routines",
            format="step_guide",
            hook_text="5 boring habits that fixed my baby's sleep",
            hook_score=16.5,
            slide_count=5,
            content_pillar="sleep_routines",
            published_at="2026-02-01T10:00:00"
        )
        post = db.get_post("tt_123")
        assert post is not None
        assert post["account_name"] == "dreamtimelullabies"
        assert post["format"] == "step_guide"
        assert post["hook_score"] == 16.5

    def test_upsert_post_updates_existing(self, db):
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_123")
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_123", topic="updated topic")
        posts = db.get_posts_for_account("test")
        assert len(posts) == 1
        assert posts[0]["topic"] == "updated topic"

    def test_get_posts_for_account(self, db):
        db.upsert_post(account_name="acct1", platform="tiktok", post_id="tt_1")
        db.upsert_post(account_name="acct2", platform="tiktok", post_id="tt_2")
        db.upsert_post(account_name="acct1", platform="instagram", post_id="ig_1")
        posts = db.get_posts_for_account("acct1")
        assert len(posts) == 2


class TestMetricsSnapshots:
    def test_insert_snapshot(self, db):
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_123")
        db.insert_snapshot(
            post_id="tt_123",
            views=10000, likes=500, comments=50,
            shares=30, saves=200
        )
        snapshots = db.get_snapshots("tt_123")
        assert len(snapshots) == 1
        assert snapshots[0]["views"] == 10000
        assert snapshots[0]["engagement_rate"] == pytest.approx((500 + 50 + 30 + 200) / 10000, rel=1e-3)

    def test_multiple_snapshots_over_time(self, db):
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_123")
        db.insert_snapshot(post_id="tt_123", views=1000, likes=50, comments=5, shares=3, saves=20)
        db.insert_snapshot(post_id="tt_123", views=5000, likes=250, comments=25, shares=15, saves=100)
        snapshots = db.get_snapshots("tt_123")
        assert len(snapshots) == 2


class TestRecommendations:
    def test_create_recommendation(self, db):
        rec_id = db.create_recommendation(
            account_name="dreamtimelullabies",
            category="format_weight",
            insight="step_guide outperforms habit_list by 2.5x on saves",
            proposed_change='{"format_weights": {"step_guide": 1.4}}',
            confidence="high"
        )
        rec = db.get_recommendation(rec_id)
        assert rec["status"] == "pending"
        assert rec["category"] == "format_weight"

    def test_approve_recommendation(self, db):
        rec_id = db.create_recommendation(
            account_name="test", category="format_weight",
            insight="test", proposed_change="{}", confidence="medium"
        )
        db.update_recommendation_status(rec_id, "approved")
        rec = db.get_recommendation(rec_id)
        assert rec["status"] == "approved"
        assert rec["approved_at"] is not None

    def test_get_pending_recommendations(self, db):
        db.create_recommendation(account_name="test", category="a", insight="1", proposed_change="{}", confidence="high")
        db.create_recommendation(account_name="test", category="b", insight="2", proposed_change="{}", confidence="medium")
        db.create_recommendation(account_name="other", category="c", insight="3", proposed_change="{}", confidence="low")
        pending = db.get_pending_recommendations("test")
        assert len(pending) == 2


class TestViews:
    def test_v_post_performance_returns_latest_snapshot(self, db):
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_1", format="step_guide")
        db.insert_snapshot(post_id="tt_1", views=1000, likes=50, comments=5, shares=3, saves=20)
        db.insert_snapshot(post_id="tt_1", views=5000, likes=250, comments=25, shares=15, saves=100)
        rows = db.execute("SELECT * FROM v_post_performance WHERE post_id = 'tt_1'").fetchall()
        assert len(rows) == 1  # Only latest snapshot

    def test_v_format_comparison(self, db):
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_1", format="step_guide")
        db.upsert_post(account_name="test", platform="tiktok", post_id="tt_2", format="habit_list")
        db.insert_snapshot(post_id="tt_1", views=10000, likes=500, comments=50, shares=30, saves=200)
        db.insert_snapshot(post_id="tt_2", views=2000, likes=50, comments=5, shares=3, saves=10)
        rows = db.execute("SELECT * FROM v_format_comparison WHERE account_name = 'test'").fetchall()
        assert len(rows) == 2
