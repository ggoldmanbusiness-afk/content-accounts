"""
Clone Post CLI
Analyze a viral post and create a reusable format blueprint.

Usage:
    python -m cli.clone_post <url>
    python -m cli.clone_post <url> --adapt salesprofessional
    python -m cli.clone_post <url> --adapt salesprofessional --mode inspired_adaptation
    python -m cli.clone_post <url> --adapt salesprofessional --topic "cold calling"
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.post_scraper import PostScraper
from core.visual_analyzer import VisualAnalyzer
from core.format_analyzer import FormatAnalyzer
from core.copy_analyzer import CopyAnalyzer
from core.virality_analyzer import ViralityAnalyzer
from core.blueprint_adapter import BlueprintAdapter
from core.blueprint_to_template import BlueprintToTemplate

BLUEPRINTS_DIR = PROJECT_ROOT / "blueprints"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def run_analysis(url: str) -> dict:
    """Run the full analysis pipeline on a post URL.

    Returns:
        Blueprint dict ready to save.
    """
    # Step 1: Scrape
    print(f"\n{'='*60}")
    print(f"SCRAPING POST: {url}")
    print(f"{'='*60}")

    scraper = PostScraper()
    post_data = scraper.scrape_url(url)

    m = post_data["metrics"]
    print(f"\n  Author: @{post_data['author']}")
    print(f"  Platform: {post_data['platform']}")
    print(f"  Type: {post_data['content_type']}")
    print(f"  Media: {len(post_data['media_urls'])} item(s)")
    print(f"  Views: {m['views']:,} | Likes: {m['likes']:,} | Comments: {m['comments']:,}")
    print(f"  Engagement: {m['engagement_rate']:.2%}")
    print(f"  Caption: {post_data['caption'][:120]}...")

    if post_data["content_type"] == "video":
        print("\n  [VIDEO] Video analysis not yet supported (v2). Exiting.")
        sys.exit(0)

    # Step 2: Visual Analysis
    print(f"\n{'='*60}")
    print("ANALYZING VISUALS (GPT-4o)...")
    print(f"{'='*60}")

    visual = VisualAnalyzer()
    visual_analysis = visual.analyze_post(post_data["media_urls"], post_data["caption"])

    print(f"\n  Post type: {visual_analysis['post_type']}")
    print(f"  Text density: {visual_analysis['text_density']}")
    print(f"  Slides analyzed: {visual_analysis['slide_count']}")
    style = visual_analysis.get("overall_visual_style", {})
    print(f"  Aesthetic: {style.get('aesthetic', 'N/A')}")

    # Step 3: Format Analysis
    print(f"\n{'='*60}")
    print("ANALYZING FORMAT...")
    print(f"{'='*60}")

    formatter = FormatAnalyzer()
    format_analysis = formatter.analyze_format(
        visual_analysis, post_data["caption"], post_data["metrics"]
    )

    print(f"\n  Format: {format_analysis.get('format_description', 'Unknown')}")
    ia = format_analysis.get("information_architecture", {})
    print(f"  Flow: {ia.get('flow', 'N/A')}")
    print(f"  Value lives in: {ia.get('where_value_lives', 'N/A')}")

    if format_analysis.get("slide_structure"):
        for s in format_analysis["slide_structure"]:
            print(f"    Slide {s['slide_number']}: [{s['role']}] {s.get('text_template', '')}")

    # Step 4: Copy Analysis
    print(f"\n{'='*60}")
    print("ANALYZING COPY...")
    print(f"{'='*60}")

    copy_analyzer = CopyAnalyzer()
    copy_analysis = copy_analyzer.analyze_copy(visual_analysis, post_data["caption"])

    vc = copy_analysis.get("visual_copy")
    if vc:
        print(f"\n  Visual copy framework: {vc.get('primary_framework', 'None')}")
        print(f"  Techniques: {', '.join(vc.get('copy_techniques', []))}")
    cap = copy_analysis.get("caption", {})
    print(f"  Caption framework: {cap.get('primary_framework', 'None')}")
    print(f"  Hook technique: {cap.get('hook_technique', 'N/A')}")
    print(f"  CTA: {cap.get('cta_type', 'N/A')}")

    # Step 5: Virality Synthesis
    print(f"\n{'='*60}")
    print("SYNTHESIZING VIRALITY...")
    print(f"{'='*60}")

    virality = ViralityAnalyzer()
    virality_insight = virality.analyze_virality(
        post_data["metrics"], format_analysis, visual_analysis, copy_analysis
    )

    print(f"\n  Virality score: {virality_insight['virality_score']}/100")
    print(f"  Replicability: {virality_insight['replicability']}")
    for factor in virality_insight.get("key_factors", []):
        print(f"    - {factor}")

    # Step 6: Assemble Blueprint
    blueprint_id = f"{post_data['platform']}_{post_data['post_id']}"

    blueprint = {
        "blueprint_id": blueprint_id,
        "source_url": post_data["url"],
        "source_platform": post_data["platform"],
        "source_author": post_data["author"],
        "source_post_id": post_data["post_id"],
        "content_type": post_data["content_type"],
        "post_type": visual_analysis["post_type"],
        "metrics": post_data["metrics"],
        "visual_analysis": visual_analysis,
        "format_analysis": format_analysis,
        "visual_copy_analysis": copy_analysis.get("visual_copy"),
        "caption_analysis": copy_analysis.get("caption", {}),
        "virality": virality_insight,
        "tags": post_data.get("hashtags", [])[:10],
        "niche": "",
    }

    # Save
    BLUEPRINTS_DIR.mkdir(exist_ok=True)
    bp_path = BLUEPRINTS_DIR / f"{blueprint_id}.json"
    bp_path.write_text(json.dumps(blueprint, indent=2, default=str))

    print(f"\n{'='*60}")
    print(f"BLUEPRINT SAVED: {bp_path}")
    print(f"{'='*60}")

    return blueprint


def run_adaptation(blueprint: dict, account_name: str, mode: str, topic: str = ""):
    """Adapt a blueprint for a specific account."""
    print(f"\n{'='*60}")
    print(f"ADAPTING FOR: {account_name} (mode: {mode})")
    print(f"{'='*60}")

    adapter = BlueprintAdapter()
    brief = adapter.adapt(blueprint, account_name, mode=mode, topic_hint=topic)

    # Print brief
    print(f"\n  === CONTENT BRIEF ===\n")
    for s in brief.get("slides", []):
        print(f"  Slide {s['slide_number']} [{s['role']}]:")
        print(f"    Copy: {s['copy']}")
        print(f"    Visual: {s['visual_direction']}")
        print()

    cap = brief.get("caption", {})
    print(f"  Caption: {cap.get('text', '')}")
    print(f"  Hashtags: {' '.join('#' + h for h in cap.get('hashtags', []))}")

    # Save
    brief_path = BLUEPRINTS_DIR / f"{brief['brief_id']}_brief.json"
    brief_path.write_text(json.dumps(brief, indent=2, default=str))

    print(f"\n  Brief saved: {brief_path}")
    return brief


def run_register_format(blueprint: dict, format_name: str, account_name: str):
    """Register a blueprint as a reusable format template for an account."""
    print(f"\n{'='*60}")
    print(f"REGISTERING FORMAT: '{format_name}' for {account_name}")
    print(f"{'='*60}")

    converter = BlueprintToTemplate()
    template = converter.convert(blueprint, format_name, account_name)

    print(f"\n  Description: {template.get('description', 'N/A')}")
    print(f"  Source blueprint: {template.get('source_blueprint', 'N/A')}")
    print(f"  Default slides: {template.get('default_slide_count', 'N/A')}")
    print(f"  Image mode: {template.get('image_mode', 'N/A')}")
    print(f"  Caption strategy: {template.get('caption_strategy', 'N/A')}")

    structure = template.get("structure", [])
    if structure:
        print(f"\n  Slide structure:")
        for s in structure:
            print(f"    {s.get('position', '?')}: {s.get('type', '?')} (max {s.get('max_words', '?')} words)")

    templates_path = PROJECT_ROOT / "accounts" / account_name / "content_templates.json"
    print(f"\n  Registered in: {templates_path}")
    print(f"\n  Generate content with:")
    print(f"    python -m cli.generate --account {account_name} --format {format_name} --topic \"your topic\"")

    return template


def main():
    parser = argparse.ArgumentParser(
        description="Clone a viral post format into a reusable blueprint"
    )
    parser.add_argument("url", help="TikTok or Instagram post URL")
    parser.add_argument("--adapt", help="Account name to adapt for")
    parser.add_argument(
        "--mode",
        choices=["format_clone", "inspired_adaptation"],
        default="format_clone",
        help="Adaptation mode (default: format_clone)",
    )
    parser.add_argument("--topic", default="", help="Topic hint for adaptation")
    parser.add_argument(
        "--register-format",
        metavar="FORMAT_NAME",
        help="Register blueprint as reusable format template (e.g., before_after)",
    )
    parser.add_argument(
        "--account",
        help="Account to register format for (used with --register-format)",
    )
    args = parser.parse_args()

    blueprint = run_analysis(args.url)

    if args.adapt:
        run_adaptation(blueprint, args.adapt, args.mode, args.topic)

    if args.register_format:
        if not args.account and not args.adapt:
            print("❌ --account is required with --register-format", file=sys.stderr)
            sys.exit(1)
        account = args.account or args.adapt
        run_register_format(blueprint, args.register_format, account)


if __name__ == "__main__":
    main()
