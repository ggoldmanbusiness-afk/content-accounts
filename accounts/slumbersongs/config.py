"""
SlumberSongs Configuration
Configuration for @slumbersongs content generation
"""

from pathlib import Path


# Account Identity
ACCOUNT_NAME = "slumbersongs"
DISPLAY_NAME = "SlumberSongs"

# Brand Voice
BRAND_IDENTITY = {
    "character_type": "lifestyle_guide",
    "personality": "Warm, magical parent whisperer who makes bedtime feel like a gift — not a battle",
    "value_proposition": "Custom lullabies with your child's name, personality, and quirks woven in",
    "voice_attributes": [
        "Supportive and empathetic",
        "Conversational and casual",
        "Humorous and lighthearted"
    ]
}

# Content Pillars (10 topics)
CONTENT_PILLARS = [
    "lullaby_benefits",
    "baby_sleep_science",
    "baby_name_trends",
    "bedtime_routines",
    "personalization_power",
    "parent_self_care",
    "nursery_vibes",
    "baby_milestones_sleep",
    "music_and_development",
    "newborn_survival",
]

# Quality Thresholds
QUALITY_OVERRIDES = {
    "min_hook_score": 12,
    "max_words_per_slide": 20,
    "optimize_for_saves": True,
    "allow_sensitive_words": False
}

# Hashtag Strategy
HASHTAG_STRATEGY = {
    "primary": ["lullaby", "babysleep", "personalized", "newmom", "slumbersongs"],
    "secondary": [
        "babylullaby", "sleepmusic", "customlullaby", "babynames",
        "nursery", "momlife", "newborn", "babygirl", "babyboy",
        "firsttimemom", "momtok", "babytok"
    ],
    "topic_hashtags": {
        "sleep": ["babysleep", "sleeptips", "sleeptraining"],
        "lullaby": ["babylullaby", "sleepmusic", "customlullaby"],
        "names": ["babynames", "babygirl", "babyboy"],
        "routines": ["bedtimeroutine", "sleepschedule", "momhacks"],
        "music": ["sleepmusic", "babycalm", "musicforbabies"],
        "general": ["momlife", "firsttimemom", "newborn", "momtok"]
    },
    "max_per_post": 5,
    "style": "simple_hashtags_only"
}

# Color Schemes (SlumberSongs brand: navy, cream, amber, lavender)
COLOR_SCHEMES = [
    {"bg": "#F5F0E8", "text": "#0A0C1E", "name": "cream"},
    {"bg": "#E8E0F0", "text": "#0A0C1E", "name": "lavender"},
    {"bg": "#0A0C1E", "text": "#F5F0E8", "name": "navy"},
    {"bg": "#FFF3E0", "text": "#0A0C1E", "name": "warm_gold"},
    {"bg": "#E8F0F5", "text": "#0A0C1E", "name": "moonlight"},
]

# Visual Style
VISUAL_STYLE = {
    "mode": "text_only_slides",
    "font_style": "clean_sans_serif",
    "slide_layout": "minimal_checklist"
}

# Carousel Strategy
CAROUSEL_STRATEGY = {
    "content_type": "save_worthy_tips",
    "slide_count_range": (5, 10),
    "default_slide_count": 5,
    "format": "habit_list",
    "cta_focus": "save_this",
    "caption_style": "hashtags_only"
}

# Caption CTA instruction (injected into caption generation prompt)
CAPTION_CTA_INSTRUCTION = """- CRITICAL: You MUST include 'link in bio for a lullaby with their name' before the CTA question
- Example: 'we switched to a custom lullaby with her name and she stopped fighting sleep. link in bio for a lullaby with their name. which tip are you trying first?'"""

# Fallback CTA suffix appended to caption if LLM doesn't include "link in bio"
CAPTION_CTA_SUFFIX = "get a lullaby with their name — link in bio"

# Output Configuration
OUTPUT_CONFIG = {
    "base_directory": "/Users/grantgoldman/Google Drive/My Drive/SlumberSongs",
    "structure": "{year}/{month}/{date}_{topic}",
    "include_metadata": True
}

# API Configuration (load from environment)
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CLAUDE_MODEL = "anthropic/claude-sonnet-4.5"

# Topic Tracking
TOPIC_TRACKER_CONFIG = {
    "max_history": 15,
    "similarity_threshold": 0.6
}

# Hook Formulas
HOOK_FORMULAS = [
    "[Number] [action] to [benefit]",
    "The one thing that changed [situation]",
    "What I wish I knew about [topic]",
    "This [expert] told me about [tip]"
]

# QA Rules (per-account)
QA_RULES = {
    "caption_must_contain": ["link in bio"],
    "image_qa_prompt": "Check for: child count (should be 1 unless topic involves siblings), nursery/sleep scenes are cozy and safe, no cribs in non-bedroom rooms, musical/lullaby elements where appropriate.",
}

# Platform profiles for analytics scraping
PLATFORM_PROFILES = {
    "tiktok": "slumbersongs",
    "instagram": "slumbersongs",
}
