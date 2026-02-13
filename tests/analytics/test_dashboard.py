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
