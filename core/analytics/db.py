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
WHERE ms.id = (
    SELECT m2.id FROM metrics_snapshots m2 WHERE m2.post_id = p.post_id ORDER BY m2.scraped_at DESC, m2.id DESC LIMIT 1
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

CREATE TABLE IF NOT EXISTS post_visuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL UNIQUE REFERENCES posts(post_id),
    photography_style TEXT,
    lighting TEXT,
    color_palette TEXT,
    composition TEXT,
    scene_setting TEXT,
    subject_focus TEXT,
    mood TEXT,
    hook_composition TEXT,
    hook_photography_style TEXT,
    hook_lighting TEXT,
    hook_mood TEXT,
    hook_subject_focus TEXT,
    all_attributes_json TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE VIEW IF NOT EXISTS v_visual_performance AS
SELECT
    pp.*,
    pv.photography_style, pv.lighting, pv.color_palette,
    pv.composition, pv.scene_setting, pv.subject_focus, pv.mood,
    pv.hook_composition, pv.hook_photography_style,
    pv.hook_lighting, pv.hook_mood, pv.hook_subject_focus,
    pv.all_attributes_json
FROM v_post_performance pp
JOIN post_visuals pv ON pp.post_id = pv.post_id;
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

    # --- Post Visuals ---

    def upsert_post_visuals(self, post_id: str, dominant: dict, hook: dict,
                            all_attributes: dict):
        """Insert or update visual attributes for a post."""
        all_json = json.dumps(all_attributes) if all_attributes else "{}"
        existing = self.conn.execute(
            "SELECT id FROM post_visuals WHERE post_id = ?", (post_id,)
        ).fetchone()

        params = (
            dominant.get("photography_style"),
            dominant.get("lighting"),
            dominant.get("color_palette"),
            dominant.get("composition"),
            dominant.get("scene_setting"),
            dominant.get("subject_focus"),
            dominant.get("mood"),
            hook.get("composition"),
            hook.get("photography_style"),
            hook.get("lighting"),
            hook.get("mood"),
            hook.get("subject_focus"),
            all_json,
        )

        if existing:
            self.conn.execute(
                """UPDATE post_visuals SET
                    photography_style=?, lighting=?, color_palette=?,
                    composition=?, scene_setting=?, subject_focus=?, mood=?,
                    hook_composition=?, hook_photography_style=?,
                    hook_lighting=?, hook_mood=?, hook_subject_focus=?,
                    all_attributes_json=?
                WHERE post_id = ?""",
                (*params, post_id)
            )
        else:
            self.conn.execute(
                """INSERT INTO post_visuals
                    (post_id, photography_style, lighting, color_palette,
                     composition, scene_setting, subject_focus, mood,
                     hook_composition, hook_photography_style,
                     hook_lighting, hook_mood, hook_subject_focus,
                     all_attributes_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (post_id, *params)
            )
        self.conn.commit()

    def get_post_visuals(self, post_id: str) -> Optional[dict]:
        row = self.conn.execute(
            "SELECT * FROM post_visuals WHERE post_id = ?", (post_id,)
        ).fetchone()
        return dict(row) if row else None

    def get_visuals_for_account(self, account_name: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM v_visual_performance WHERE account_name = ?",
            (account_name,)
        ).fetchall()
        return [dict(r) for r in rows]
