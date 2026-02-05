"""
{DISPLAY_NAME} Configuration
Auto-generated configuration for @{ACCOUNT_NAME}
"""

from pathlib import Path


# Account Identity
ACCOUNT_NAME = "{ACCOUNT_NAME}"
DISPLAY_NAME = "{DISPLAY_NAME}"

# Brand Voice
BRAND_IDENTITY = {{
    "character_type": "{CHARACTER_TYPE}",
    "personality": "{PERSONALITY}",
    "value_proposition": "{VALUE_PROPOSITION}",
    "voice_attributes": {VOICE_ATTRIBUTES}
}}

# Content Pillars ({PILLAR_COUNT} topics)
CONTENT_PILLARS = {CONTENT_PILLARS}

# Quality Thresholds
QUALITY_OVERRIDES = {{
    "min_hook_score": {MIN_HOOK_SCORE},
    "max_words_per_slide": {MAX_WORDS_PER_SLIDE},
    "optimize_for_saves": True,
    "allow_sensitive_words": False
}}

# Hashtag Strategy
HASHTAG_STRATEGY = {{
    "primary": {PRIMARY_HASHTAGS},
    "secondary": {SECONDARY_HASHTAGS},
    "max_per_post": {MAX_HASHTAGS},
    "style": "simple_hashtags_only"
}}

# Color Schemes ({COLOR_SCHEME_COUNT} schemes)
COLOR_SCHEMES = {COLOR_SCHEMES}

# Visual Style
VISUAL_STYLE = {{
    "mode": "text_only_slides",
    "font_style": "clean_sans_serif",
    "slide_layout": "minimal_checklist"
}}

# Carousel Strategy
CAROUSEL_STRATEGY = {{
    "content_type": "save_worthy_tips",
    "slide_count_range": (5, 10),
    "default_slide_count": 5,
    "format": "checklist_framework",
    "cta_focus": "save_this",
    "caption_style": "hashtags_only"
}}

# Output Configuration
OUTPUT_CONFIG = {{
    "base_directory": "{OUTPUT_DIRECTORY}",
    "structure": "{{year}}/{{month}}/{{date}}_{{topic}}",
    "include_metadata": True
}}

# API Configuration (load from environment)
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_MODEL = "anthropic/claude-sonnet-4.5"

# Topic Tracking
TOPIC_TRACKER_CONFIG = {{
    "max_history": 10,
    "similarity_threshold": 0.6
}}

# Hook Formulas
HOOK_FORMULAS = [
    "[Number] [action] to [benefit]",
    "The one thing that changed [situation]",
    "What I wish I knew about [topic]",
    "This [expert] told me about [tip]"
]
