# Content Accounts Framework

Multi-account content generation framework for creating unlimited social media carousel accounts with an interactive onboarding wizard.

## Quick Start

### Create Your First Account

```bash
# Interactive wizard (25-30 mins)
python -m cli.create_account
```

### Generate Content

```bash
# Random carousel
python -m cli.generate --account dreamtimelullabies --random

# Specific topic
python -m cli.generate --account myaccount --topic "your topic" --slides 7

# Batch generation
python -m cli.generate --account myaccount --random --count 10
```

## Features

- **Interactive Onboarding**: 25-30 minute wizard creates production-ready accounts
- **Shared Core Library**: Bug fixes apply to all accounts automatically
- **Account Isolation**: Each account fully self-contained (config, output, history)
- **Config Validation**: Pydantic schemas catch errors before generation
- **Template System**: Copy/customize patterns from existing accounts
- **Scalable**: Supports 50+ accounts without performance degradation

## Architecture

```
content-accounts/
├── core/                  # Shared library (DRY principle)
│   ├── generator.py       # BaseContentGenerator
│   ├── config_schema.py   # Pydantic validation
│   ├── image_generator.py # Gemini image generation
│   └── utils.py           # SlugGenerator, TopicTracker
├── cli/                   # CLI tooling
│   ├── create_account.py  # Interactive wizard
│   ├── generate.py        # Universal content generation
│   └── templates/         # Scaffolding templates
└── accounts/              # Account instances
    └── [account-name]/    # Isolated account
        ├── config.py
        ├── scenes.json
        └── output/
```

## Installation

```bash
# Clone repository
cd content-accounts

# Install dependencies
pip install -r requirements.txt

# Or use pip install -e .
pip install -e .

# Set up API keys
cp .env.example .env
# Edit .env with your keys
```

## Requirements

- Python 3.9+
- OpenRouter API key (for Claude)
- Gemini API key (for image generation)

## Commands

### Create Account
```bash
python -m cli.create_account
```
Interactive wizard with 9 steps:
1. Account identity
2. Brand voice
3. Content pillars (5-50 topics)
4. Visual style
5. Hashtag strategy
6. Output configuration
7. API keys
8. Review & confirm
9. Generate samples

### Generate Content
```bash
# Random topic
python -m cli.generate --account NAME --random

# Specific topic
python -m cli.generate --account NAME --topic "TOPIC"

# With options
python -m cli.generate --account NAME --topic "TOPIC" \
    --format habit_list \
    --slides 7 \
    --count 3
```

### Validate Config
```bash
# Single account
python -m cli.validate ACCOUNT_NAME

# All accounts
python -m cli.validate --all
```

## Configuration

Each account has a `config.py` with:

```python
# Account Identity
ACCOUNT_NAME = "myaccount"
DISPLAY_NAME = "My Account"

# Brand Identity
BRAND_IDENTITY = {
    "character_type": "faceless_expert",
    "personality": "...",
    "value_proposition": "...",
    "voice_attributes": [...]
}

# Content Pillars (5-50 topics)
CONTENT_PILLARS = [
    "topic_1",
    "topic_2",
    ...
]

# Color Schemes (3+ schemes)
COLOR_SCHEMES = [
    {"bg": "#E8F4F8", "text": "#2C3E50", "name": "calm"},
    ...
]

# Output Configuration
OUTPUT_CONFIG = {
    "base_directory": "/path/to/output",
    "structure": "{year}/{month}/{date}_{topic}"
}
```

## Output Structure

```
accounts/myaccount/output/
└── 2026/
    └── 02-february/
        └── 2026-02-05_topic-slug/
            ├── slides/
            │   ├── slide_01.png
            │   └── ...
            ├── caption.txt
            ├── meta.json
            └── carousel_data.json
```

## Development

### Running Tests
```bash
pytest
```

### Type Checking
```bash
mypy core/ cli/
```

### Linting
```bash
ruff check .
```

## License

Proprietary - All Rights Reserved
