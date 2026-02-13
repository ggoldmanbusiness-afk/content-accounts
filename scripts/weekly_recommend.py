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
