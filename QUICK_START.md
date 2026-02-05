# Quick Start Guide

Get started with the Content Accounts Framework in 5 minutes.

## Prerequisites

- Python 3.9+
- OpenRouter API key (for Claude)
- Gemini API key (optional, for images)

## Step 1: Install Dependencies (2 minutes)

```bash
cd /Users/grantgoldman/Documents/GitHub/content-accounts
pip3 install -r requirements.txt
```

This installs:
- openai, pillow, pilmoji (content generation)
- pydantic, python-dotenv (config & env)
- questionary, rich (interactive wizard)

## Step 2: Set Up API Keys (1 minute)

Create `.env` in project root:

```bash
# Copy example
cp .env.example .env

# Edit with your keys
nano .env
```

Add your keys:
```
OPENROUTER_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
```

## Step 3: Create Your First Account (30 minutes)

Run the interactive wizard:

```bash
python3 -m cli.create_account
```

The wizard will guide you through:
1. **Account Identity** - Name and display name
2. **Brand Voice** - Persona, personality, voice attributes
3. **Content Pillars** - Choose template (parenting, fitness, cooking, productivity) or create custom
4. **Visual Style** - Pick color palette (6 presets available)
5. **Hashtags** - Primary and secondary tags
6. **Output Location** - Where to save generated content
7. **API Keys** - Use env keys or enter custom ones
8. **Review** - Confirm your configuration
9. **Sample Generation** - Creates 3 test carousels

## Step 4: Generate Content (2 minutes)

After account creation:

```bash
# Generate a random carousel
python3 -m cli.generate --account youraccountname --random

# Generate specific topic
python3 -m cli.generate --account youraccountname --topic "your topic here"

# Batch generate 5 carousels
python3 -m cli.generate --account youraccountname --random --count 5
```

## Step 5: Review Output

Generated content is saved to your configured output directory:

```
YourOutputDirectory/
└── 2026/
    └── 02-february/
        └── 2026-02-05_topic-slug/
            ├── slides/
            │   ├── slide_01.png
            │   ├── slide_02.png
            │   └── ...
            ├── caption.txt
            ├── meta.json
            └── carousel_data.json
```

## Common Commands

### Validate Configuration
```bash
# Single account
python3 -m cli.validate youraccountname

# All accounts
python3 -m cli.validate --all
```

### Generate with Options
```bash
# Step guide format with 7 slides
python3 -m cli.generate --account youraccountname --topic "topic" --format step_guide --slides 7

# Verbose output for debugging
python3 -m cli.generate --account youraccountname --random --verbose

# Batch generation
python3 -m cli.generate --account youraccountname --random --count 10
```

## Testing the Migrated Account

The existing dreamtimelullabies account has been migrated:

```bash
# Validate it works
python3 -m cli.validate dreamtimelullabies

# Generate content
python3 -m cli.generate --account dreamtimelullabies --random
```

## Customizing Your Account

After creation, you can customize:

1. **Edit config** - `accounts/youraccountname/config.py`
   - Add more content pillars
   - Adjust quality thresholds
   - Modify hashtag strategy

2. **Customize scenes** - `accounts/youraccountname/scenes.json`
   - Add more scene descriptions
   - Adjust aesthetic styles

3. **Update templates** - `accounts/youraccountname/content_templates.json`
   - Modify hook examples
   - Change CTA templates

## Troubleshooting

### Error: Module not found
```bash
# Install dependencies
pip3 install -r requirements.txt
```

### Error: API key not found
```bash
# Check .env file exists
cat .env

# Or set environment variables
export OPENROUTER_API_KEY=your_key
export GEMINI_API_KEY=your_key
```

### Error: Account not found
```bash
# List available accounts
ls accounts/

# Validate specific account
python3 -m cli.validate accountname
```

### Image generation fails
- Check GEMINI_API_KEY is set
- Gemini images are optional - content generation works without them
- Text overlays will still be created

## Next Steps

1. **Create multiple accounts** - Try different niches
2. **A/B test** - Different brand voices, pillars, styles
3. **Monitor performance** - Track hook scores, engagement
4. **Iterate** - Refine based on what works

## Need Help?

See detailed documentation:
- `README.md` - Full framework overview
- `COMPLETION_SUMMARY.md` - Implementation details
- `IMPLEMENTATION_STATUS.md` - Development progress

## Tips for Success

1. **Start with templates** - Use preset pillars for your niche
2. **Generate samples first** - The wizard creates 3 test carousels
3. **Review quality** - Check hook scores, adjust thresholds if needed
4. **Batch generate** - Create multiple carousels to find patterns
5. **Customize gradually** - Start with defaults, refine over time

---

**Ready to create unlimited content accounts!** 🚀
