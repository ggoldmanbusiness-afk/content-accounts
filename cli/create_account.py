#!/usr/bin/env python3
"""
Interactive Account Creation Wizard
Creates new content accounts with guided onboarding
"""

import questionary
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
import json
import shutil
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_schema import AccountConfig
from core.generator import BaseContentGenerator

console = Console()


def welcome():
    """Display welcome message"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Content Account Creation Wizard[/bold cyan]\n"
        "Create a new social media content account in 25-30 minutes\n\n"
        "[dim]This wizard will guide you through:[/dim]\n"
        "• Account setup & brand voice\n"
        "• Content strategy & pillars\n"
        "• Visual styling & hashtags\n"
        "• Sample generation & validation",
        border_style="cyan"
    ))
    console.print()


def step_1_identity() -> dict:
    """Step 1: Account Identity"""
    console.print("[bold]Step 1/9: Account Identity[/bold]", style="cyan")
    console.print()

    account_name = questionary.text(
        "Account name (lowercase, alphanumeric + underscores):",
        validate=lambda text: len(text) >= 3 and text.replace('_', '').isalnum() and text.islower()
    ).ask()

    display_name = questionary.text(
        "Display name (shown to users):",
        default=account_name.replace('_', ' ').title()
    ).ask()

    console.print(f"✓ Account: [cyan]{account_name}[/cyan] ({display_name})\n")

    return {
        "account_name": account_name,
        "display_name": display_name
    }


def step_2_brand_identity() -> dict:
    """Step 2: Brand Identity"""
    console.print("[bold]Step 2/9: Brand Identity[/bold]", style="cyan")
    console.print()

    character_type = questionary.select(
        "Account persona type:",
        choices=[
            "faceless_expert - Anonymous expert sharing knowledge",
            "personal_brand - Individual creator with personality",
            "educational_coach - Teacher/coach persona",
            "lifestyle_guide - Lifestyle inspiration account"
        ]
    ).ask().split(' - ')[0]

    personality = questionary.text(
        "Brand personality (1-2 sentences describing your voice):",
        multiline=False
    ).ask()

    value_proposition = questionary.text(
        "What value do you provide to your audience?",
        multiline=False
    ).ask()

    # Voice attributes
    all_attributes = [
        "Clear and direct",
        "Conversational and casual",
        "Evidence-based",
        "Practical and actionable",
        "Supportive and empathetic",
        "Motivational and energetic",
        "Humorous and lighthearted",
        "Professional and authoritative"
    ]

    voice_attributes = questionary.checkbox(
        "Select 3-5 voice attributes:",
        choices=all_attributes
    ).ask()

    if len(voice_attributes) < 2:
        console.print("[yellow]⚠️  Please select at least 2 attributes[/yellow]")
        return step_2_brand_identity()

    console.print(f"✓ Brand: [cyan]{character_type}[/cyan]\n")

    return {
        "character_type": character_type,
        "personality": personality,
        "value_proposition": value_proposition,
        "voice_attributes": voice_attributes
    }


def step_3_content_pillars() -> list:
    """Step 3: Content Pillars"""
    console.print("[bold]Step 3/9: Content Pillars[/bold]", style="cyan")
    console.print()

    # Load preset templates
    templates_dir = Path(__file__).parent / "templates"
    presets = {
        "parenting": "Parenting tips (baby/child care)",
        "fitness": "Fitness and workout tips",
        "cooking": "Cooking tips and recipes",
        "productivity": "Productivity and time management",
        "custom": "Start from scratch (custom pillars)"
    }

    template_choice = questionary.select(
        "Choose a content pillar template:",
        choices=list(presets.values())
    ).ask()

    template_key = [k for k, v in presets.items() if v == template_choice][0]

    if template_key != "custom":
        # Load preset pillars
        preset_file = templates_dir / f"pillars_{template_key}.json"
        with open(preset_file, 'r') as f:
            preset_data = json.load(f)
            pillars = preset_data["pillars"]

        console.print(f"\n[green]✓ Loaded {len(pillars)} pillars from {template_key} template[/green]")

        # Option to customize
        if questionary.confirm("Would you like to add/remove pillars?").ask():
            pillars = customize_pillars(pillars)
    else:
        # Manual entry
        console.print("\n[dim]Enter content pillars (topics you'll create content about)[/dim]")
        console.print("[dim]Enter at least 5 topics. Type 'done' when finished.[/dim]\n")

        pillars = []
        while True:
            pillar = questionary.text(
                f"Pillar {len(pillars) + 1} (or 'done'):"
            ).ask()

            if pillar.lower() == 'done':
                if len(pillars) >= 5:
                    break
                else:
                    console.print("[yellow]⚠️  Please enter at least 5 pillars[/yellow]")
                    continue

            pillars.append(pillar.lower().replace(' ', '_'))

    console.print(f"\n✓ {len(pillars)} content pillars configured\n")

    return pillars


def customize_pillars(initial_pillars: list) -> list:
    """Customize pillar list"""
    pillars = initial_pillars.copy()

    while True:
        action = questionary.select(
            "Customize pillars:",
            choices=[
                f"View all ({len(pillars)} pillars)",
                "Add new pillar",
                "Remove pillar",
                "Done customizing"
            ]
        ).ask()

        if "View all" in action:
            console.print(f"\n[dim]Current pillars ({len(pillars)}):[/dim]")
            for i, p in enumerate(pillars, 1):
                console.print(f"  {i}. {p}")
            console.print()

        elif "Add new" in action:
            new_pillar = questionary.text("New pillar:").ask()
            pillars.append(new_pillar.lower().replace(' ', '_'))
            console.print(f"[green]✓ Added: {new_pillar}[/green]\n")

        elif "Remove" in action:
            to_remove = questionary.autocomplete(
                "Pillar to remove:",
                choices=pillars
            ).ask()
            pillars.remove(to_remove)
            console.print(f"[yellow]✓ Removed: {to_remove}[/yellow]\n")

        else:  # Done
            if len(pillars) >= 5:
                break
            else:
                console.print("[yellow]⚠️  Need at least 5 pillars[/yellow]\n")

    return pillars


def step_4_visual_style() -> dict:
    """Step 4: Visual Style"""
    console.print("[bold]Step 4/9: Visual Style[/bold]", style="cyan")
    console.print()

    # Load color presets
    templates_dir = Path(__file__).parent / "templates"
    with open(templates_dir / "color_presets.json", 'r') as f:
        presets = json.load(f)

    preset_names = {k: f"{v['name']} - {v['description']}" for k, v in presets.items()}

    color_choice = questionary.select(
        "Choose a color palette:",
        choices=list(preset_names.values()) + ["Custom colors"]
    ).ask()

    if color_choice == "Custom colors":
        # Manual color entry
        color_schemes = []
        num_schemes = int(questionary.text(
            "How many color schemes? (3-6 recommended):",
            default="3"
        ).ask())

        for i in range(num_schemes):
            console.print(f"\n[dim]Color scheme {i+1}:[/dim]")
            bg = questionary.text(
                "Background color (hex #RRGGBB):",
                validate=lambda x: x.startswith('#') and len(x) == 7
            ).ask()
            text = questionary.text(
                "Text color (hex #RRGGBB):",
                validate=lambda x: x.startswith('#') and len(x) == 7
            ).ask()
            name = questionary.text("Scheme name:").ask()

            color_schemes.append({"bg": bg, "text": text, "name": name})
    else:
        # Use preset
        preset_key = [k for k, v in preset_names.items() if preset_names[k] == color_choice][0]
        color_schemes = presets[preset_key]["schemes"]

    console.print(f"\n✓ {len(color_schemes)} color schemes configured\n")

    return {"color_schemes": color_schemes}


def step_5_hashtags() -> dict:
    """Step 5: Hashtag Strategy"""
    console.print("[bold]Step 5/9: Hashtag Strategy[/bold]", style="cyan")
    console.print()

    console.print("[dim]Enter primary hashtags (always included in posts)[/dim]")
    primary = questionary.text(
        "Primary hashtags (comma-separated, no #):",
        instruction="e.g., fitness, workout, health"
    ).ask().split(',')
    primary = [tag.strip() for tag in primary if tag.strip()]

    console.print("\n[dim]Enter secondary hashtags (rotated/optional)[/dim]")
    secondary = questionary.text(
        "Secondary hashtags (comma-separated, no #):",
        instruction="e.g., motivation, lifestyle, tips"
    ).ask().split(',')
    secondary = [tag.strip() for tag in secondary if tag.strip()]

    max_per_post = int(questionary.text(
        "Max hashtags per post:",
        default="4"
    ).ask())

    console.print(f"\n✓ Hashtag strategy: {len(primary)} primary, {len(secondary)} secondary\n")

    return {
        "primary": primary,
        "secondary": secondary,
        "max_per_post": max_per_post,
        "style": "simple_hashtags_only"
    }


def step_6_output_config() -> dict:
    """Step 6: Output Configuration"""
    console.print("[bold]Step 6/9: Output Configuration[/bold]", style="cyan")
    console.print()

    console.print("[dim]Where should generated content be saved?[/dim]")
    console.print("[dim]Examples:[/dim]")
    console.print("[dim]  • /Users/you/Google Drive/My Drive/AccountName/[/dim]")
    console.print("[dim]  • /Users/you/Dropbox/ContentAccounts/AccountName/[/dim]")
    console.print("[dim]  • /Users/you/Documents/Content/AccountName/[/dim]\n")

    output_dir = questionary.path(
        "Output directory (absolute path):",
        only_directories=True
    ).ask()

    # Expand user path
    output_dir = os.path.expanduser(output_dir)

    # Validate path is absolute
    if not os.path.isabs(output_dir):
        console.print("[yellow]⚠️  Path must be absolute, converting...[/yellow]")
        output_dir = os.path.abspath(output_dir)

    console.print(f"\n✓ Output: [cyan]{output_dir}[/cyan]\n")

    return {
        "base_directory": output_dir,
        "structure": "{year}/{month}/{date}_{topic}",
        "include_metadata": True
    }


def step_7_api_keys() -> dict:
    """Step 7: API Keys"""
    console.print("[bold]Step 7/9: API Keys[/bold]", style="cyan")
    console.print()

    # Check environment first
    env_openrouter = os.getenv("OPENROUTER_API_KEY")
    env_gemini = os.getenv("GEMINI_API_KEY")

    if env_openrouter and env_gemini:
        use_env = questionary.confirm(
            "API keys found in environment. Use these?"
        ).ask()

        if use_env:
            console.print("[green]✓ Using environment API keys[/green]\n")
            return {"use_env": True}

    # Manual entry
    openrouter_key = questionary.password(
        "OpenRouter API key (for Claude):"
    ).ask()

    gemini_key = questionary.password(
        "Gemini API key (for image generation):"
    ).ask()

    console.print("[green]✓ API keys configured[/green]\n")

    return {
        "openrouter_api_key": openrouter_key,
        "gemini_api_key": gemini_key
    }


def step_8_review(config_data: dict) -> bool:
    """Step 8: Review & Confirm"""
    console.print("[bold]Step 8/9: Review Configuration[/bold]", style="cyan")
    console.print()

    # Create review table
    table = Table(title="Account Configuration", box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Setting", style="dim")
    table.add_column("Value")

    table.add_row("Account Name", config_data["account_name"])
    table.add_row("Display Name", config_data["display_name"])
    table.add_row("Character Type", config_data["brand_identity"]["character_type"])
    table.add_row("Content Pillars", f"{len(config_data['content_pillars'])} topics")
    table.add_row("Color Schemes", f"{len(config_data['color_schemes'])} palettes")
    table.add_row("Primary Hashtags", ", ".join(config_data["hashtag_strategy"]["primary"][:5]))
    table.add_row("Output Directory", config_data["output_config"]["base_directory"])

    console.print(table)
    console.print()

    return questionary.confirm(
        "Does everything look correct?",
        default=True
    ).ask()


def step_9_generate_samples(account_dir: Path, config: AccountConfig):
    """Step 9: Generate Sample Carousels"""
    console.print("[bold]Step 9/9: Generate Sample Carousels[/bold]", style="cyan")
    console.print()
    console.print("[dim]Generating 3 sample carousels to validate your configuration...[/dim]\n")

    try:
        # Initialize generator
        scenes_path = account_dir / "scenes.json"
        generator = BaseContentGenerator(
            account_config=config,
            scenes_path=scenes_path if scenes_path.exists() else None
        )

        # Generate 3 samples
        for i in range(3):
            console.print(f"[cyan]Generating sample {i+1}/3...[/cyan]")

            result = generator.generate(
                use_random=True,
                num_items=5
            )

            console.print(f"  ✓ Created: {Path(result['output_dir']).name}")

        console.print()
        console.print("[green]✓ Sample generation complete![/green]\n")
        return True

    except Exception as e:
        console.print(f"[red]❌ Sample generation failed: {e}[/red]\n")
        return False


def create_account_files(config_data: dict) -> Path:
    """Create account directory and files"""
    account_name = config_data["account_name"]

    # Create account directory
    accounts_dir = Path(__file__).parent.parent / "accounts"
    account_dir = accounts_dir / account_name

    if account_dir.exists():
        overwrite = questionary.confirm(
            f"Account '{account_name}' already exists. Overwrite?",
            default=False
        ).ask()

        if not overwrite:
            console.print("[yellow]Cancelled[/yellow]")
            sys.exit(0)

        shutil.rmtree(account_dir)

    account_dir.mkdir(parents=True, exist_ok=True)

    # Load config template
    templates_dir = Path(__file__).parent / "templates"
    with open(templates_dir / "config_template.py", 'r') as f:
        config_template = f.read()

    # Format template
    config_content = config_template.format(
        ACCOUNT_NAME=config_data["account_name"],
        DISPLAY_NAME=config_data["display_name"],
        CHARACTER_TYPE=config_data["brand_identity"]["character_type"],
        PERSONALITY=config_data["brand_identity"]["personality"],
        VALUE_PROPOSITION=config_data["brand_identity"]["value_proposition"],
        VOICE_ATTRIBUTES=json.dumps(config_data["brand_identity"]["voice_attributes"], indent=4),
        CONTENT_PILLARS=json.dumps(config_data["content_pillars"], indent=4),
        PILLAR_COUNT=len(config_data["content_pillars"]),
        MIN_HOOK_SCORE=12,
        MAX_WORDS_PER_SLIDE=20,
        PRIMARY_HASHTAGS=json.dumps(config_data["hashtag_strategy"]["primary"]),
        SECONDARY_HASHTAGS=json.dumps(config_data["hashtag_strategy"]["secondary"]),
        MAX_HASHTAGS=config_data["hashtag_strategy"]["max_per_post"],
        COLOR_SCHEMES=json.dumps(config_data["color_schemes"], indent=4),
        COLOR_SCHEME_COUNT=len(config_data["color_schemes"]),
        OUTPUT_DIRECTORY=config_data["output_config"]["base_directory"]
    )

    # Write config.py
    (account_dir / "config.py").write_text(config_content)

    # Copy scenes.json and content_templates.json
    shutil.copy(templates_dir / "scenes_template.json", account_dir / "scenes.json")
    shutil.copy(templates_dir / "content_templates.json", account_dir / "content_templates.json")

    # Create .env if keys provided
    if config_data.get("api_keys") and not config_data["api_keys"].get("use_env"):
        env_content = f"""# API Keys for {account_name}
