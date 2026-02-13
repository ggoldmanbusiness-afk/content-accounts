import json
import logging
import os
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
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                recommendations = json.loads(response[start:end])
            else:
                logger.error(f"Failed to parse recommendations: {response[:200]}")
                return []

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
                self._merge_change(context, change)
                context["approved_recommendations"].append({
                    "id": rec["id"],
                    "insight": rec["insight"],
                    "approved_at": rec["approved_at"]
                })
            except (json.JSONDecodeError, KeyError) as e:
                logger.error(f"Failed to apply recommendation {rec['id']}: {e}")

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
