"""Daily cron job: scrape metrics for all accounts."""
import importlib.util
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
        account_output = ACCOUNTS_DIR / account / "output"
        if not account_output.exists():
            # Check output_config from the module
            config_path = ACCOUNTS_DIR / account / "config.py"
            if config_path.exists():
                spec = importlib.util.spec_from_file_location(f"{account}_config", config_path)
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                output_base_str = getattr(mod, "OUTPUT_CONFIG", {}).get("base_directory")
                if output_base_str:
                    account_output = Path(output_base_str)

        if account_output.exists():
            matcher = BackfillMatcher(db=db, output_base=account_output)
            matched = matcher.backfill_account(account)
            if matched:
                logger.info(f"Backfilled {matched} posts for {account}")

    db.close()


if __name__ == "__main__":
    main()
