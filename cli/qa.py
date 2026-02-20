#!/usr/bin/env python3
"""
Standalone QA Command for Carousel Generator

Usage:
  # Single carousel
  python3 -m cli.qa --dir path/to/carousel

  # All carousels for account + date
  python3 -m cli.qa --account dreamtimelullabies --date 2026-02-20

  # With LLM image review (~$0.10/carousel)
  python3 -m cli.qa --dir path/to/carousel --image-qa
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from core.qa_checker import CarouselQAChecker
from core.qa_learnings import add_learning, VALID_CATEGORIES

console = Console()

STATUS_STYLE = {
    "pass": "[bold green]PASS[/bold green]",
    "fail": "[bold red]FAIL[/bold red]",
    "warn": "[bold yellow]WARN[/bold yellow]",
}


def find_carousel_dirs(account: str, date: str) -> "list[Path]":
    """Find all carousel output directories for an account + date."""
    accounts_dir = Path(__file__).parent.parent / "accounts"
    account_dir = accounts_dir / account

    if not account_dir.exists():
        console.print(f"[red]Account '{account}' not found in {accounts_dir}[/red]")
        sys.exit(1)

    output_dir = account_dir / "output"
    if not output_dir.exists():
        console.print(f"[red]No output directory for account '{account}'[/red]")
        sys.exit(1)

    # Search for directories matching the date pattern
    matching = []
    for path in output_dir.rglob(f"{date}*"):
        if path.is_dir() and (path / "carousel_data.json").exists():
            matching.append(path)

    return sorted(matching)


def print_report(report: dict):
    """Print a single carousel's QA report with colors."""
    output_dir = report["output_dir"]
    console.print(f"\n[bold]📋 QA Report: {output_dir}[/bold]")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Check", style="cyan", min_width=25)
    table.add_column("Status", justify="center", min_width=6)
    table.add_column("Details")

    for name, result in report["checks"].items():
        status_str = STATUS_STYLE.get(result["status"], result["status"])
        table.add_row(name, status_str, result.get("message", ""))

        # Print image QA issues inline
        if name == "image_qa" and "issues" in result:
            for issue in result["issues"]:
                table.add_row("", "", f"  → {issue}")

    console.print(table)

    summary = report["summary"]
    parts = []
    if summary["pass"]:
        parts.append(f"[green]{summary['pass']} passed[/green]")
    if summary["fail"]:
        parts.append(f"[red]{summary['fail']} failed[/red]")
    if summary["warn"]:
        parts.append(f"[yellow]{summary['warn']} warnings[/yellow]")
    console.print(f"  Summary: {', '.join(parts)}")


