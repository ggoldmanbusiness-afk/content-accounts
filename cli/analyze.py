"""
Account Analytics CLI

Usage:
    python -m cli.analyze --account dreamtimelullabies          # Full report + pending approvals
    python -m cli.analyze --all                                 # Cross-account report
    python -m cli.analyze --account test --focus formats         # Focused report
    python -m cli.analyze --account test --dashboard            # Generate HTML dashboard
    python -m cli.analyze --scrape                              # Run scraper for all accounts
    python -m cli.analyze --recommend                           # Generate new recommendations
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt

from core.analytics.db import AnalyticsDB
from core.analytics.analyzer import AccountAnalyzer

console = Console()

PROJECT_ROOT = Path(__file__).parent.parent
ACCOUNTS_DIR = PROJECT_ROOT / "accounts"
DATA_DIR = PROJECT_ROOT / "data"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Account Analytics")
    parser.add_argument("--account", type=str, help="Account name to analyze")
    parser.add_argument("--all", action="store_true", help="Analyze all accounts")
    parser.add_argument("--focus", type=str, choices=["formats", "pillars", "hooks", "failures", "slides"],
                        help="Focus on a specific analysis dimension")
    parser.add_argument("--dashboard", action="store_true", help="Generate HTML dashboard")
    parser.add_argument("--scrape", action="store_true", help="Run scraper for all accounts")
    parser.add_argument("--recommend", action="store_true", help="Generate new recommendations")
    return parser


def load_account_config(account_name: str):
    """Load an account config using the same pattern as cli/generate.py."""
    config_path = ACCOUNTS_DIR / account_name / "config.py"
    if not config_path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"{account_name}_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_all_platform_profiles() -> dict[str, dict[str, str]]:
    """Load platform_profiles from all account configs."""
    profiles = {}
    if not ACCOUNTS_DIR.exists():
        return profiles
    for account_dir in ACCOUNTS_DIR.iterdir():
        if not account_dir.is_dir():
            continue
        module = load_account_config(account_dir.name)
        if module and hasattr(module, "PLATFORM_PROFILES"):
            profiles[account_dir.name] = module.PLATFORM_PROFILES
    return profiles


def print_report(report: dict, account_name: str):
    """Print a formatted analytics report."""
    summary = report.get("summary", {})
    if not summary:
        console.print(f"[yellow]No data for {account_name}[/yellow]")
        return

    console.print(Panel(
        f"Posts: {summary.get('total_posts', 0)} | "
        f"Avg Views: {summary.get('avg_views', 0):,.0f} | "
        f"Total Views: {summary.get('total_views', 0):,.0f} | "
        f"Avg Engagement: {summary.get('avg_engagement_rate', 0):.2%}",
        title=f"[bold]{account_name}[/bold]"
    ))

    formats = report.get("formats", {})
    if formats:
        table = Table(title="Format Performance")
        table.add_column("Format", style="cyan")
        table.add_column("Posts", justify="right")
        table.add_column("Avg Views", justify="right")
        table.add_column("Avg Saves", justify="right")
        table.add_column("Avg Engagement", justify="right")
        for fmt, data in sorted(formats.items(), key=lambda x: x[1]["avg_views"], reverse=True):
            table.add_row(
                fmt, str(data["post_count"]),
                f"{data['avg_views']:,.0f}", f"{data['avg_saves']:,.0f}",
                f"{data['avg_engagement_rate']:.2%}"
            )
        console.print(table)

    top = report.get("top_posts", [])
    if top:
        table = Table(title="Top 5 Posts")
        table.add_column("Hook", style="green", max_width=50)
        table.add_column("Format", style="cyan")
        table.add_column("Views", justify="right")
        table.add_column("Saves", justify="right")
        for post in top[:5]:
            table.add_row(
                (post.get("hook_text") or "")[:50],
                post.get("format", "?"),
                f"{post.get('views', 0):,}",
                f"{post.get('saves', 0):,}"
            )
        console.print(table)

    bottom = report.get("bottom_posts", [])
    if bottom:
        table = Table(title="Bottom 5 Posts (Failure Analysis)")
        table.add_column("Hook", style="red", max_width=50)
        table.add_column("Format", style="cyan")
        table.add_column("Views", justify="right")
        table.add_column("Saves", justify="right")
        for post in bottom[:5]:
            table.add_row(
                (post.get("hook_text") or "")[:50],
                post.get("format", "?"),
                f"{post.get('views', 0):,}",
                f"{post.get('saves', 0):,}"
            )
        console.print(table)

    pareto = report.get("pareto", {})
    top_formats = pareto.get("top_formats", [])
    if top_formats:
        top_fmt = top_formats[0]
        console.print(f"\n[bold]80/20 Insight:[/bold] [green]{top_fmt['format']}[/green] is your top format "
                       f"with {top_fmt['avg_views']:,.0f} avg views across {top_fmt['post_count']} posts")


def handle_pending_recommendations(db: AnalyticsDB, account_name: str):
    """Interactive approval flow for pending recommendations."""
    pending = db.get_pending_recommendations(account_name)
    if not pending:
        return

    console.print(f"\n[bold yellow]You have {len(pending)} pending recommendations:[/bold yellow]\n")

    for rec in pending:
        confidence_color = {"high": "green", "medium": "yellow", "low": "red"}.get(rec["confidence"], "white")
        console.print(f"  [{confidence_color}][{rec['confidence'].upper()}][/{confidence_color}] "
                       f"[cyan]{rec['category']}[/cyan]: {rec['insight']}")
        proposed = json.loads(rec["proposed_change"]) if isinstance(rec["proposed_change"], str) else rec["proposed_change"]
        console.print(f"  Proposed: {json.dumps(proposed, indent=2)}")

        choice = Prompt.ask("  Action", choices=["y", "n", "s"], default="s")
        if choice == "y":
            db.update_recommendation_status(rec["id"], "approved")
            console.print("  [green]Approved[/green]")
        elif choice == "n":
            db.update_recommendation_status(rec["id"], "rejected")
            console.print("  [red]Rejected[/red]")
        else:
            console.print("  [dim]Skipped[/dim]")
        console.print()

    from core.analytics.recommender import Recommender
    approved_count = len([r for r in pending if db.get_recommendation(r["id"])["status"] == "approved"])
    if approved_count > 0:
        recommender = Recommender(db=db)
        context_path = ACCOUNTS_DIR / account_name / "performance_context.json"
        recommender.apply_approved(account_name, context_path)
        console.print(f"[green]Applied {approved_count} recommendations to {context_path.name}[/green]")


def main():
    parser = build_parser()
    args = parser.parse_args()
    db = AnalyticsDB(DATA_DIR / "analytics.db")

    if args.scrape:
        from core.analytics.scraper import AccountScraper
        profiles = load_all_platform_profiles()
        if not profiles:
            console.print("[yellow]No accounts with platform_profiles configured[/yellow]")
            return
        scraper = AccountScraper(db=db)
        results = scraper.scrape_all(profiles)
        for account, platforms in results.items():
            for platform, result in platforms.items():
                if "error" in result:
                    console.print(f"[red]{account}/{platform}: {result['error']}[/red]")
                else:
                    console.print(f"[green]{account}/{platform}: {result['new_posts']} new, {result['updated_posts']} updated[/green]")
        return

    if args.recommend:
        from core.analytics.recommender import Recommender
        recommender = Recommender(db=db)
        accounts = [args.account] if args.account else [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]
        for account in accounts:
            recs = recommender.generate_recommendations(account)
            console.print(f"[green]Generated {len(recs)} recommendations for {account}[/green]")
        return

    if args.dashboard:
        from core.analytics.dashboard import generate_dashboard
        analyzer = AccountAnalyzer(db=db)
        if args.all:
            accounts = [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]
            reports = {name: analyzer.full_report(name) for name in accounts}
        elif args.account:
            reports = {args.account: analyzer.full_report(args.account)}
        else:
            console.print("[yellow]Specify --account or --all with --dashboard[/yellow]")
            return
        output_path = generate_dashboard(reports)
        console.print(f"[green]Dashboard saved to {output_path}[/green]")
        import webbrowser
        webbrowser.open(f"file://{output_path}")
        return

    if not args.account and not args.all:
        parser.print_help()
        return

    analyzer = AccountAnalyzer(db=db)

    if args.all:
        accounts = [d.name for d in ACCOUNTS_DIR.iterdir() if d.is_dir()]
        for account in accounts:
            report = analyzer.full_report(account)
            print_report(report, account)
            console.print()
    else:
        report = analyzer.full_report(args.account)
        print_report(report, args.account)
        handle_pending_recommendations(db, args.account)


if __name__ == "__main__":
    main()
