#!/usr/bin/env python3
"""
Migration Script: Dreamtime Lullabies → Framework
Migrate existing dreamtimelullabies account to new framework structure
"""

import shutil
import json
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_schema import AccountConfig


def migrate_dreamtime():
    """Migrate dreamtimelullabies to new framework"""

    print("=" * 70)
    print("  Dreamtime Lullabies Migration")
    print("=" * 70)
    print()

    # Paths
    source_dir = Path("/Users/grantgoldman/Documents/GitHub/dreamtimelullabies")
    target_dir = Path(__file__).parent.parent / "accounts" / "dreamtimelullabies"

    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return False

    # Create target directory
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created target directory: {target_dir}")

    # Step 1: Copy config.py
    print("\n1. Copying config.py...")
    shutil.copy(source_dir / "config.py", target_dir / "config.py")
    print("   ✓ config.py copied")

    # Step 2: Copy scenes.json
    print("\n2. Copying scenes.json...")
    shutil.copy(source_dir / "scenes.json", target_dir / "scenes.json")
    print("   ✓ scenes.json copied")

    # Step 3: Copy content_templates.json
    print("\n3. Copying content_templates.json...")
    shutil.copy(source_dir / "content_templates.json", target_dir / "content_templates.json")
    print("   ✓ content_templates.json copied")

    # Step 4: Copy .env if exists
    print("\n4. Checking for .env file...")
    env_file = source_dir / ".env"
    if env_file.exists():
        shutil.copy(env_file, target_dir / ".env")
        print("   ✓ .env copied")
    else:
        print("   ⚠️  .env not found (will use framework .env)")

    # Step 5: Move output directory
    print("\n5. Migrating output directory...")
    source_output = source_dir / "output" / "dreamtimelullabies"
    target_output = target_dir / "output"

    if source_output.exists():
        # Count files for progress
        file_count = sum(1 for _ in source_output.rglob("*") if _.is_file())
        print(f"   Found {file_count} files to migrate...")

        if target_output.exists():
            print("   ⚠️  Target output directory already exists, skipping...")
        else:
            shutil.copytree(source_output, target_output)
            print(f"   ✓ Migrated output directory ({file_count} files)")
    else:
        print("   ⚠️  No output directory found")
        target_output.mkdir(parents=True, exist_ok=True)

    # Step 6: Create account README
    print("\n6. Creating account README...")
    readme_content = """# Dreamtime Lullabies

Parenting content account focused on baby sleep and child development.

## Account Info

- **Display Name**: Dreamtime Lullabies
- **Niche**: Baby sleep, parenting tips, child development
- **Character Type**: Faceless expert
- **Brand Voice**: Clear, direct, evidence-based, practical

## Content Pillars

40+ topics covering:
- Sleep schedules and routines
- Development milestones
- Feeding & nutrition
- Behavior & discipline
- Play & activities
- Safety, health, products, general parenting

## Generation

```bash
# Random carousel
python -m cli.generate --account dreamtimelullabies --random

# Specific topic
python -m cli.generate --account dreamtimelullabies --topic "sleep schedules"

# Batch generation
python -m cli.generate --account dreamtimelullabies --random --count 5
```

## Output

Generated content is saved to:
```
/Users/grantgoldman/Google Drive/My Drive/DreamtimeLullabies/
├── YYYY/
│   └── MM-month/
│       └── YYYY-MM-DD_topic-slug/
│           ├── slides/
│           ├── caption.txt
│           └── meta.json
```

## History

Topic history tracked in `output/history/topic_history.json` (max 10 topics).
"""

    readme_path = target_dir / "README.md"
    readme_path.write_text(readme_content)
    print("   ✓ README.md created")

    # Step 7: Validate config
    print("\n7. Validating configuration...")
    try:
        # Import the migrated config
        sys.path.insert(0, str(target_dir))
        import config as dreamtime_config

        # Build AccountConfig from migrated config
        account_config = AccountConfig(
            account_name=dreamtime_config.ACCOUNT_NAME,
            display_name=dreamtime_config.DISPLAY_NAME,
            brand_identity=dreamtime_config.BRAND_IDENTITY,
            content_pillars=dreamtime_config.CONTENT_PILLARS,
            color_schemes=[
                {"bg": scheme["bg"], "text": scheme["text"], "name": scheme["name"]}
                for scheme in dreamtime_config.COLOR_SCHEMES
            ],
            visual_style=getattr(dreamtime_config, 'VISUAL_STYLE', {}),
            hashtag_strategy=dreamtime_config.HASHTAG_STRATEGY,
            carousel_strategy=getattr(dreamtime_config, 'CAROUSEL_STRATEGY', {}),
            quality_overrides=dreamtime_config.QUALITY_OVERRIDES,
            output_config=dreamtime_config.OUTPUT_CONFIG,
            topic_tracker_config=dreamtime_config.TOPIC_TRACKER_CONFIG,
            claude_model=dreamtime_config.CLAUDE_MODEL,
            hook_formulas=getattr(dreamtime_config, 'HOOK_FORMULAS', [])
        )

        print("   ✓ Configuration validated successfully")
        print(f"   - Account: {account_config.account_name}")
        print(f"   - Content pillars: {len(account_config.content_pillars)}")
        print(f"   - Color schemes: {len(account_config.color_schemes)}")
        print(f"   - Output directory: {account_config.output_config.base_directory}")

    except Exception as e:
        print(f"   ❌ Configuration validation failed: {e}")
        return False

    # Step 8: Migration summary
    print("\n" + "=" * 70)
    print("  Migration Complete!")
    print("=" * 70)
    print("\nMigrated files:")
    print(f"  ✓ config.py")
    print(f"  ✓ scenes.json")
    print(f"  ✓ content_templates.json")
    print(f"  ✓ output directory")
    print(f"  ✓ README.md")
    print()
    print("Next steps:")
    print("  1. Test generation:")
    print("     python -m cli.generate --account dreamtimelullabies --random")
    print()
    print("  2. Verify output matches old system")
    print()
    print("  3. Once validated, original dreamtimelullabies/ can be archived")
    print()

    return True


if __name__ == "__main__":
    success = migrate_dreamtime()
    sys.exit(0 if success else 1)