OPENROUTER_API_KEY={config_data["api_keys"]["openrouter_api_key"]}
GEMINI_API_KEY={config_data["api_keys"]["gemini_api_key"]}
"""
        (account_dir / ".env").write_text(env_content)

    # Create README
    readme_content = f"""# {config_data["display_name"]}

{config_data["brand_identity"]["value_proposition"]}

## Account Info

- **Account Name**: {account_name}
- **Character Type**: {config_data["brand_identity"]["character_type"]}
- **Content Pillars**: {len(config_data["content_pillars"])} topics

## Generate Content

```bash
# Random carousel
python -m cli.generate --account {account_name} --random

# Specific topic
python -m cli.generate --account {account_name} --topic "your topic"

# Batch generation
python -m cli.generate --account {account_name} --random --count 5
```

## Output

Content saved to: `{config_data["output_config"]["base_directory"]}`
"""

    (account_dir / "README.md").write_text(readme_content)

    return account_dir


def main():
    """Main wizard flow"""
    welcome()

    # Collect configuration
    config_data = {}

    # Step 1: Identity
    config_data.update(step_1_identity())

    # Step 2: Brand
    config_data["brand_identity"] = step_2_brand_identity()

    # Step 3: Content Pillars
    config_data["content_pillars"] = step_3_content_pillars()

    # Step 4: Visual Style
    visual_data = step_4_visual_style()
    config_data["color_schemes"] = visual_data["color_schemes"]

    # Step 5: Hashtags
    config_data["hashtag_strategy"] = step_5_hashtags()

    # Step 6: Output
    config_data["output_config"] = step_6_output_config()

    # Step 7: API Keys
    config_data["api_keys"] = step_7_api_keys()

    # Step 8: Review
    if not step_8_review(config_data):
        console.print("[yellow]Configuration cancelled. Please run the wizard again.[/yellow]")
        sys.exit(0)

    # Create account files
    console.print("\n[cyan]Creating account files...[/cyan]")
    account_dir = create_account_files(config_data)
    console.print(f"[green]✓ Account created: {account_dir}[/green]\n")

    # Validate config
    console.print("[cyan]Validating configuration...[/cyan]")
    try:
        # Import and validate
        sys.path.insert(0, str(account_dir))
        import config as account_config

        validated_config = AccountConfig(
            account_name=account_config.ACCOUNT_NAME,
            display_name=account_config.DISPLAY_NAME,
            brand_identity=account_config.BRAND_IDENTITY,
            content_pillars=account_config.CONTENT_PILLARS,
            color_schemes=account_config.COLOR_SCHEMES,
            visual_style=getattr(account_config, 'VISUAL_STYLE', {}),
            hashtag_strategy=account_config.HASHTAG_STRATEGY,
            carousel_strategy=getattr(account_config, 'CAROUSEL_STRATEGY', {}),
            quality_overrides=account_config.QUALITY_OVERRIDES,
            output_config=account_config.OUTPUT_CONFIG,
            topic_tracker_config=account_config.TOPIC_TRACKER_CONFIG,
            claude_model=account_config.CLAUDE_MODEL,
            openrouter_api_key=getattr(account_config, 'OPENROUTER_API_KEY', None),
            gemini_api_key=getattr(account_config, 'GEMINI_API_KEY', None)
        )

        console.print("[green]✓ Configuration valid[/green]\n")

        # Step 9: Generate samples
        generate_samples = questionary.confirm(
            "Generate 3 sample carousels to test your configuration?",
            default=True
        ).ask()

        if generate_samples:
            step_9_generate_samples(account_dir, validated_config)

    except Exception as e:
        console.print(f"[red]❌ Validation failed: {e}[/red]")
        sys.exit(1)

    # Success!
    console.print(Panel.fit(
        f"[bold green]✓ Account '{config_data['account_name']}' created successfully![/bold green]\n\n"
        f"[dim]Next steps:[/dim]\n"
        f"1. Generate content:\n"
        f"   [cyan]python -m cli.generate --account {config_data['account_name']} --random[/cyan]\n\n"
        f"2. View account:\n"
        f"   [cyan]cd {account_dir}[/cyan]\n\n"
        f"3. Customize:\n"
        f"   [cyan]Edit config.py, scenes.json as needed[/cyan]",
        border_style="green",
        title="Success!"
    ))


if __name__ == "__main__":
    main()
