import logging
from typing import Optional
from core.analytics.db import AnalyticsDB

logger = logging.getLogger(__name__)

PILLAR_GROUPS = {
    "Sleep & Routines": ["sleep", "bedtime", "nap", "routine", "night"],
    "Activities & Play": ["activit", "play", "sensory", "outdoor", "DIY", "cardboard", "motor", "craft"],
    "Feeding & Nutrition": ["feed", "eating", "picky", "meal", "solid", "breastfeed", "bottle", "weaning"],
    "Development": ["milestone", "development", "cognitive", "language", "social", "emotional"],
    "Behavior & Discipline": ["tantrum", "boundar", "discipline", "sibling", "behavior", "emotion"],
    "Safety & Health": ["safety", "babyproof", "car seat", "choking", "first aid", "illness", "teeth", "vaccine", "doctor"],
    "Products & Gear": ["product", "gear", "budget", "registry", "must have", "essentials"],
    "Parenting Life": ["mom", "parent", "self care", "partner", "work life", "guilt", "exhausted", "screen time"],
}


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
        """Content pillar performance breakdown, grouped into broad categories."""
        rows = self.db.execute("""
            SELECT content_pillar, views, saves, engagement_rate
            FROM v_post_performance
            WHERE account_name = ? AND content_pillar IS NOT NULL
        """, (account_name,)).fetchall()

        grouped = {}
        for row in rows:
            topic = row["content_pillar"].lower()
            group = self._classify_pillar(topic)
            if group not in grouped:
                grouped[group] = {"views": [], "saves": [], "engagement": []}
            grouped[group]["views"].append(row["views"] or 0)
            grouped[group]["saves"].append(row["saves"] or 0)
            grouped[group]["engagement"].append(row["engagement_rate"] or 0)

        result = {}
        for group, data in grouped.items():
            n = len(data["views"])
            result[group] = {
                "post_count": n,
                "avg_views": sum(data["views"]) / n if n else 0,
                "avg_saves": sum(data["saves"]) / n if n else 0,
                "avg_engagement_rate": sum(data["engagement"]) / n if n else 0,
            }
        return result

    @staticmethod
    def _classify_pillar(topic: str) -> str:
        """Map a specific topic to a broad pillar group."""
        topic_lower = topic.lower()
        for group, keywords in PILLAR_GROUPS.items():
            if any(kw.lower() in topic_lower for kw in keywords):
                return group
        return "Other"

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

    def timeline(self, account_name: str) -> list[dict]:
        """Views and engagement over time, ordered by publish date."""
        rows = self.db.execute("""
            SELECT post_id, hook_text, format, published_at, views, likes, saves, engagement_rate
            FROM v_post_performance
            WHERE account_name = ? AND published_at IS NOT NULL
            ORDER BY published_at ASC
        """, (account_name,)).fetchall()
        return [dict(r) for r in rows]

    def save_rate_analysis(self, account_name: str) -> dict:
        """Save rate (saves/views) by format — key metric for carousel content."""
        rows = self.db.execute("""
            SELECT format, views, saves
            FROM v_post_performance
            WHERE account_name = ? AND views > 0
        """, (account_name,)).fetchall()

        by_format = {}
        overall_saves = 0
        overall_views = 0
        for row in rows:
            fmt = row["format"] or "unknown"
            if fmt not in by_format:
                by_format[fmt] = {"saves": 0, "views": 0}
            by_format[fmt]["saves"] += row["saves"] or 0
            by_format[fmt]["views"] += row["views"] or 0
            overall_saves += row["saves"] or 0
            overall_views += row["views"] or 0

        result = {}
        for fmt, data in by_format.items():
            result[fmt] = round(data["saves"] / data["views"] * 100, 2) if data["views"] > 0 else 0

        return {
            "overall_save_rate": round(overall_saves / overall_views * 100, 2) if overall_views > 0 else 0,
            "by_format": result,
        }

    def posting_cadence(self, account_name: str) -> dict:
        """Posting frequency analysis."""
        rows = self.db.execute("""
            SELECT published_at FROM v_post_performance
            WHERE account_name = ? AND published_at IS NOT NULL
            ORDER BY published_at ASC
        """, (account_name,)).fetchall()

        if len(rows) < 2:
            return {"total_posts": len(rows), "avg_days_between": None, "posts_per_week": None}

        from datetime import datetime
        dates = []
        for r in rows:
            try:
                dt = datetime.fromisoformat(str(r["published_at"]).replace("Z", "+00:00"))
                dates.append(dt)
            except (ValueError, TypeError):
                continue

        if len(dates) < 2:
            return {"total_posts": len(rows), "avg_days_between": None, "posts_per_week": None}

        gaps = [(dates[i+1] - dates[i]).total_seconds() / 86400 for i in range(len(dates)-1)]
        avg_gap = sum(gaps) / len(gaps)
        span_days = (dates[-1] - dates[0]).total_seconds() / 86400
        posts_per_week = len(dates) / (span_days / 7) if span_days > 0 else 0

        return {
            "total_posts": len(dates),
            "avg_days_between": round(avg_gap, 1),
            "posts_per_week": round(posts_per_week, 1),
            "first_post": dates[0].isoformat(),
            "last_post": dates[-1].isoformat(),
        }

    def summary(self, account_name: str) -> dict:
        """Account-level summary stats."""
        rows = self.db.execute(
            "SELECT * FROM v_account_summary WHERE account_name = ?",
            (account_name,)
        ).fetchall()
        if not rows:
            return {}
        return dict(rows[0])

    def get_recommendations(self, account_name: str) -> list[dict]:
        """Get all recommendations for the dashboard."""
        rows = self.db.execute("""
            SELECT id, category, insight, proposed_change, confidence, status, created_at, approved_at
            FROM recommendations WHERE account_name = ?
            ORDER BY created_at DESC
        """, (account_name,)).fetchall()
        return [dict(r) for r in rows]

    def analyze_visuals(self, account_name: str) -> dict:
        """Visual attribute performance breakdown.

        Groups each visual attribute by value, returns avg views/saves/engagement per value.
        """
        rows = self.db.get_visuals_for_account(account_name)
        if not rows:
            return {}

        visual_attrs = [
            "photography_style", "lighting", "color_palette",
            "composition", "scene_setting", "subject_focus", "mood"
        ]
        result = {}
        for attr in visual_attrs:
            grouped = {}
            for row in rows:
                val = row.get(attr)
                if not val:
                    continue
                if val not in grouped:
                    grouped[val] = {"views": [], "saves": [], "engagement": []}
                grouped[val]["views"].append(row.get("views") or 0)
                grouped[val]["saves"].append(row.get("saves") or 0)
                grouped[val]["engagement"].append(row.get("engagement_rate") or 0)

            attr_result = {}
            for val, data in grouped.items():
                n = len(data["views"])
                attr_result[val] = {
                    "post_count": n,
                    "avg_views": sum(data["views"]) / n if n else 0,
                    "avg_saves": sum(data["saves"]) / n if n else 0,
                    "avg_engagement_rate": sum(data["engagement"]) / n if n else 0,
                }
            if attr_result:
                result[attr] = attr_result
        return result

    def analyze_hook_visuals(self, account_name: str) -> dict:
        """Hook-specific visual attribute performance.

        Same as analyze_visuals but uses hook_* columns (composition, photography_style,
        lighting, mood) since the hook slide is the scroll-stopper.
        """
        rows = self.db.get_visuals_for_account(account_name)
        if not rows:
            return {}

        hook_attrs = {
            "hook_composition": "composition",
            "hook_photography_style": "photography_style",
            "hook_lighting": "lighting",
            "hook_mood": "mood",
            "hook_subject_focus": "subject_focus",
        }
        result = {}
        for col, label in hook_attrs.items():
            grouped = {}
            for row in rows:
                val = row.get(col)
                if not val:
                    continue
                if val not in grouped:
                    grouped[val] = {"views": [], "saves": [], "engagement": []}
                grouped[val]["views"].append(row.get("views") or 0)
                grouped[val]["saves"].append(row.get("saves") or 0)
                grouped[val]["engagement"].append(row.get("engagement_rate") or 0)

            attr_result = {}
            for val, data in grouped.items():
                n = len(data["views"])
                attr_result[val] = {
                    "post_count": n,
                    "avg_views": sum(data["views"]) / n if n else 0,
                    "avg_saves": sum(data["saves"]) / n if n else 0,
                    "avg_engagement_rate": sum(data["engagement"]) / n if n else 0,
                }
            if attr_result:
                result[label] = attr_result
        return result

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
            "timeline": self.timeline(account_name),
            "save_rate": self.save_rate_analysis(account_name),
            "cadence": self.posting_cadence(account_name),
            "recommendations": self.get_recommendations(account_name),
            "visuals": self.analyze_visuals(account_name),
            "hook_visuals": self.analyze_hook_visuals(account_name),
        }

    def cross_account_report(self, account_names: list[str]) -> dict:
        """Cross-account comparison."""
        return {
            name: self.full_report(name)
            for name in account_names
        }
