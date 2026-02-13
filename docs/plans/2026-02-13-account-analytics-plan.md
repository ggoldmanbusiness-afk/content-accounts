# Account Analytics System — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a performance analytics system that scrapes engagement metrics, analyzes what's working/failing using marketing psychology frameworks, and feeds learnings back into the content generator.

**Architecture:** SQLite database stores posts + daily metric snapshots. Apify scrapes own accounts on daily cron. Analyzer crunches data with 80/20, survivorship bias, exploration/exploitation frameworks. Recommender generates proposals via Claude. Approved recommendations update `performance_context.json` which the generator reads.

**Tech Stack:** Python, SQLite (stdlib), Apify (existing), OpenRouter/Claude (existing), Chart.js (CDN), Rich (existing)

---

### Task 1: SQLite Database Layer

**Files:**
- Create: `core/analytics/__init__.py`
- Create: `core/analytics/db.py`
- Create: `data/.gitkeep`
- Test: `tests/analytics/test_db.py`

**Step 1: Create analytics package**

```python
# core/analytics/__init__.py
```

Empty `__init__.py` to make it a package.

**Step 2: Write failing tests for database layer**

```python
# tests/analytics/test_db.py
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
```

**Step 3: Run tests to verify they fail**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'core.analytics'`

**Step 4: Implement AnalyticsDB**

```python
# core/analytics/db.py
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    platform TEXT NOT NULL DEFAULT '',
    post_id TEXT NOT NULL UNIQUE,
    post_url TEXT,
    topic TEXT,
    format TEXT,
    hook_text TEXT,
    hook_score REAL,
    slide_count INTEGER,
    content_pillar TEXT,
    published_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL REFERENCES posts(post_id),
    scraped_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    category TEXT NOT NULL,
    insight TEXT NOT NULL,
    proposed_change TEXT NOT NULL,
    confidence TEXT DEFAULT 'medium',
    approved_at DATETIME
);

CREATE VIEW IF NOT EXISTS v_post_performance AS
SELECT
    p.id, p.account_name, p.platform, p.post_id, p.post_url,
    p.topic, p.format, p.hook_text, p.hook_score, p.slide_count,
    p.content_pillar, p.published_at,
    ms.views, ms.likes, ms.comments, ms.shares, ms.saves,
    ms.engagement_rate, ms.scraped_at
FROM posts p
JOIN metrics_snapshots ms ON p.post_id = ms.post_id
WHERE ms.scraped_at = (
    SELECT MAX(m2.scraped_at) FROM metrics_snapshots m2 WHERE m2.post_id = p.post_id
);

CREATE VIEW IF NOT EXISTS v_format_comparison AS
SELECT
    account_name, format,
    COUNT(*) as post_count,
    AVG(views) as avg_views,
    AVG(likes) as avg_likes,
    AVG(saves) as avg_saves,
    AVG(engagement_rate) as avg_engagement_rate
FROM v_post_performance
GROUP BY account_name, format;

CREATE VIEW IF NOT EXISTS v_account_summary AS
SELECT
    account_name,
    COUNT(*) as total_posts,
    AVG(views) as avg_views,
    AVG(engagement_rate) as avg_engagement_rate,
    SUM(views) as total_views,
    MAX(views) as best_views
