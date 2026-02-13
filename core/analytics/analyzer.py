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

    def hook_score_correlation(self, account_name: str) -> list[dict]:
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

    def slide_count_analysis(self, account_name: str) -> list[dict]:
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
