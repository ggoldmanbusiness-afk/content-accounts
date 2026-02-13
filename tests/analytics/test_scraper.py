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
        snapshots = db.get_snapshots("7601234567890")
        assert len(snapshots) == 1
        assert snapshots[0]["views"] == 10000

    def test_scrape_all_accounts(self, db):
        """Test that scrape_all reads account configs and scrapes each."""
        scraper = AccountScraper(db=db, apify_token="test_token")
        with patch.object(scraper, "scrape_account", return_value={"new_posts": 2, "updated_posts": 0}):
            configs = {
                "dreamtimelullabies": {"tiktok": "dreamtimelullabies", "instagram": "dreamtimelullabies"},
            }
            results = scraper.scrape_all(configs)
            assert "dreamtimelullabies" in results