def main():
    parser = argparse.ArgumentParser(
        description="Run QA checks on generated carousels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m cli.qa --dir path/to/carousel
  python3 -m cli.qa --account dreamtimelullabies --date 2026-02-20
  python3 -m cli.qa --account dreamtimelullabies --date 2026-02-20 --image-qa
""",
    )

    parser.add_argument("--dir", type=str, help="Path to a single carousel output directory")
    parser.add_argument("--account", type=str, help="Account name (use with --date)")
    parser.add_argument("--date", type=str, help="Date prefix to match (e.g. 2026-02-20)")
    parser.add_argument("--image-qa", action="store_true", help="Run LLM vision checks (~$0.10/carousel)")
    parser.add_argument("--feedback", action="store_true", help="Add a learning from a specific carousel")

    args = parser.parse_args()

    # Handle --feedback mode: quick add a learning
    if args.feedback:
        if not args.dir:
            parser.error("--feedback requires --dir")
        carousel_dir = Path(args.dir)
        # Read meta.json to get account name
        meta_path = carousel_dir / "meta.json"
        if not meta_path.exists():
            console.print("[red]No meta.json found in carousel directory[/red]")
            sys.exit(1)
        import json
        with open(meta_path) as f:
            meta = json.load(f)
        account_name = meta.get("account", "")
        if not account_name:
            console.print("[red]No account name in meta.json[/red]")
            sys.exit(1)
        accounts_dir = Path(__file__).parent.parent / "accounts"
        account_dir = accounts_dir / account_name

        # Get remaining args as the description
        remaining = sys.argv[sys.argv.index("--feedback") + 1:]
        # Filter out known flags
        description = " ".join(a for a in remaining if not a.startswith("--") and a != args.dir)
        if not description:
            description = input("Describe the issue: ").strip()
        if not description:
            console.print("[yellow]No description provided, skipping[/yellow]")
            sys.exit(0)

        categories_str = "/".join(sorted(VALID_CATEGORIES))
        category = input(f"Category [{categories_str}]: ").strip() or "other"

        entry = add_learning(
            account_dir, category=category, description=description,
            carousel_dir=str(carousel_dir), slide_num=0
        )
        console.print(f"[green]Learning saved to {account_dir / 'qa_learnings.json'}[/green]")
        sys.exit(0)

    # Validate args
    if not args.dir and not (args.account and args.date):
        parser.error("Either --dir or --account + --date is required")

    # Collect directories to check
    dirs = []
    if args.dir:
        d = Path(args.dir)
        if not d.exists():
            console.print(f"[red]Directory not found: {d}[/red]")
            sys.exit(1)
        dirs.append(d)
    else:
        dirs = find_carousel_dirs(args.account, args.date)
        if not dirs:
            console.print(f"[yellow]No carousels found for {args.account} on {args.date}[/yellow]")
            sys.exit(0)
        console.print(f"Found {len(dirs)} carousel(s) for {args.account} on {args.date}")

    # Load account-specific QA config if running with --account
    qa_config = None
    account_dir = None
    learnings_path = None
    if args.account:
        accounts_dir = Path(__file__).parent.parent / "accounts"
        account_dir = accounts_dir / args.account
        learnings_path = account_dir / "qa_learnings.json"
        # Try to load QA_RULES from account config
        try:
            import importlib.util
            config_path = account_dir / "config.py"
            if config_path.exists():
                spec = importlib.util.spec_from_file_location(f"{args.account}_config", config_path)
                if spec and spec.loader:
                    config_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(config_module)
                    qa_rules = getattr(config_module, 'QA_RULES', None)
                    if qa_rules:
                        from core.config_schema import QAConfig
                        qa_config = QAConfig(**qa_rules)
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load QA config: {e}[/yellow]")

    # Run QA
    checker = CarouselQAChecker(qa_config=qa_config, learnings_path=learnings_path)
    reports = checker.check_batch(dirs, image_qa=args.image_qa)

    # Print individual reports
    for report in reports:
        print_report(report)

    # Interactive review (when running with --account)
    if args.account and account_dir and sys.stdin.isatty():
        categories_str = "/".join(sorted(VALID_CATEGORIES))
        while True:
            issue = input("\nAny issues to flag? (enter to skip): ").strip()
            if not issue:
                break
            category = input(f"Category [{categories_str}]: ").strip() or "other"
            add_learning(account_dir, category=category, description=issue)
            console.print(f"[green]Learning saved to {account_dir / 'qa_learnings.json'}[/green]")
            cont = input("Flag another? (enter to skip): ").strip()
            if not cont:
                break
            # The user typed something — treat it as the next issue description
            category = input(f"Category [{categories_str}]: ").strip() or "other"
            add_learning(account_dir, category=category, description=cont)
            console.print(f"[green]Learning saved to {account_dir / 'qa_learnings.json'}[/green]")

    # Batch summary
    if len(reports) > 1:
        console.print(f"\n[bold]{'=' * 60}[/bold]")
        console.print(f"[bold]  Batch Summary: {len(reports)} carousels[/bold]")
        console.print(f"[bold]{'=' * 60}[/bold]")

        total_pass = sum(r["summary"]["pass"] for r in reports)
        total_fail = sum(r["summary"]["fail"] for r in reports)
        total_warn = sum(r["summary"]["warn"] for r in reports)
        carousels_clean = sum(1 for r in reports if r["summary"]["fail"] == 0)

        console.print(f"  Carousels clean: {carousels_clean}/{len(reports)}")
        console.print(f"  Total checks: [green]{total_pass} pass[/green], [red]{total_fail} fail[/red], [yellow]{total_warn} warn[/yellow]")

    # Exit code
    any_fail = any(r["summary"]["fail"] > 0 for r in reports)
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()