FROM v_post_performance
GROUP BY account_name;
"""


class AnalyticsDB:
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / "data" / "analytics.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def close(self):
        self.conn.close()

    # --- Posts ---

    def upsert_post(self, account_name: str, platform: str, post_id: str,
                    post_url: str = None, topic: str = None, format: str = None,
                    hook_text: str = None, hook_score: float = None,
                    slide_count: int = None, content_pillar: str = None,
                    published_at: str = None):
        existing = self.get_post(post_id)
        if existing:
            fields = {}
            for key, val in [("topic", topic), ("format", format), ("hook_text", hook_text),
                             ("hook_score", hook_score), ("slide_count", slide_count),
                             ("content_pillar", content_pillar), ("post_url", post_url),
                             ("published_at", published_at)]:
                if val is not None:
                    fields[key] = val
            if fields:
                set_clause = ", ".join(f"{k} = ?" for k in fields)
                self.conn.execute(
                    f"UPDATE posts SET {set_clause} WHERE post_id = ?",
                    (*fields.values(), post_id)
                )
                self.conn.commit()
        else:
            self.conn.execute(
                """INSERT INTO posts (account_name, platform, post_id, post_url, topic,
                   format, hook_text, hook_score, slide_count, content_pillar, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (account_name, platform, post_id, post_url, topic, format,
                 hook_text, hook_score, slide_count, content_pillar, published_at)
            )
            self.conn.commit()

    def get_post(self, post_id: str) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM posts WHERE post_id = ?", (post_id,)).fetchone()
        return dict(row) if row else None

    def get_posts_for_account(self, account_name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM posts WHERE account_name = ? ORDER BY published_at DESC",
            (account_name,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Metrics Snapshots ---

    def insert_snapshot(self, post_id: str, views: int = 0, likes: int = 0,
                        comments: int = 0, shares: int = 0, saves: int = 0):
        total_engagement = likes + comments + shares + saves
        engagement_rate = total_engagement / views if views > 0 else 0.0
        self.conn.execute(
            """INSERT INTO metrics_snapshots (post_id, views, likes, comments, shares, saves, engagement_rate)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (post_id, views, likes, comments, shares, saves, engagement_rate)
        )
        self.conn.commit()

    def get_snapshots(self, post_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM metrics_snapshots WHERE post_id = ? ORDER BY scraped_at ASC",
            (post_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    # --- Recommendations ---

    def create_recommendation(self, account_name: str, category: str,
                              insight: str, proposed_change: str,
                              confidence: str = "medium") -> int:
        cursor = self.conn.execute(
            """INSERT INTO recommendations (account_name, category, insight, proposed_change, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (account_name, category, insight, proposed_change, confidence)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_recommendation(self, rec_id: int) -> Optional[dict]:
        row = self.conn.execute("SELECT * FROM recommendations WHERE id = ?", (rec_id,)).fetchone()
        return dict(row) if row else None

    def get_pending_recommendations(self, account_name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM recommendations WHERE account_name = ? AND status = 'pending' ORDER BY created_at ASC",
            (account_name,)
        ).fetchall()
        return [dict(r) for r in rows]

    def update_recommendation_status(self, rec_id: int, status: str):
        approved_at = datetime.now().isoformat() if status == "approved" else None
        self.conn.execute(
            "UPDATE recommendations SET status = ?, approved_at = ? WHERE id = ?",
            (status, approved_at, rec_id)
        )
        self.conn.commit()
```

**Step 5: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_db.py -v`
Expected: All PASS

**Step 6: Commit**

```bash
git add core/analytics/__init__.py core/analytics/db.py tests/analytics/test_db.py data/.gitkeep
git commit -m "feat: add SQLite analytics database layer with posts, snapshots, recommendations"
```

---

### Task 2: Account Config — Add platform_profiles

**Files:**
- Modify: `core/config_schema.py` — add `platform_profiles` field
- Test: `tests/analytics/test_config.py`

**Step 1: Write failing test**

```python
# tests/analytics/test_config.py
from core.config_schema import AccountConfig


def test_platform_profiles_optional_default_empty():
    """platform_profiles should default to empty dict and not break existing configs."""
    # Minimal valid config (all required fields)
    config = AccountConfig(
        account_name="testaccount",
        display_name="Test Account",
        brand_identity={
            "character_type": "faceless_expert",
            "personality": "test",
            "value_proposition": "test",
            "voice_attributes": ["friendly"]
        },
        content_pillars=["a", "b", "c", "d", "e"],
        color_schemes=[
            {"bg": "#000000", "text": "#FFFFFF", "name": "dark"},
            {"bg": "#FFFFFF", "text": "#000000", "name": "light"},
            {"bg": "#FF0000", "text": "#FFFFFF", "name": "red"},
        ],
        hashtag_strategy={"primary": ["#test"], "secondary": ["#test2"]},
        output_config={"base_directory": "/tmp/test", "structure": "{year}/{month}"}
    )
    assert config.platform_profiles == {}


def test_platform_profiles_accepts_values():
    config = AccountConfig(
        account_name="testaccount",
        display_name="Test Account",
        brand_identity={
            "character_type": "faceless_expert",
            "personality": "test",
            "value_proposition": "test",
            "voice_attributes": ["friendly"]
        },
        content_pillars=["a", "b", "c", "d", "e"],
        color_schemes=[
            {"bg": "#000000", "text": "#FFFFFF", "name": "dark"},
            {"bg": "#FFFFFF", "text": "#000000", "name": "light"},
            {"bg": "#FF0000", "text": "#FFFFFF", "name": "red"},
        ],
        hashtag_strategy={"primary": ["#test"], "secondary": ["#test2"]},
        output_config={"base_directory": "/tmp/test", "structure": "{year}/{month}"},
        platform_profiles={"tiktok": "dreamtimelullabies", "instagram": "dreamtimelullabies"}
    )
    assert config.platform_profiles["tiktok"] == "dreamtimelullabies"
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_config.py -v`
Expected: FAIL — `platform_profiles` not recognized

**Step 3: Add platform_profiles to AccountConfig**

In `core/config_schema.py`, add to the `AccountConfig` class after `hook_formulas`:

```python
    # Platform profiles for analytics scraping
    platform_profiles: dict[str, str] = Field(
        default_factory=dict,
        description="Platform username mapping, e.g. {'tiktok': 'myaccount', 'instagram': 'myaccount'}"
    )
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_config.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/config_schema.py tests/analytics/test_config.py
git commit -m "feat: add platform_profiles field to AccountConfig for analytics scraping"
```

---

### Task 3: Apify Scraper for Own Accounts

**Files:**
- Create: `core/analytics/scraper.py`
- Test: `tests/analytics/test_scraper.py`

**Step 1: Write failing tests**

```python
# tests/analytics/test_scraper.py
import pytest
import json
from unittest.mock import patch, MagicMock
from pathlib import Path
from core.analytics.scraper import AccountScraper
from core.analytics.db import AnalyticsDB


@pytest.fixture
def db(tmp_path):
    return AnalyticsDB(tmp_path / "test.db")


@pytest.fixture
def mock_apify_tiktok_response():
    return [
        {
            "id": "7601234567890",
            "webVideoUrl": "https://www.tiktok.com/@dreamtimelullabies/video/7601234567890",
            "text": "5 boring habits that fixed my baby's sleep #babysleep",
            "createTimeISO": "2026-02-01T10:00:00.000Z",
            "statsV2": {
                "diggCount": 500,
                "commentCount": 50,
                "shareCount": 30,
                "playCount": 10000,
                "collectCount": 200
            },
            "imagePost": {"images": [{"imageURL": "url1"}, {"imageURL": "url2"}]}
        },
        {
            "id": "7601234567891",
            "webVideoUrl": "https://www.tiktok.com/@dreamtimelullabies/video/7601234567891",
            "text": "Stop saying 'good job' to your toddler",
            "createTimeISO": "2026-02-05T14:00:00.000Z",
            "statsV2": {
                "diggCount": 1200,
                "commentCount": 300,
                "shareCount": 150,
                "playCount": 50000,
                "collectCount": 800
            }
        }
    ]


class TestAccountScraper:
    @patch("core.analytics.scraper.ApifyClient")
    def test_scrape_tiktok_account(self, mock_apify_cls, db, mock_apify_tiktok_response):
        mock_client = MagicMock()
        mock_apify_cls.return_value = mock_client
        mock_dataset = MagicMock()
        mock_dataset.iterate_items.return_value = mock_apify_tiktok_response
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds_123"}
        mock_client.dataset.return_value = mock_dataset

        scraper = AccountScraper(db=db, apify_token="test_token")
        result = scraper.scrape_account("dreamtimelullabies", "tiktok", "dreamtimelullabies")

        assert result["new_posts"] == 2
        assert result["updated_posts"] == 0
        posts = db.get_posts_for_account("dreamtimelullabies")
        assert len(posts) == 2

    @patch("core.analytics.scraper.ApifyClient")
    def test_scrape_updates_existing_posts(self, mock_apify_cls, db, mock_apify_tiktok_response):
        mock_client = MagicMock()
        mock_apify_cls.return_value = mock_client
        mock_dataset = MagicMock()
        mock_dataset.iterate_items.return_value = mock_apify_tiktok_response
        mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds_123"}
        mock_client.dataset.return_value = mock_dataset

        # Pre-insert a post
        db.upsert_post(account_name="dreamtimelullabies", platform="tiktok", post_id="7601234567890")

        scraper = AccountScraper(db=db, apify_token="test_token")
        result = scraper.scrape_account("dreamtimelullabies", "tiktok", "dreamtimelullabies")

        assert result["new_posts"] == 1
        assert result["updated_posts"] == 1
        # Should have snapshot for both
        snapshots = db.get_snapshots("7601234567890")
        assert len(snapshots) == 1
        assert snapshots[0]["views"] == 10000

    def test_scrape_all_accounts(self, db):
        """Test that scrape_all reads account configs and scrapes each."""
        # This is an integration-level test, mock at the scrape_account level
        scraper = AccountScraper(db=db, apify_token="test_token")
        with patch.object(scraper, "scrape_account", return_value={"new_posts": 2, "updated_posts": 0}):
            configs = {
                "dreamtimelullabies": {"tiktok": "dreamtimelullabies", "instagram": "dreamtimelullabies"},
            }
            results = scraper.scrape_all(configs)
            assert "dreamtimelullabies" in results
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_scraper.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Implement AccountScraper**

```python
# core/analytics/scraper.py
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from apify_client import ApifyClient

from core.analytics.db import AnalyticsDB

logger = logging.getLogger(__name__)

# Same actors used in core/post_scraper.py
TIKTOK_ACTOR = "clockworks~tiktok-scraper"
INSTAGRAM_ACTOR = "apify~instagram-scraper"


class AccountScraper:
    def __init__(self, db: AnalyticsDB, apify_token: str = None):
        import os
        self.db = db
        self.apify_token = apify_token or os.environ.get("APIFY_API_TOKEN")
        if not self.apify_token:
            raise ValueError("Apify token required. Set APIFY_API_TOKEN env var or pass apify_token.")
        self.client = ApifyClient(self.apify_token)

    def scrape_account(self, account_name: str, platform: str, username: str) -> dict:
        """Scrape a single account's posts and store metrics."""
        logger.info(f"Scraping {platform}/@{username} for account {account_name}")

        if platform == "tiktok":
            posts_data = self._scrape_tiktok(username)
        elif platform == "instagram":
            posts_data = self._scrape_instagram(username)
        else:
            raise ValueError(f"Unsupported platform: {platform}")

        new_posts = 0
        updated_posts = 0

        for post in posts_data:
            post_id = post["post_id"]
            existing = self.db.get_post(post_id)

            if existing:
                updated_posts += 1
            else:
                new_posts += 1
                self.db.upsert_post(
                    account_name=account_name,
                    platform=platform,
                    post_id=post_id,
                    post_url=post.get("url"),
                    hook_text=post.get("caption", "")[:200],
                    published_at=post.get("published_at"),
                )

            # Always insert a fresh metrics snapshot
            self.db.insert_snapshot(
                post_id=post_id,
                views=post.get("views", 0),
                likes=post.get("likes", 0),
                comments=post.get("comments", 0),
                shares=post.get("shares", 0),
                saves=post.get("saves", 0),
            )

        result = {"new_posts": new_posts, "updated_posts": updated_posts}
        logger.info(f"Done: {new_posts} new, {updated_posts} updated for {account_name}/{platform}")
        return result

    def scrape_all(self, platform_profiles: dict[str, dict[str, str]]) -> dict:
        """Scrape all accounts. platform_profiles: {account_name: {platform: username}}"""
        results = {}
        for account_name, profiles in platform_profiles.items():
            results[account_name] = {}
            for platform, username in profiles.items():
                try:
                    results[account_name][platform] = self.scrape_account(account_name, platform, username)
                except Exception as e:
                    logger.error(f"Failed to scrape {account_name}/{platform}: {e}")
                    results[account_name][platform] = {"error": str(e)}
        return results

    def _scrape_tiktok(self, username: str) -> list[dict]:
        run = self.client.actor(TIKTOK_ACTOR).call(
            run_input={
                "profiles": [username],
                "resultsPerPage": 30,
                "shouldDownloadVideos": False,
            }
        )
        dataset = self.client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())

        posts = []
        for item in items:
            stats = item.get("statsV2", {})
            posts.append({
                "post_id": str(item.get("id", "")),
                "url": item.get("webVideoUrl", ""),
                "caption": item.get("text", ""),
                "published_at": item.get("createTimeISO"),
                "views": stats.get("playCount", 0),
                "likes": stats.get("diggCount", 0),
                "comments": stats.get("commentCount", 0),
                "shares": stats.get("shareCount", 0),
                "saves": stats.get("collectCount", 0),
            })
        return posts

    def _scrape_instagram(self, username: str) -> list[dict]:
        run = self.client.actor(INSTAGRAM_ACTOR).call(
            run_input={
                "usernames": [username],
                "resultsLimit": 30,
            }
        )
        dataset = self.client.dataset(run["defaultDatasetId"])
        items = list(dataset.iterate_items())

        posts = []
        for item in items:
            posts.append({
                "post_id": str(item.get("id", "")),
                "url": item.get("url", ""),
                "caption": item.get("caption", ""),
                "published_at": item.get("timestamp"),
                "views": item.get("videoViewCount", 0) or item.get("playCount", 0),
                "likes": item.get("likesCount", 0),
                "comments": item.get("commentsCount", 0),
                "shares": 0,  # Instagram doesn't expose shares via scraping
                "saves": 0,   # Instagram doesn't expose saves via scraping
            })
        return posts
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_scraper.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/analytics/scraper.py tests/analytics/test_scraper.py
git commit -m "feat: add Apify-based scraper for own account metrics"
```

---

### Task 4: Backfill — Match Scraped Posts to Generated Content

**Files:**
- Create: `core/analytics/backfill.py`
- Test: `tests/analytics/test_backfill.py`

**Step 1: Write failing tests**

```python
# tests/analytics/test_backfill.py
import json
import pytest
from pathlib import Path
from core.analytics.backfill import BackfillMatcher
from core.analytics.db import AnalyticsDB


@pytest.fixture
def db(tmp_path):
    return AnalyticsDB(tmp_path / "test.db")


@pytest.fixture
def fake_output(tmp_path):
    """Create a fake output directory mimicking real structure."""
    output_dir = tmp_path / "output" / "2026" / "02-february" / "2026-02-01_sleep-routines"
    output_dir.mkdir(parents=True)

    meta = {
        "account": "dreamtimelullabies",
        "topic": "sleep routines",
        "format": "step_guide",
        "num_items": 5,
        "hook_strategy": "viral",
        "timestamp": "2026-02-01T10:00:00",
        "output_dir": str(output_dir)
    }
    (output_dir / "meta.json").write_text(json.dumps(meta))

    carousel = {
        "slides": [{"text": "5 boring habits that fixed my baby's sleep"}],
        "meta": meta
    }
    (output_dir / "carousel_data.json").write_text(json.dumps(carousel))
    return tmp_path / "output"


class TestBackfillMatcher:
    def test_match_post_by_date_and_topic(self, db, fake_output):
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_123",
            hook_text="5 boring habits that fixed my baby's sleep",
            published_at="2026-02-01T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 1

        post = db.get_post("tt_123")
        assert post["format"] == "step_guide"
        assert post["topic"] == "sleep routines"

    def test_no_match_leaves_post_unchanged(self, db, fake_output):
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_999",
            hook_text="completely unrelated post",
            published_at="2026-03-15T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 0
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_backfill.py -v`
Expected: FAIL

**Step 3: Implement BackfillMatcher**

```python
# core/analytics/backfill.py
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.analytics.db import AnalyticsDB

logger = logging.getLogger(__name__)


class BackfillMatcher:
    """Match scraped posts to generated content in output directories."""

    def __init__(self, db: AnalyticsDB, output_base: Path):
        self.db = db
        self.output_base = output_base

    def backfill_account(self, account_name: str) -> int:
        """Try to match unmatched posts to generated content. Returns count of matched posts."""
        posts = self.db.get_posts_for_account(account_name)
        unmatched = [p for p in posts if p["format"] is None]

        if not unmatched:
            return 0

        # Index all generated content by scanning output dirs
        generated = self._index_generated_content()

        matched_count = 0
        for post in unmatched:
            match = self._find_match(post, generated)
            if match:
                self.db.upsert_post(
                    account_name=account_name,
                    platform=post["platform"],
                    post_id=post["post_id"],
                    topic=match.get("topic"),
                    format=match.get("format"),
                    hook_score=match.get("hook_score"),
                    slide_count=match.get("num_items"),
                )
                matched_count += 1
                logger.info(f"Matched post {post['post_id']} to {match.get('topic')}")

        logger.info(f"Backfill: {matched_count}/{len(unmatched)} posts matched for {account_name}")
        return matched_count

    def _index_generated_content(self) -> list[dict]:
        """Scan output directories for carousel_data.json files."""
        generated = []
        for meta_path in self.output_base.rglob("meta.json"):
            try:
                meta = json.loads(meta_path.read_text())
                carousel_path = meta_path.parent / "carousel_data.json"
                if carousel_path.exists():
                    carousel = json.loads(carousel_path.read_text())
                    hook_text = carousel.get("slides", [{}])[0].get("text", "")
                    meta["hook_text"] = hook_text
                generated.append(meta)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse {meta_path}: {e}")
        return generated

    def _find_match(self, post: dict, generated: list[dict]) -> Optional[dict]:
        """Match a post to generated content by hook text similarity."""
        post_hook = (post.get("hook_text") or "").lower().strip()
        if not post_hook:
            return None

        best_match = None
        best_score = 0.0

        for gen in generated:
            gen_hook = (gen.get("hook_text") or "").lower().strip()
            if not gen_hook:
                continue
            score = self._jaccard_similarity(post_hook, gen_hook)
            if score > best_score and score >= 0.4:
                best_score = score
                best_match = gen

        return best_match

    @staticmethod
    def _jaccard_similarity(a: str, b: str) -> float:
        stopwords = {"the", "a", "an", "is", "to", "and", "of", "in", "for", "that", "this", "my", "your"}
        words_a = {w for w in a.split() if w not in stopwords}
        words_b = {w for w in b.split() if w not in stopwords}
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_backfill.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/analytics/backfill.py tests/analytics/test_backfill.py
git commit -m "feat: add backfill matcher to link scraped posts with generated content"
```

---

### Task 5: Analyzer — Crunch Metrics Into Insights

**Files:**
- Create: `core/analytics/analyzer.py`
- Test: `tests/analytics/test_analyzer.py`

**Step 1: Write failing tests**

```python
# tests/analytics/test_analyzer.py
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
        # Should identify that step_guide drives disproportionate engagement
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
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_analyzer.py -v`
Expected: FAIL

**Step 3: Implement AccountAnalyzer**

```python
# core/analytics/analyzer.py
import logging
from typing import Optional
from core.analytics.db import AnalyticsDB

logger = logging.getLogger(__name__)


class AccountAnalyzer:
    """Analyzes account performance data using marketing psychology frameworks."""

    def __init__(self, db: AnalyticsDB):
        self.db = db

    def analyze_formats(self, account_name: str) -> dict:
        """Format performance breakdown."""
        rows = self.db.execute(
            "SELECT * FROM v_format_comparison WHERE account_name = ?",
            (account_name,)
        ).fetchall()
        return {
            row["format"]: {
                "post_count": row["post_count"],
                "avg_views": row["avg_views"],
                "avg_likes": row["avg_likes"],
                "avg_saves": row["avg_saves"],
                "avg_engagement_rate": row["avg_engagement_rate"],
            }
            for row in rows if row["format"]
        }

    def analyze_pillars(self, account_name: str) -> dict:
        """Content pillar performance breakdown."""
        rows = self.db.execute("""
            SELECT content_pillar, COUNT(*) as post_count,
                   AVG(views) as avg_views, AVG(saves) as avg_saves,
                   AVG(engagement_rate) as avg_engagement_rate
            FROM v_post_performance
            WHERE account_name = ? AND content_pillar IS NOT NULL
            GROUP BY content_pillar
        """, (account_name,)).fetchall()
        return {
            row["content_pillar"]: {
                "post_count": row["post_count"],
                "avg_views": row["avg_views"],
                "avg_saves": row["avg_saves"],
                "avg_engagement_rate": row["avg_engagement_rate"],
            }
            for row in rows
        }

    def top_posts(self, account_name: str, n: int = 5) -> list[dict]:
        """Top N posts by views."""
        rows = self.db.execute("""
            SELECT * FROM v_post_performance
            WHERE account_name = ?
            ORDER BY views DESC LIMIT ?
        """, (account_name, n)).fetchall()
        return [dict(r) for r in rows]

    def bottom_posts(self, account_name: str, n: int = 5) -> list[dict]:
        """Bottom N posts by views."""
        rows = self.db.execute("""
            SELECT * FROM v_post_performance
            WHERE account_name = ?
            ORDER BY views ASC LIMIT ?
        """, (account_name, n)).fetchall()
        return [dict(r) for r in rows]

    def pareto_analysis(self, account_name: str) -> dict:
        """80/20 analysis — which formats and pillars drive disproportionate results."""
        formats = self.analyze_formats(account_name)
        pillars = self.analyze_pillars(account_name)

        # Sort by total engagement (avg_views * post_count as proxy)
        sorted_formats = sorted(
            [{"format": k, **v} for k, v in formats.items()],
            key=lambda x: x["avg_views"] * x["post_count"],
            reverse=True
        )
        sorted_pillars = sorted(
            [{"pillar": k, **v} for k, v in pillars.items()],
            key=lambda x: x["avg_views"] * x["post_count"],
            reverse=True
        )

        return {
            "top_formats": sorted_formats,
            "top_pillars": sorted_pillars,
        }

    def hook_score_correlation(self, account_name: str) -> dict:
        """Does hook_score actually predict engagement?"""
        rows = self.db.execute("""
            SELECT hook_score, AVG(views) as avg_views,
                   AVG(engagement_rate) as avg_engagement_rate, COUNT(*) as count
            FROM v_post_performance
            WHERE account_name = ? AND hook_score IS NOT NULL
            GROUP BY CAST(hook_score AS INTEGER)
            ORDER BY hook_score
        """, (account_name,)).fetchall()
        return [dict(r) for r in rows]

    def slide_count_analysis(self, account_name: str) -> dict:
        """Performance by slide count."""
        rows = self.db.execute("""
            SELECT slide_count, AVG(views) as avg_views,
                   AVG(saves) as avg_saves, AVG(engagement_rate) as avg_engagement_rate,
                   COUNT(*) as count
            FROM v_post_performance
            WHERE account_name = ? AND slide_count IS NOT NULL
            GROUP BY slide_count ORDER BY slide_count
        """, (account_name,)).fetchall()
        return [dict(r) for r in rows]

    def summary(self, account_name: str) -> dict:
        """Account-level summary stats."""
        rows = self.db.execute(
            "SELECT * FROM v_account_summary WHERE account_name = ?",
            (account_name,)
        ).fetchall()
        if not rows:
            return {}
        return dict(rows[0])

    def full_report(self, account_name: str) -> dict:
        """Complete analysis report for an account."""
        return {
            "summary": self.summary(account_name),
            "formats": self.analyze_formats(account_name),
            "pillars": self.analyze_pillars(account_name),
            "top_posts": self.top_posts(account_name),
            "bottom_posts": self.bottom_posts(account_name),
            "pareto": self.pareto_analysis(account_name),
            "hook_correlation": self.hook_score_correlation(account_name),
            "slide_count": self.slide_count_analysis(account_name),
        }

    def cross_account_report(self, account_names: list[str]) -> dict:
        """Cross-account comparison."""
        return {
            name: self.full_report(name)
            for name in account_names
        }
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_analyzer.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/analytics/analyzer.py tests/analytics/test_analyzer.py
git commit -m "feat: add analytics analyzer with format, pillar, pareto, and hook analysis"
```

---

### Task 6: Recommender — AI-Generated Recommendations

**Files:**
- Create: `core/analytics/recommender.py`
- Test: `tests/analytics/test_recommender.py`

**Step 1: Write failing tests**

```python
# tests/analytics/test_recommender.py
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

        recommender = Recommender(db=db_with_data, api_key="test")
        recs = recommender.generate_recommendations("test")
        assert len(recs) >= 1

        # Should be stored in DB
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
```

**Step 2: Run tests to verify they fail**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_recommender.py -v`
Expected: FAIL

**Step 3: Implement Recommender**

```python
# core/analytics/recommender.py
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.analytics.db import AnalyticsDB
from core.analytics.analyzer import AccountAnalyzer
from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

RECOMMENDER_PROMPT = """You are an expert social media content strategist. Analyze this performance data and generate actionable recommendations.

## Analysis Data
{report_json}

## Frameworks to Apply
- **Pareto (80/20)**: Which 20% of formats/topics drive 80% of results?
- **Survivorship Bias**: What's failing that we should stop doing?
- **Exploration vs Exploitation**: Are we over-indexing on one format? What should we experiment with?
- **Local vs Global Optima**: Are we optimizing the wrong thing?
- **Content Pillar Rebalancing**: Which pillars deserve more/less investment?
- **Save vs Share**: Different engagement types suggest different strategies.

## Output Format
Return a JSON array of 3-5 recommendations. Each recommendation:
```json
[
  {{
    "category": "format_weight|hook_style|topic_priority|pillar_rebalance|format_experiment|failure_pattern|80_20_insight|save_vs_share|slide_count|cta_strategy",
    "insight": "Human-readable insight with specific numbers from the data",
    "proposed_change": {{}},
    "confidence": "high|medium|low"
  }}
]
```

Rules:
- Every insight MUST reference specific numbers from the data
- proposed_change should be a JSON object that can patch performance_context.json
- Only recommend changes supported by sufficient sample size (5+ posts)
- Include at least one experiment suggestion (exploration)
- Include at least one failure analysis (survivorship bias)

Return ONLY the JSON array, no other text."""


class Recommender:
    def __init__(self, db: AnalyticsDB, api_key: str = None, model: str = "anthropic/claude-sonnet-4.5"):
        import os
        self.db = db
        self.analyzer = AccountAnalyzer(db)
        api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if api_key and api_key != "test":
            self.llm = LLMClient(api_key=api_key, model=model)
        else:
            self.llm = None

    def generate_recommendations(self, account_name: str) -> list[dict]:
        """Generate AI-powered recommendations from analysis data."""
        report = self.analyzer.full_report(account_name)

        if not report.get("summary"):
            logger.warning(f"No data for {account_name}, skipping recommendations")
            return []

        prompt = RECOMMENDER_PROMPT.format(report_json=json.dumps(report, indent=2, default=str))

        response = self.llm.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )

        try:
            recommendations = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                recommendations = json.loads(response[start:end])
            else:
                logger.error(f"Failed to parse recommendations: {response[:200]}")
                return []

        # Store in DB
        stored = []
        for rec in recommendations:
            rec_id = self.db.create_recommendation(
                account_name=account_name,
                category=rec["category"],
                insight=rec["insight"],
                proposed_change=json.dumps(rec["proposed_change"]),
                confidence=rec.get("confidence", "medium")
            )
            rec["id"] = rec_id
            stored.append(rec)

        logger.info(f"Generated {len(stored)} recommendations for {account_name}")
        return stored

    def apply_approved(self, account_name: str, context_path: Path):
        """Apply all approved recommendations to performance_context.json."""
        # Load existing context or start fresh
        if context_path.exists():
            context = json.loads(context_path.read_text())
        else:
            context = {
                "last_updated": None,
                "sample_size": 0,
                "format_weights": {},
                "top_pillars": [],
                "underperforming_pillars": [],
                "optimal_slide_count": 5,
                "hook_insights": {"best_styles": [], "worst_styles": [], "reference_hooks": []},
                "save_vs_share": {"high_save_formats": [], "high_share_formats": []},
                "experiment_suggestions": [],
                "approved_recommendations": []
            }

        # Get approved recommendations not yet applied
        approved = self.db.execute("""
            SELECT * FROM recommendations
            WHERE account_name = ? AND status = 'approved'
            ORDER BY approved_at ASC
        """, (account_name,)).fetchall()

        already_applied = {r["id"] for r in context.get("approved_recommendations", [])}

        for rec in approved:
            if rec["id"] in already_applied:
                continue
            try:
                change = json.loads(rec["proposed_change"])
                # Deep merge the proposed change into context
                self._merge_change(context, change)
                context["approved_recommendations"].append({
                    "id": rec["id"],
                    "insight": rec["insight"],
                    "approved_at": rec["approved_at"]
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to apply recommendation {rec['id']}: {e}")

        # Update metadata
        summary = self.analyzer.summary(account_name)
        context["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        context["sample_size"] = summary.get("total_posts", 0)

        context_path.write_text(json.dumps(context, indent=2))
        logger.info(f"Updated performance context for {account_name}")

    @staticmethod
    def _merge_change(context: dict, change: dict):
        """Deep merge a proposed change into the context."""
        for key, value in change.items():
            if isinstance(value, dict) and isinstance(context.get(key), dict):
                context[key].update(value)
            elif isinstance(value, list) and isinstance(context.get(key), list):
                for item in value:
                    if item not in context[key]:
                        context[key].append(item)
            else:
                context[key] = value
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_recommender.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/analytics/recommender.py tests/analytics/test_recommender.py
git commit -m "feat: add AI-powered recommender with marketing psychology frameworks"
```

---

### Task 7: CLI — Analyze Command with Approval Flow

**Files:**
- Create: `cli/analyze.py`
- Test: `tests/analytics/test_cli_analyze.py`

**Step 1: Write failing test**

```python
# tests/analytics/test_cli_analyze.py
import pytest
from unittest.mock import patch, MagicMock
from cli.analyze import build_parser, load_all_platform_profiles


def test_parser_account_flag():
    parser = build_parser()
    args = parser.parse_args(["--account", "dreamtimelullabies"])
    assert args.account == "dreamtimelullabies"


def test_parser_all_flag():
    parser = build_parser()
    args = parser.parse_args(["--all"])
    assert args.all is True


def test_parser_dashboard_flag():
    parser = build_parser()
    args = parser.parse_args(["--account", "test", "--dashboard"])
    assert args.dashboard is True


def test_parser_focus_flag():
    parser = build_parser()
    args = parser.parse_args(["--account", "test", "--focus", "formats"])
    assert args.focus == "formats"


def test_parser_scrape_flag():
    parser = build_parser()
    args = parser.parse_args(["--scrape"])
    assert args.scrape is True
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_cli_analyze.py -v`
Expected: FAIL

**Step 3: Implement CLI**

```python
# cli/analyze.py
"""
Account Analytics CLI

Usage:
    python -m cli.analyze --account dreamtimelullabies          # Full report + pending approvals
    python -m cli.analyze --all                                 # Cross-account report
    python -m cli.analyze --account test --focus formats         # Focused report
    python -m cli.analyze --account test --dashboard            # Generate HTML dashboard
    python -m cli.analyze --scrape                              # Run scraper for all accounts
    python -m cli.analyze --recommend                           # Generate new recommendations
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from core.analytics.db import AnalyticsDB
from core.analytics.analyzer import AccountAnalyzer

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
ACCOUNTS_DIR = PROJECT_ROOT / "accounts"
DATA_DIR = PROJECT_ROOT / "data"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Account Analytics")
    parser.add_argument("--account", type=str, help="Account name to analyze")
    parser.add_argument("--all", action="store_true", help="Analyze all accounts")
    parser.add_argument("--focus", type=str, choices=["formats", "pillars", "hooks", "failures", "slides"],
                        help="Focus on a specific analysis dimension")
    parser.add_argument("--dashboard", action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--scrape", action="store_true", help="Run scraper for all accounts")
    parser.add_argument("--recommend", action="store_true", help="Generate new recommendations")
    return parser


def load_account_config(account_name: str):
    """Load an account config using the same pattern as cli/generate.py."""
    config_path = ACCOUNTS_DIR / account_name / "config.py"
    if not config_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"{account_name}_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_all_platform_profiles() -> dict[str, dict[str, str]]:
    """Load platform_profiles from all account configs."""
    profiles = {}
    if not ACCOUNTS_DIR.exists():
        return profiles
    for account_dir in ACCOUNTS_DIR.iterdir():
        if not account_dir.is_dir():
            continue
        module = load_account_config(account_dir.name)
        if module and hasattr(module, "PLATFORM_PROFILES"):
            profiles[account_dir.name] = module.PLATFORM_PROFILES
    return profiles


def print_report(report: dict, account_name: str):
    """Print a formatted analytics report."""
    summary = report.get("summary", {})
    if not summary:
        console.print(f"[yellow]No data for {account_name}[/yellow]")
        return

    # Summary panel
    console.print(Panel(
        f"Posts: {summary.get('total_posts', 0)} | "
        f"Avg Views: {summary.get('avg_views', 0):,.0f} | "
        f"Total Views: {summary.get('total_views', 0):,.0f} | "
        f"Avg Engagement: {summary.get('avg_engagement_rate', 0):.2%}",
        title=f"[bold]{account_name}[/bold]"
    ))

    # Format comparison table
    formats = report.get("formats", {})
    if formats:
        table = Table(title="Format Performance")
        table.add_column("Format", style="cyan")
        table.add_column("Posts", justify="right")
        table.add_column("Avg Views", justify="right")
        table.add_column("Avg Saves", justify="right")
        table.add_column("Avg Engagement", justify="right")
        for fmt, data in sorted(formats.items(), key=lambda x: x[1]["avg_views"], reverse=True):
            table.add_row(
                fmt, str(data["post_count"]),
                f"{data['avg_views']:,.0f}", f"{data['avg_saves']:,.0f}",
                f"{data['avg_engagement_rate']:.2%}"
            )
        console.print(table)

    # Top posts
    top = report.get("top_posts", [])
    if top:
        table = Table(title="Top 5 Posts")
        table.add_column("Hook", style="green", max_width=50)
        table.add_column("Format", style="cyan")
        table.add_column("Views", justify="right")
        table.add_column("Saves", justify="right")
        for post in top[:5]:
            table.add_row(
                (post.get("hook_text") or "")[:50],
                post.get("format", "?"),
                f"{post.get('views', 0):,}",
                f"{post.get('saves', 0):,}"
            )
        console.print(table)

    # Bottom posts (failure analysis)
    bottom = report.get("bottom_posts", [])
    if bottom:
        table = Table(title="Bottom 5 Posts (Failure Analysis)")
        table.add_column("Hook", style="red", max_width=50)
        table.add_column("Format", style="cyan")
        table.add_column("Views", justify="right")
        table.add_column("Saves", justify="right")
        for post in bottom[:5]:
            table.add_row(
                (post.get("hook_text") or "")[:50],
                post.get("format", "?"),
                f"{post.get('views', 0):,}",
                f"{post.get('saves', 0):,}"
            )
        console.print(table)

    # Pareto insight
    pareto = report.get("pareto", {})
    top_formats = pareto.get("top_formats", [])
    if top_formats:
        top_fmt = top_formats[0]
        console.print(f"\n[bold]80/20 Insight:[/bold] [green]{top_fmt['format']}[/green] is your top format "
                       f"with {top_fmt['avg_views']:,.0f} avg views across {top_fmt['post_count']} posts")


def handle_pending_recommendations(db: AnalyticsDB, account_name: str):
    """Interactive approval flow for pending recommendations."""
    pending = db.get_pending_recommendations(account_name)
    if not pending:
        return

    console.print(f"\n[bold yellow]You have {len(pending)} pending recommendations:[/bold yellow]\n")

    for rec in pending:
        confidence_color = {"high": "green", "medium": "yellow", "low": "red"}.get(rec["confidence"], "white")
        console.print(f"  [{confidence_color}][{rec['confidence'].upper()}][/{confidence_color}] "
                       f"[cyan]{rec['category']}[/cyan]: {rec['insight']}")
        proposed = json.loads(rec["proposed_change"]) if isinstance(rec["proposed_change"], str) else rec["proposed_change"]
        console.print(f"  Proposed: {json.dumps(proposed, indent=2)}")

        choice = Prompt.ask("  Action", choices=["y", "n", "s"], default="s")
        if choice == "y":
            db.update_recommendation_status(rec["id"], "approved")
            console.print("  [green]Approved[/green]")
        elif choice == "n":
            db.update_recommendation_status(rec["id"], "rejected")
            console.print("  [red]Rejected[/red]")
        else:
            console.print("  [dim]Skipped[/dim]")
        console.print()

    # Apply approved recommendations
    from core.analytics.recommender import Recommender
    approved_count = len([r for r in pending if db.get_recommendation(r["id"])["status"] == "approved"])
    if approved_count > 0:
        recommender = Recommender(db=db)
        context_path = ACCOUNTS_DIR / account_name / "performance_context.json"
        recommender.apply_approved(account_name, context_path)
        console.print(f"[green]Applied {approved_count} recommendations to {context_path.name}[/green]")


def main():
    parser = build_parser()
    args = parser.parse_args()
    db = AnalyticsDB(DATA_DIR / "analytics.db")

    if args.scrape:
        from core.analytics.scraper import AccountScraper
        profiles = load_all_platform_profiles()
        if not profiles:
            console.print("[yellow]No accounts with platform_profiles configured[/yellow]")
            return
        scraper = AccountScraper(db=db)
        results = scraper.scrape_all(profiles)
        for account, platforms in results.items():
            for platform, result in platforms.items():
                if "error" in result:
                    console.print(f"[red]{account}/{platform}: {result['error']}[/red]")
                else:
                    console.print(f"[green]{account}/{platform}: {result['new_posts']} new, {result['updated_posts']} updated[/green]")
        return

    if args.recommend:
        from core.analytics.recommender import Recommender
        recommender = Recommender(db=db)
        accounts = [args.account] if args.account else [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]
        for account in accounts:
            recs = recommender.generate_recommendations(account)
            console.print(f"[green]Generated {len(recs)} recommendations for {account}[/green]")
        return

    if args.dashboard:
        from core.analytics.dashboard import generate_dashboard
        analyzer = AccountAnalyzer(db=db)
        if args.all:
            accounts = [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]
            reports = {name: analyzer.full_report(name) for name in accounts}
        else:
            reports = {args.account: analyzer.full_report(args.account)}
        output_path = generate_dashboard(reports)
        console.print(f"[green]Dashboard saved to {output_path}[/green]")
        import webbrowser
        webbrowser.open(f"file://{output_path}")
        return

    if not args.account and not args.all:
        parser.print_help()
        return

    analyzer = AccountAnalyzer(db=db)

    if args.all:
        accounts = [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]
        for account in accounts:
            report = analyzer.full_report(account)
            print_report(report, account)
            console.print()
    else:
        report = analyzer.full_report(args.account)
        print_report(report, args.account)
        handle_pending_recommendations(db, args.account)


if __name__ == "__main__":
    main()
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_cli_analyze.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add cli/analyze.py tests/analytics/test_cli_analyze.py
git commit -m "feat: add analytics CLI with reports, approval flow, scrape, and recommend commands"
```

---

### Task 8: HTML Dashboard

**Files:**
- Create: `core/analytics/dashboard.py`
- Test: `tests/analytics/test_dashboard.py`

**Step 1: Write failing test**

```python
# tests/analytics/test_dashboard.py
import pytest
from pathlib import Path
from core.analytics.dashboard import generate_dashboard


def test_generates_html_file(tmp_path):
    reports = {
        "test_account": {
            "summary": {"total_posts": 10, "avg_views": 5000, "total_views": 50000, "avg_engagement_rate": 0.07, "best_views": 20000},
            "formats": {
                "step_guide": {"post_count": 5, "avg_views": 8000, "avg_likes": 400, "avg_saves": 150, "avg_engagement_rate": 0.09},
                "habit_list": {"post_count": 5, "avg_views": 2000, "avg_likes": 80, "avg_saves": 20, "avg_engagement_rate": 0.05},
            },
            "pillars": {},
            "top_posts": [],
            "bottom_posts": [],
            "pareto": {"top_formats": [], "top_pillars": []},
            "hook_correlation": [],
            "slide_count": [],
        }
    }
    output = generate_dashboard(reports, output_dir=tmp_path)
    assert output.exists()
    assert output.suffix == ".html"
    content = output.read_text()
    assert "test_account" in content
    assert "Chart" in content or "chart" in content
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_dashboard.py -v`
Expected: FAIL

**Step 3: Implement dashboard generator**

```python
# core/analytics/dashboard.py
import json
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent


def generate_dashboard(reports: dict, output_dir: Path = None) -> Path:
    """Generate a self-contained HTML dashboard from analysis reports."""
    if output_dir is None:
        output_dir = PROJECT_ROOT / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    output_path = output_dir / f"dashboard_{timestamp}.html"

    accounts_json = json.dumps(reports, default=str)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Content Analytics Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
        h1 {{ font-size: 1.8rem; margin-bottom: 1.5rem; color: #f8fafc; }}
        h2 {{ font-size: 1.3rem; margin: 1.5rem 0 1rem; color: #94a3b8; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-bottom: 2rem; }}
        .card {{ background: #1e293b; border-radius: 12px; padding: 1.5rem; border: 1px solid #334155; }}
        .stat {{ font-size: 2rem; font-weight: 700; color: #38bdf8; }}
        .stat-label {{ font-size: 0.85rem; color: #64748b; margin-top: 0.25rem; }}
        .chart-container {{ position: relative; height: 300px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #334155; }}
        th {{ color: #94a3b8; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; }}
        td {{ color: #cbd5e1; }}
        .tab-bar {{ display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }}
        .tab {{ padding: 0.5rem 1rem; border-radius: 8px; background: #1e293b; border: 1px solid #334155; cursor: pointer; color: #94a3b8; }}
        .tab.active {{ background: #38bdf8; color: #0f172a; border-color: #38bdf8; font-weight: 600; }}
        .account-section {{ display: none; }}
        .account-section.active {{ display: block; }}
    </style>
</head>
<body>
    <h1>Content Analytics Dashboard</h1>
    <div class="tab-bar" id="tabs"></div>
    <div id="content"></div>

    <script>
    const data = {accounts_json};
    const accounts = Object.keys(data);

    // Build tabs
    const tabBar = document.getElementById('tabs');
    accounts.forEach((name, i) => {{
        const tab = document.createElement('div');
        tab.className = 'tab' + (i === 0 ? ' active' : '');
        tab.textContent = name;
        tab.onclick = () => switchTab(name);
        tabBar.appendChild(tab);
    }});

    function switchTab(name) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.account-section').forEach(s => s.classList.remove('active'));
        event.target.classList.add('active');
        document.getElementById('section-' + name).classList.add('active');
    }}

    const content = document.getElementById('content');

    accounts.forEach((name, i) => {{
        const report = data[name];
        const summary = report.summary || {{}};
        const formats = report.formats || {{}};

        const section = document.createElement('div');
        section.id = 'section-' + name;
        section.className = 'account-section' + (i === 0 ? ' active' : '');

        // Summary cards
        const totalPosts = summary.total_posts || 0;
        const avgViews = Math.round(summary.avg_views || 0);
        const totalViews = summary.total_views || 0;
        const avgEng = ((summary.avg_engagement_rate || 0) * 100).toFixed(1);

        section.innerHTML = `
            <div class="grid">
                <div class="card"><div class="stat">${{totalPosts}}</div><div class="stat-label">Total Posts</div></div>
                <div class="card"><div class="stat">${{avgViews.toLocaleString()}}</div><div class="stat-label">Avg Views</div></div>
                <div class="card"><div class="stat">${{totalViews.toLocaleString()}}</div><div class="stat-label">Total Views</div></div>
                <div class="card"><div class="stat">${{avgEng}}%</div><div class="stat-label">Avg Engagement</div></div>
            </div>
            <h2>Format Performance</h2>
            <div class="card"><div class="chart-container"><canvas id="chart-formats-${{name}}"></canvas></div></div>
            <h2>Top Posts</h2>
            <div class="card">
                <table>
                    <thead><tr><th>Hook</th><th>Format</th><th>Views</th><th>Saves</th></tr></thead>
                    <tbody id="top-posts-${{name}}"></tbody>
                </table>
            </div>
            <h2>Bottom Posts</h2>
            <div class="card">
                <table>
                    <thead><tr><th>Hook</th><th>Format</th><th>Views</th><th>Saves</th></tr></thead>
                    <tbody id="bottom-posts-${{name}}"></tbody>
                </table>
            </div>
        `;
        content.appendChild(section);

        // Format chart
        const formatNames = Object.keys(formats);
        const formatViews = formatNames.map(f => Math.round(formats[f].avg_views || 0));
        const formatSaves = formatNames.map(f => Math.round(formats[f].avg_saves || 0));

        if (formatNames.length > 0) {{
            new Chart(document.getElementById('chart-formats-' + name), {{
                type: 'bar',
                data: {{
                    labels: formatNames,
                    datasets: [
                        {{ label: 'Avg Views', data: formatViews, backgroundColor: '#38bdf8' }},
                        {{ label: 'Avg Saves', data: formatSaves, backgroundColor: '#a78bfa' }}
                    ]
                }},
                options: {{
                    responsive: true, maintainAspectRatio: false,
                    scales: {{ y: {{ ticks: {{ color: '#94a3b8' }} }}, x: {{ ticks: {{ color: '#94a3b8' }} }} }},
                    plugins: {{ legend: {{ labels: {{ color: '#e2e8f0' }} }} }}
                }}
            }});
        }}

        // Top posts table
        const topBody = document.getElementById('top-posts-' + name);
        (report.top_posts || []).slice(0, 5).forEach(p => {{
            topBody.innerHTML += `<tr><td>${{(p.hook_text || '').slice(0, 60)}}</td><td>${{p.format || '?'}}</td><td>${{(p.views || 0).toLocaleString()}}</td><td>${{(p.saves || 0).toLocaleString()}}</td></tr>`;
        }});

        // Bottom posts table
        const bottomBody = document.getElementById('bottom-posts-' + name);
        (report.bottom_posts || []).slice(0, 5).forEach(p => {{
            bottomBody.innerHTML += `<tr><td>${{(p.hook_text || '').slice(0, 60)}}</td><td>${{p.format || '?'}}</td><td>${{(p.views || 0).toLocaleString()}}</td><td>${{(p.saves || 0).toLocaleString()}}</td></tr>`;
        }});
    }});
    </script>
</body>
</html>"""

    output_path.write_text(html)
    return output_path
```

**Step 4: Run tests to verify they pass**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_dashboard.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/analytics/dashboard.py tests/analytics/test_dashboard.py
git commit -m "feat: add self-contained HTML analytics dashboard with Chart.js"
```

---

### Task 9: Generator Integration — Read performance_context.json

**Files:**
- Modify: `core/generator.py` — add performance context reading
- Test: `tests/analytics/test_generator_integration.py`

**Step 1: Write failing test**

```python
# tests/analytics/test_generator_integration.py
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
    # Run multiple times to verify weighting works (step_guide should appear most)
    counts = {}
    for _ in range(1000):
        choice = weighted_format_choice(available_formats, ctx["format_weights"])
        counts[choice] = counts.get(choice, 0) + 1
    # step_guide (weight 1.5) should be chosen more than habit_list (weight 0.6)
    assert counts.get("step_guide", 0) > counts.get("habit_list", 0)
```

**Step 2: Run test to verify it fails**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_generator_integration.py -v`
Expected: FAIL

**Step 3: Create integration module**

```python
# core/analytics/generator_integration.py
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
```

**Step 4: Run test to verify it passes**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_generator_integration.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add core/analytics/generator_integration.py tests/analytics/test_generator_integration.py
git commit -m "feat: add generator integration for reading performance context"
```

**Step 6: Wire into BaseContentGenerator**

This step modifies `core/generator.py` to read `performance_context.json` during initialization and use it for format/topic selection. The exact integration points depend on the current generator code — the executing agent should:

1. In `__init__`, after loading account config, call `load_performance_context()` for the account directory
2. In the random format selection path (when `use_random=True`), use `weighted_format_choice()` instead of `random.choice()`
3. In the random topic selection path, prefer `top_pillars` from context (with ~20% chance of picking an experiment suggestion)
4. Pass `reference_hooks` to the `SemanticHookScorer` as additional examples

**Step 7: Run full test suite**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest -v`
Expected: All PASS

**Step 8: Commit**

```bash
git add core/generator.py
git commit -m "feat: wire performance context into generator for weighted format/topic selection"
```

---

### Task 10: Cron Setup + Scrape Entry Point

**Files:**
- Create: `scripts/daily_scrape.py`
- Create: `scripts/weekly_recommend.py`
- Create: `scripts/setup_cron.sh`

**Step 1: Create daily scrape script**

```python
# scripts/daily_scrape.py
"""Daily cron job: scrape metrics for all accounts."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analytics.db import AnalyticsDB
from core.analytics.scraper import AccountScraper
from core.analytics.backfill import BackfillMatcher

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ACCOUNTS_DIR = PROJECT_ROOT / "accounts"


def main():
    db = AnalyticsDB(DATA_DIR / "analytics.db")
    scraper = AccountScraper(db=db)

    # Load platform profiles from account configs
    import importlib.util
    profiles = {}
    for account_dir in ACCOUNTS_DIR.iterdir():
        if not account_dir.is_dir():
            continue
        config_path = account_dir / "config.py"
        if not config_path.exists():
            continue
        spec = importlib.util.spec_from_file_location(f"{account_dir.name}_config", config_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if hasattr(module, "PLATFORM_PROFILES"):
            profiles[account_dir.name] = module.PLATFORM_PROFILES

    if not profiles:
        logger.warning("No accounts with PLATFORM_PROFILES configured")
        return

    results = scraper.scrape_all(profiles)
    for account, platforms in results.items():
        for platform, result in platforms.items():
            if "error" in result:
                logger.error(f"{account}/{platform}: {result['error']}")
            else:
                logger.info(f"{account}/{platform}: {result['new_posts']} new, {result['updated_posts']} updated")

        # Run backfill for any unmatched posts
        output_base = account_dir / "output" if (ACCOUNTS_DIR / account / "output").exists() else None
        if output_base is None:
            # Check output_config from the module
            output_base_str = getattr(module, "OUTPUT_CONFIG", {}).get("base_directory")
            if output_base_str:
                output_base = Path(output_base_str)
        if output_base and output_base.exists():
            matcher = BackfillMatcher(db=db, output_base=output_base)
            matched = matcher.backfill_account(account)
            if matched:
                logger.info(f"Backfilled {matched} posts for {account}")

    db.close()


if __name__ == "__main__":
    main()
```

**Step 2: Create weekly recommend script**

```python
# scripts/weekly_recommend.py
"""Weekly cron job: generate recommendations for all accounts."""
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.analytics.db import AnalyticsDB
from core.analytics.recommender import Recommender

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ACCOUNTS_DIR = PROJECT_ROOT / "accounts"


def main():
    db = AnalyticsDB(DATA_DIR / "analytics.db")
    recommender = Recommender(db=db)

    for account_dir in ACCOUNTS_DIR.iterdir():
        if not account_dir.is_dir():
            continue
        name = account_dir.name
        logger.info(f"Generating recommendations for {name}")
        recs = recommender.generate_recommendations(name)
        logger.info(f"Generated {len(recs)} recommendations for {name}")

    db.close()


if __name__ == "__main__":
    main()
```

**Step 3: Create cron setup script**

```bash
#!/bin/bash
# scripts/setup_cron.sh
# Sets up launchd jobs for daily scraping and weekly recommendations

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$(which python3)"

echo "Setting up analytics cron jobs..."
echo "Project: $PROJECT_DIR"
echo "Python: $PYTHON"

# Daily scrape (8am)
SCRAPE_PLIST="$HOME/Library/LaunchAgents/com.content-accounts.daily-scrape.plist"
cat > "$SCRAPE_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.content-accounts.daily-scrape</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_DIR/scripts/daily_scrape.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>8</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/daily_scrape.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/daily_scrape_error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
EOF

# Weekly recommend (Monday 9am)
RECOMMEND_PLIST="$HOME/Library/LaunchAgents/com.content-accounts.weekly-recommend.plist"
cat > "$RECOMMEND_PLIST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.content-accounts.weekly-recommend</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$PROJECT_DIR/scripts/weekly_recommend.py</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>
    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/logs/weekly_recommend.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/logs/weekly_recommend_error.log</string>
</dict>
</plist>
EOF

mkdir -p "$PROJECT_DIR/logs"

launchctl load "$SCRAPE_PLIST"
launchctl load "$RECOMMEND_PLIST"

echo "Done! Cron jobs installed:"
echo "  - Daily scrape: 8:00 AM"
echo "  - Weekly recommend: Monday 9:00 AM"
echo ""
echo "To check status: launchctl list | grep content-accounts"
echo "To unload: launchctl unload $SCRAPE_PLIST"
```

**Step 4: Commit**

```bash
git add scripts/daily_scrape.py scripts/weekly_recommend.py scripts/setup_cron.sh
git commit -m "feat: add cron scripts for daily scraping and weekly recommendations"
```

---

### Task 11: Add PLATFORM_PROFILES to Existing Accounts

**Files:**
- Modify: `accounts/dreamtimelullabies/config.py`
- Modify: `accounts/salesprofessional/config.py` (if applicable)

**Step 1: Add PLATFORM_PROFILES to dreamtimelullabies config**

Add after existing config variables:

```python
# Platform profiles for analytics scraping
PLATFORM_PROFILES = {
    "tiktok": "dreamtimelullabies",
    "instagram": "dreamtimelullabies",
}
```

**Step 2: Update cli/generate.py load_account_config to pass platform_profiles**

In the `load_account_config` function, add:

```python
platform_profiles=getattr(config_module, 'PLATFORM_PROFILES', {}),
```

**Step 3: Commit**

```bash
git add accounts/dreamtimelullabies/config.py core/config_schema.py cli/generate.py
git commit -m "feat: add platform profiles to dreamtimelullabies for analytics scraping"
```

---

### Task 12: Integration Test — Full Pipeline

**Files:**
- Test: `tests/analytics/test_integration.py`

**Step 1: Write integration test**

```python
# tests/analytics/test_integration.py
"""End-to-end integration test for the analytics pipeline."""
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.analytics.db import AnalyticsDB
from core.analytics.scraper import AccountScraper
from core.analytics.analyzer import AccountAnalyzer
from core.analytics.recommender import Recommender
from core.analytics.dashboard import generate_dashboard
from core.analytics.generator_integration import load_performance_context, weighted_format_choice


@pytest.fixture
def full_pipeline(tmp_path):
    """Set up a complete pipeline with test data."""
    db = AnalyticsDB(tmp_path / "test.db")

    # Simulate scraped data: 20 posts across 2 formats
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
        assert counts.get("step_guide", 0) > 80  # Should be heavily weighted
```

**Step 2: Run integration test**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest tests/analytics/test_integration.py -v`
Expected: All PASS

**Step 3: Run full test suite**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add tests/analytics/test_integration.py
git commit -m "test: add end-to-end integration test for analytics pipeline"
```

---

### Task 13: Add tests/__init__.py and final cleanup

**Files:**
- Create: `tests/__init__.py` (if missing)
- Create: `tests/analytics/__init__.py`
- Update: `data/.gitignore` — ignore analytics.db but keep .gitkeep

**Step 1: Create init files and gitignore**

```python
# tests/__init__.py
# tests/analytics/__init__.py
```

```
# data/.gitignore
*.db
!.gitkeep
```

**Step 2: Run full test suite one final time**

Run: `cd /Users/grantgoldman/Documents/GitHub/content-accounts && python -m pytest -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/__init__.py tests/analytics/__init__.py data/.gitignore
git commit -m "chore: add test init files and gitignore for analytics db"
```
