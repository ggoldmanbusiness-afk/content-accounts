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


def load_account_config(account_name: str) -> tuple[AccountConfig, Path]:
    """
    Dynamically load and validate account config

    Args:
        account_name: Account directory name

    Returns:
        Tuple of (validated AccountConfig, account directory path)

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
            gemini_api_key=getattr(config_module, 'GEMINI_API_KEY', None)
        )

        return account_config, account_dir

    except Exception as e:
        raise ValueError(f"Invalid config for account '{account_name}': {e}")


def validate_args(args) -> list[str]:
    """Validate command-line arguments"""
    errors = []

    # Topic or random required
    if not args.topic and not args.random:
        errors.append("Either --topic or --random is required")

    # Validate slide count
    if not (5 <= args.slides <= 10):
        errors.append(f"Slide count must be 5-10 (got {args.slides})")

    # Validate format (if specified)
    valid_formats = ['habit_list', 'step_guide', 'scripts', 'boring_habits', 'how_to']
    if args.format is not None and args.format not in valid_formats:
        errors.append(f"Format must be one of {valid_formats} (got {args.format})")

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
        choices=['habit_list', 'step_guide', 'scripts', 'boring_habits', 'how_to'],
        default=None,
        help='Content format (auto-selected if not specified)'
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
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
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
        account_config, account_dir = load_account_config(args.account)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    # Check API keys
    if not account_config.openrouter_api_key and not os.getenv("OPENROUTER_API_KEY"):
        print("❌ OPENROUTER_API_KEY not found in config or environment", file=sys.stderr)
        sys.exit(1)

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
        content_templates_path=content_templates_path if content_templates_path.exists() else None
    )

    # Generate carousel(s)
    output_dirs = []

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

    print("=" * 70)
    print()


if __name__ == "__main__":
    main()
