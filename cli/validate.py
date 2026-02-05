#!/usr/bin/env python3
"""
Configuration Validation CLI
Validates account configurations
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli.generate import load_account_config


def validate_account(account_name: str) -> bool:
    """Validate single account"""
    try:
        config, account_dir = load_account_config(account_name)

        print(f"\n✓ {account_name}")
        print(f"  Display: {config.display_name}")
        print(f"  Pillars: {len(config.content_pillars)}")
        print(f"  Colors: {len(config.color_schemes)}")
        print(f"  Output: {config.output_config.base_directory}")

        return True

    except Exception as e:
        print(f"\n❌ {account_name}")
        print(f"  Error: {e}")
        return False


def validate_all() -> tuple[int, int]:
    """Validate all accounts"""
    accounts_dir = Path(__file__).parent.parent / "accounts"
    account_dirs = [d for d in accounts_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]

    if not account_dirs:
        print("No accounts found")
        return 0, 0

    passed = 0
    failed = 0

    for account_dir in sorted(account_dirs):
        if validate_account(account_dir.name):
            passed += 1
        else:
            failed += 1

    return passed, failed


def main():
    parser = argparse.ArgumentParser(description="Validate account configurations")

    parser.add_argument(
        'account',
        nargs='?',
        help='Account name to validate (omit to validate all)'
    )

    parser.add_argument(
        '--all',
        action='store_true',
        help='Validate all accounts'
    )

    args = parser.parse_args()

    print("=" * 70)
    print("  Account Configuration Validator")
    print("=" * 70)

    if args.all or args.account is None:
        passed, failed = validate_all()
        print()
        print("=" * 70)
        print(f"Results: {passed} passed, {failed} failed")
        print("=" * 70)
        sys.exit(0 if failed == 0 else 1)
    else:
        success = validate_account(args.account)
        print()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
