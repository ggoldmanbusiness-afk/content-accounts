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
    """Create fake output directories mimicking real structure."""
    # Content piece 1: step_guide about sleep routines
    output_dir = tmp_path / "output" / "2026" / "02-february" / "2026-02-01_sleep-routines"
    output_dir.mkdir(parents=True)

    meta = {
        "account": "dreamtimelullabies",
        "topic": "sleep routines",
        "format": "step_guide",
        "content_id": "abc123def456",
        "hook_text": "5 boring habits that fixed my baby's sleep",
        "num_items": 5,
        "hook_strategy": "viral",
        "timestamp": "2026-02-01T10:00:00",
        "output_dir": str(output_dir)
    }
    (output_dir / "meta.json").write_text(json.dumps(meta))

    carousel = {
        "slides": [{"text": "5 boring habits that fixed my baby's sleep"}],
        "image_prompts": [
            "Close-up of a peaceful baby sleeping in a cozy bedroom, soft warm golden hour "
            "light through curtains, iPhone photography, authentic candid moment, pastel blanket, "
            "gentle calm atmosphere, hands gripping stuffed animal"
        ],
        "meta": meta
    }
    (output_dir / "carousel_data.json").write_text(json.dumps(carousel))

    caption = "5 boring habits that fixed my baby's sleep schedule. which one are you trying tonight?\n\n#babysleep #sleeptips"
    (output_dir / "caption.txt").write_text(caption)

    # Content piece 2: habit_list about outdoor activities
    output_dir2 = tmp_path / "output" / "2026" / "02-february" / "2026-02-03_outdoor-activities"
    output_dir2.mkdir(parents=True)

    meta2 = {
        "account": "dreamtimelullabies",
        "topic": "outdoor activities for toddlers",
        "format": "habit_list",
        "content_id": "xyz789abc012",
        "hook_text": "5 outdoor activities that actually tire toddlers out",
        "num_items": 5,
        "hook_strategy": "viral",
        "timestamp": "2026-02-03T10:00:00",
        "output_dir": str(output_dir2)
    }
    (output_dir2 / "meta.json").write_text(json.dumps(meta2))

    carousel2 = {
        "slides": [{"text": "5 outdoor activities that actually tire toddlers out"}],
        "image_prompts": [
            "Wide shot of a toddler running across a colorful playground, energetic joyful "
            "movement, bright saturated colors, natural daylight, iPhone photography, "
            "candid authentic moment, outdoor park setting"
        ],
        "meta": meta2
    }
    (output_dir2 / "carousel_data.json").write_text(json.dumps(carousel2))

    caption2 = "that water table hack finally got me 20 minutes of peace and quiet\n\n#toddleractivities #momhacks"
    (output_dir2 / "caption.txt").write_text(caption2)

    return tmp_path / "output"


class TestBackfillMatcher:
    def test_exact_caption_match(self, db, fake_output):
        """Posts matching caption.txt content should match with high confidence."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_123",
            hook_text="5 boring habits that fixed my baby's sleep schedule. which one are you trying tonight?",
            published_at="2026-02-01T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 1

        post = db.get_post("tt_123")
        assert post["format"] == "step_guide"
        assert post["topic"] == "sleep routines"

    def test_caption_substring_match(self, db, fake_output):
        """Post caption that's a substring of the generated caption should match."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_456",
            hook_text="that water table hack finally got me 20 minutes of peace and quiet",
            published_at="2026-02-03T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 1

        post = db.get_post("tt_456")
        assert post["format"] == "habit_list"
        assert post["topic"] == "outdoor activities for toddlers"

    def test_no_match_for_unrelated_content(self, db, fake_output):
        """Completely unrelated posts should NOT match."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_999",
            hook_text="completely unrelated post about cooking pasta",
            published_at="2026-03-15T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 0

    def test_weak_topic_overlap_does_not_match(self, db, fake_output):
        """Posts with only 1-2 overlapping keywords should NOT match (threshold is 3)."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_weak",
            hook_text="my baby sleeps great now",  # only 'baby' and 'sleep' overlap
            published_at="2026-02-02T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 0

    def test_visual_extraction_during_backfill(self, db, fake_output):
        """Matching a post with image_prompts should also extract visual attributes."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_vis",
            hook_text="5 boring habits that fixed my baby's sleep schedule. which one are you trying tonight?",
            published_at="2026-02-01T10:00:00"
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 1

        visuals = db.get_post_visuals("tt_vis")
        assert visuals is not None
        assert visuals["photography_style"] == "iphone_authentic"
        assert visuals["scene_setting"] == "bedroom"

    def test_backfill_visuals_for_matched_posts(self, db, fake_output):
        """backfill_visuals() should extract visuals for already-matched posts missing visual data."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_already",
            hook_text="5 boring habits that fixed my baby's sleep schedule. which one are you trying tonight?",
            published_at="2026-02-01T10:00:00",
            format="step_guide", topic="sleep routines",
        )
        # No visuals yet
        assert db.get_post_visuals("tt_already") is None

        matcher = BackfillMatcher(db=db, output_base=fake_output)
        count = matcher.backfill_visuals("dreamtimelullabies")
        assert count == 1

        visuals = db.get_post_visuals("tt_already")
        assert visuals is not None
        assert visuals["photography_style"] is not None

    def test_already_matched_posts_skipped(self, db, fake_output):
        """Posts that already have a format should not be re-matched."""
        db.upsert_post(
            account_name="dreamtimelullabies", platform="tiktok", post_id="tt_done",
            hook_text="5 boring habits that fixed my baby's sleep",
            published_at="2026-02-01T10:00:00",
            format="habit_list",  # already matched
        )
        matcher = BackfillMatcher(db=db, output_base=fake_output)
        matched = matcher.backfill_account("dreamtimelullabies")
        assert matched == 0
