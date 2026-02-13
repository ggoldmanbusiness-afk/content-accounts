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
