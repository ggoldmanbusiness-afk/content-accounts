#!/usr/bin/env python3
"""
Universal Content Generation CLI
Works with any account in the framework
"""

import argparse
import logging
import sys
import os
from pathlib import Path
from typing import Optional
import importlib.util

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_schema import AccountConfig
from core.generator import BaseContentGenerator


def setup_logging(verbose: bool = False):
    """Configure logging"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(message)s'
    )


def load_account_config(account_name: str) -> tuple[AccountConfig, Path, Optional[dict]]:
    """
    Dynamically load and validate account config

    Args:
        account_name: Account directory name

    Returns:
        Tuple of (validated AccountConfig, account directory path, platform_profiles or None)

    Raises:
        ValueError: If account not found or config invalid
    """
    # Find account directory
    accounts_dir = Path(__file__).parent.parent / "accounts"
    account_dir = accounts_dir / account_name

    if not account_dir.exists():
        raise ValueError(
            f"Account '{account_name}' not found in {accounts_dir}\n"
            f"Available accounts: {', '.join([d.name for d in accounts_dir.iterdir() if d.is_dir()])}"
        )

    config_path = account_dir / "config.py"
    if not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")

    # Dynamically import config module
    spec = importlib.util.spec_from_file_location(f"{account_name}_config", config_path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Failed to load config from {config_path}")

    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)

    # Extract platform profiles for scraper integration
    platform_profiles = getattr(config_module, 'PLATFORM_PROFILES', None)

    # Build AccountConfig from module
    try:
        account_config = AccountConfig(
            account_name=config_module.ACCOUNT_NAME,
            display_name=config_module.DISPLAY_NAME,
            brand_identity=config_module.BRAND_IDENTITY,
            content_pillars=config_module.CONTENT_PILLARS,
            color_schemes=[
                {"bg": scheme["bg"], "text": scheme["text"], "name": scheme["name"]}
                for scheme in config_module.COLOR_SCHEMES
            ],
            visual_style=getattr(config_module, 'VISUAL_STYLE', {}),
            hashtag_strategy=config_module.HASHTAG_STRATEGY,
            carousel_strategy=getattr(config_module, 'CAROUSEL_STRATEGY', {}),
            quality_overrides=config_module.QUALITY_OVERRIDES,
            output_config=config_module.OUTPUT_CONFIG,
            topic_tracker_config=config_module.TOPIC_TRACKER_CONFIG,
            claude_model=config_module.CLAUDE_MODEL,
            hook_formulas=getattr(config_module, 'HOOK_FORMULAS', []),
            openrouter_api_key=getattr(config_module, 'OPENROUTER_API_KEY', None),
            gemini_api_key=getattr(config_module, 'GEMINI_API_KEY', None),
            caption_cta_instruction=getattr(config_module, 'CAPTION_CTA_INSTRUCTION', ''),
            caption_cta_suffix=getattr(config_module, 'CAPTION_CTA_SUFFIX', ''),
            qa_config=getattr(config_module, 'QA_RULES', {}),
        )

        return account_config, account_dir, platform_profiles

    except Exception as e:
        raise ValueError(f"Invalid config for account '{account_name}': {e}")


def ensure_fresh_data(account_name: str, account_dir: Path, platform_profiles: Optional[dict],
                      output_base_dir: Optional[str] = None):
    """Auto-scrape + backfill + refresh context if data is stale (>1 day).

    Runs entirely from local DB + Apify. No-op if data is fresh.
    """
    from datetime import datetime, timedelta

    logger = logging.getLogger(__name__)
    project_root = Path(__file__).parent.parent
    db_path = project_root / "data" / "analytics.db"

    from core.analytics.db import AnalyticsDB
    db = AnalyticsDB(db_path)

    # Check when we last scraped for this account
    row = db.execute("""
        SELECT MAX(ms.scraped_at) as last_scraped
        FROM metrics_snapshots ms
        JOIN posts p ON ms.post_id = p.post_id
        WHERE p.account_name = ?
    """, (account_name,)).fetchone()

    last_scraped = row["last_scraped"] if row else None
    stale_threshold = datetime.now() - timedelta(days=1)

    if last_scraped:
        try:
            scraped_dt = datetime.fromisoformat(str(last_scraped).replace("Z", "+00:00"))
            # Compare naive datetimes
            if scraped_dt.tzinfo:
                scraped_dt = scraped_dt.replace(tzinfo=None)
            days_ago = (datetime.now() - scraped_dt).days
            if scraped_dt > stale_threshold:
                logger.info(f"📊 Data is fresh (last scraped {days_ago} day(s) ago) — skipping pipeline")
                db.close()
                return
            logger.info(f"📊 Data is stale (last scraped {days_ago} days ago) — running auto-refresh...")
        except (ValueError, TypeError):
            logger.info("📊 Can't parse last scrape date — running auto-refresh...")
    else:
        logger.info("📊 No scrape data found — running auto-refresh...")

    # Step 1: Scrape (if platform profiles available)
    if platform_profiles:
        try:
            from core.analytics.scraper import AccountScraper
            scraper = AccountScraper(db=db)
            for platform, username in platform_profiles.items():
                result = scraper.scrape_account(account_name, platform, username)
                new = result.get("new_posts", 0)
                updated = result.get("updated_posts", 0)
                logger.info(f"   Scraped {platform}/@{username}: {new} new, {updated} updated")
        except Exception as e:
            logger.warning(f"   Scrape failed (continuing anyway): {e}")
    else:
        logger.info("   No platform profiles configured — skipping scrape")

    # Step 2: Backfill (match scraped posts to generated content)
    try:
        from core.analytics.backfill import BackfillMatcher
        output_base = Path(output_base_dir) if output_base_dir else account_dir / "output"
        if not output_base.exists():
            output_base = account_dir / "output"

        if output_base.exists():
            matcher = BackfillMatcher(db=db, output_base=output_base)
            matched = matcher.backfill_account(account_name)
            visuals = matcher.backfill_visuals(account_name)
            logger.info(f"   Backfilled: {matched} matched, {visuals} visual extractions")
        else:
            logger.info("   No output directory found — skipping backfill")
    except Exception as e:
        logger.warning(f"   Backfill failed (continuing anyway): {e}")

    # Step 3: Refresh visual context
    try:
        from core.analytics.analyzer import AccountAnalyzer
        analyzer = AccountAnalyzer(db=db)
        context_path = account_dir / "performance_context.json"
        insights = analyzer.refresh_context(account_name, context_path)
        top_count = len(insights.get("top_performing", {}))
        logger.info(f"   Refreshed visual context: {top_count} top attributes, sample_size={insights.get('sample_size', 0)}")
    except Exception as e:
        logger.warning(f"   Context refresh failed (continuing anyway): {e}")

    db.close()


def validate_args(args) -> list[str]:
    """Validate command-line arguments"""
    errors = []

    # Topic or random required
    if not args.topic and not args.random:
        errors.append("Either --topic or --random is required")

    # Validate slide count
    if not (5 <= args.slides <= 10):
        errors.append(f"Slide count must be 5-10 (got {args.slides})")

    # Validate format (if specified) — built-in formats only checked here;
    # cloned formats from content_templates.json are validated at runtime in generator
    builtin_formats = ['habit_list', 'step_guide', 'scripts', 'boring_habits', 'how_to']
    if args.format is not None and args.format not in builtin_formats:
        # Allow through — might be a cloned format; generator will validate
        pass

    # Validate count
    if args.count < 1:
        errors.append(f"Count must be at least 1 (got {args.count})")

    return errors


def main():
    parser = argparse.ArgumentParser(
        description="Generate content for any account",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate random carousel
  python -m cli.generate --account dreamtimelullabies --random

  # Generate on specific topic
  python -m cli.generate --account myaccount --topic "bedtime routines"

  # Generate step guide with 7 slides
  python -m cli.generate --account myaccount --topic "sleep schedules" --format step_guide --slides 7

  # Batch generate 3 random carousels
  python -m cli.generate --account myaccount --random --count 3
"""
    )

    parser.add_argument(
        '--account',
        type=str,
        required=True,
        help='Account name (directory in accounts/)'
    )

    parser.add_argument(
        '--topic',
        type=str,
        help='Topic to generate content about'
    )

    parser.add_argument(
        '--format',
        type=str,
        default=None,
        help='Content format: habit_list, step_guide, scripts, boring_habits, how_to, or any cloned format name'
    )

    parser.add_argument(
        '--slides',
        type=int,
        default=5,
        help='Number of slides 5-10 (default: 5)'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=1,
        help='Number of carousels to generate (default: 1)'
    )

    parser.add_argument(
        '--random',
        action='store_true',
        help='Generate random topic from content pillars'
    )

    parser.add_argument(
        '--style',
        type=str,
        choices=['iphone_photo', 'iphone_photo_v2', 'painterly', 'painterly_v2'],
        default=None,
        help='Aesthetic style for images (default: random v2 mix)'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    parser.add_argument(
        '--qa',
        action='store_true',
        help='Run LLM image QA checks after generation (~$0.10/carousel)'
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.verbose)

    # Validate args
    errors = validate_args(args)
    if errors:
        for error in errors:
            print(f"❌ {error}", file=sys.stderr)
        sys.exit(1)

    # Load account config
    try:
        account_config, account_dir, platform_profiles = load_account_config(args.account)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Check API keys
    if not account_config.openrouter_api_key and not os.getenv("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY not found in config or environment", file=sys.stderr)
        sys.exit(1)

    # Auto-refresh data pipeline (scrape + backfill + context refresh if stale)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
    ensure_fresh_data(args.account, account_dir, platform_profiles,
                      output_base_dir=account_config.output_config.base_directory)

    # Print header
    print()
    print("=" * 70)
    print(f"  {account_config.display_name} Content Generator")
    print("=" * 70)
    print()

    # Initialize generator
    scenes_path = account_dir / "scenes.json"
    content_templates_path = account_dir / "content_templates.json"
    generator = BaseContentGenerator(
        account_config=account_config,
        scenes_path=scenes_path if scenes_path.exists() else None,
        content_templates_path=content_templates_path if content_templates_path.exists() else None,
        account_dir=account_dir,
    )

    # Set style override if specified
    if args.style:
        generator._style_override = args.style

    # Generate carousel(s)
    output_dirs = []
    qa_reports = []

    for i in range(args.count):
        try:
            if args.count > 1:
                print(f"\n📝 Generating carousel {i+1}/{args.count}...")
                print("-" * 70)

            result = generator.generate(
                topic=args.topic,
                content_format=args.format,
                num_items=args.slides,
                use_random=args.random
            )

            output_dirs.append(Path(result["output_dir"]))

            # Run LLM image QA if --qa flag set
            if args.qa:
                from core.qa_checker import CarouselQAChecker
                qa_checker = CarouselQAChecker(
                    qa_config=account_config.qa_config,
                    learnings_path=account_dir / "qa_learnings.json",
                )
                qa_report = qa_checker.check(result["output_dir"], image_qa=True)
                qa_reports.append(qa_report)
            elif "qa_report" in result:
                qa_reports.append(result["qa_report"])

        except Exception as e:
            print(f"❌ Failed to generate carousel: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            continue

    # Print summary
    print()
    print("=" * 70)
    print("  Summary")
    print("=" * 70)
    print(f"✅ Successfully generated {len(output_dirs)} carousel(s)")
    print()

    for i, output_dir in enumerate(output_dirs, 1):
        print(f"{i}. {output_dir}")

        # Show files
        caption_file = output_dir / "caption.txt"
        if caption_file.exists():
            caption = caption_file.read_text().strip()
            print(f"   Caption: {caption[:60]}..." if len(caption) > 60 else f"   Caption: {caption}")

        slides_dir = output_dir / "slides"
        if slides_dir.exists():
            slide_count = len(list(slides_dir.glob("*.png")))
            print(f"   Slides: {slide_count} images")

        print()

    # QA batch summary table
    if qa_reports:
        print("=" * 70)
        print("  QA Summary")
        print("=" * 70)

        for i, report in enumerate(qa_reports, 1):
            s = report["summary"]
            fails = [
                f"{name}: {r['message']}"
                for name, r in report["checks"].items()
                if r["status"] == "fail"
            ]
            status_str = "✅ CLEAN" if s["fail"] == 0 else f"❌ {s['fail']} FAIL"
            print(f"  {i}. {status_str}  ({s['pass']}P/{s['fail']}F/{s['warn']}W)")
            for fail in fails:
                print(f"     → {fail}")

        total_fail = sum(r["summary"]["fail"] for r in qa_reports)
        clean = sum(1 for r in qa_reports if r["summary"]["fail"] == 0)
        print()
        print(f"  {clean}/{len(qa_reports)} carousels clean, {total_fail} total failures")
        print()

    # Post-generation feedback prompt (when --qa flag set)
    if args.qa and sys.stdin.isatty():
        from core.qa_learnings import add_learning, VALID_CATEGORIES
        categories_str = "/".join(sorted(VALID_CATEGORIES))
        while True:
            issue = input("Flag any issues? (enter to skip): ").strip()
            if not issue:
                break
            category = input(f"Category [{categories_str}]: ").strip() or "other"
            add_learning(account_dir, category=category, description=issue)
            print(f"  Learning saved to {account_dir.name}/qa_learnings.json")

    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
