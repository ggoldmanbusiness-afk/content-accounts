"""
Dreamtime Lullabies Configuration
Consolidated configuration for @dreamtimelullabies content generation
"""

from pathlib import Path


# Account Identity
ACCOUNT_NAME = "dreamtimelullabies"
DISPLAY_NAME = "Dreamtime Lullabies"

# Brand Voice
BRAND_IDENTITY = {
    "character_type": "lifestyle_guide",
    "personality": "Practical parenting expert sharing actionable tips for babies and young children",
    "value_proposition": "Save-worthy baby and child parenting solutions that actually work",
    "voice_attributes": [
        "Clear and direct",
        "Evidence-based",
        "Practical and actionable",
        "Supportive but not emotional"
    ]
}

# Content Pillars (comprehensive baby & child topics)
CONTENT_PILLARS = [
    # Sleep (important but just one pillar)
    "sleep_schedules_and_routines",
    "sleep_training_methods",
    "nap_transitions",

    # Developmental Milestones
    "physical_milestones",
    "cognitive_development",
    "language_development",
    "social_emotional_skills",

    # Feeding & Nutrition
    "breastfeeding_tips",
    "bottle_feeding_guide",
    "starting_solids",
    "picky_eating_solutions",
    "toddler_meal_ideas",

    # Behavior & Discipline
    "tantrum_management",
    "setting_boundaries",
    "positive_discipline",
    "sibling_dynamics",

    # Play & Activities
    "age_appropriate_activities",
    "developmental_play",
    "sensory_play_ideas",
    "outdoor_activities",

    # Safety
    "babyproofing_checklist",
    "car_seat_safety",
    "choking_hazards",
    "first_aid_basics",

    # Health & Wellness
    "common_illnesses",
    "teething_relief",
    "vaccine_schedules",
    "when_to_call_doctor",

    # Products & Gear
    "must_have_items",
    "budget_baby_gear",
    "product_comparisons",
    "registry_essentials",

    # General Parenting
    "managing_mom_guilt",
    "self_care_for_parents",
    "partner_communication",
    "work_life_balance"
]

# Quality Thresholds
QUALITY_OVERRIDES = {
    "min_hook_score": 12,  # Recalibrated: thresholds lowered so 12 is achievable
    "max_words_per_slide": 20,
    "optimize_for_saves": True,
    "allow_sensitive_words": False
}

# Hashtag Strategy
HASHTAG_STRATEGY = {
    "primary": ["newmom", "momlife", "parentingtips", "babytips"],
    "secondary": [
        "babysleep", "sleeptips", "sleeptraining",
        "babymilestonnes", "toddlerlife", "childdevelopment",
        "babyledweaning", "toddlermeals", "pickyeater",
        "gentleparenting", "toddlertantrums", "positiveparenting",
        "toddleractivities", "sensoryplay", "playideas",
        "momhacks", "firsttimemom", "babyhacks", "toddlermom"
    ],
    "topic_hashtags": {
        "sleep": ["babysleep", "sleeptips", "sleeptraining"],
        "development": ["babymilestonnes", "toddlerlife", "childdevelopment"],
        "feeding": ["babyledweaning", "toddlermeals", "pickyeater"],
        "behavior": ["gentleparenting", "toddlertantrums", "positiveparenting"],
        "activities": ["toddleractivities", "sensoryplay", "playideas"],
        "safety": ["babyhacks", "momhacks", "babyproofing"],
        "gear": ["babyhacks", "firsttimemom", "babyregistry"],
        "general": ["momhacks", "firsttimemom", "babyhacks", "toddlermom"]
    },
    "max_per_post": 5,
    "style": "simple_hashtags_only"
}

# Color Schemes (Calm sleep theme - rotating per carousel)
COLOR_SCHEMES = [
    {"bg": "#E8F4F8", "text": "#2C3E50", "name": "sleep_calm"},      # Primary soft blue
    {"bg": "#AED6F1", "text": "#2C3E50", "name": "soft_blue"},       # Lighter blue
    {"bg": "#D5B8E8", "text": "#2C3E50", "name": "gentle_purple"},   # Gentle purple
    {"bg": "#F5E6D3", "text": "#2C3E50", "name": "warm_cream"},      # Warm neutral
    {"bg": "#C8E6C9", "text": "#2C3E50", "name": "soft_green"},      # Soft green
    {"bg": "#B3E5FC", "text": "#2C3E50", "name": "sky_blue"},        # Sky blue
]

# Visual Style
VISUAL_STYLE = {
    "mode": "text_only_slides",  # Default mode (formats can override via CLI --format flag)
    "font_style": "clean_sans_serif",
    "slide_layout": "minimal_checklist",
    # Pexels mode settings (used when format requires stock photos)
    "pexels_mode": {
        "image_source": "pexels",
        "image_quality": "large2x",  # 1920px
        "text_color": "#FFFFFF",
        "text_shadow": True,
        "max_words_per_slide": 10
    }
}

# Carousel Strategy
CAROUSEL_STRATEGY = {
    "content_type": "save_worthy_tips",
    "slide_count_range": (5, 10),  # 5-10 slides per carousel
    "default_slide_count": 5,
    "format": "habit_list",  # Default format (override via CLI --format flag)
    "cta_focus": "save_this",
    "caption_style": "hashtags_only"
}

# Pexels Configuration (for stock photo formats)
PEXELS_CONFIG = {
    "orientation": "portrait",  # 9:16 ratio for Instagram/TikTok
    "quality": "large2x",  # 1920px resolution
    "per_page": 10,
    "history_max": 50  # Track last 50 used images to avoid duplicates
}

# Format Options (accessible via CLI --format flag)
# Available formats:
# - "scripts" - Scripts That Work (2,746 views proven, Pexels images)
# - "boring_habits" - 5 Boring Habits (1,386 views proven, Pexels images)
# - "how_to" - How to [Outcome] (2,049 views proven, Pexels images)
# - "habit_list" - Default habit/tip list (current format, text-only)
# - "step_guide" - Step-by-step guide (current format, text-only)

# Output Configuration
OUTPUT_CONFIG = {
    "base_directory": "/Users/grantgoldman/Google Drive/My Drive/DreamtimeLullabies",
    "structure": "{year}/{month}/{date}_{topic}",
    "include_metadata": True
}

# API Configuration (load from environment)
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
CLAUDE_MODEL = "anthropic/claude-sonnet-4.5"

# Topic Tracking
TOPIC_TRACKER_CONFIG = {
    "max_history": 15,
    "similarity_threshold": 0.6
}

# Hook Formulas (from safe_educational template)
HOOK_FORMULAS = [
    "[Number] [action] to [benefit]",
    "The one thing that changed [situation]",
    "What I wish I knew about [topic]",
    "This [expert] told me about [tip]"
]

# QA Rules (per-account)
QA_RULES = {
    "image_qa_prompt": "Check for: child count (should be 1 unless topic involves siblings), scene matches topic, clothing appropriate for scene, no cribs in non-bedroom rooms, warm inviting aesthetic.",
}

# Platform profiles for analytics scraping
PLATFORM_PROFILES = {
    "tiktok": "dreamtimelullabies",
    "instagram": "dreamtimelullabies",
}
