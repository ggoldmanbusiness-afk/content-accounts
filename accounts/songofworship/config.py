"""
SongOfWorship Configuration
Configuration for @songofworship content generation
"""

from pathlib import Path


# Account Identity
ACCOUNT_NAME = "songofworship"
DISPLAY_NAME = "SongOfWorship"

# Brand Voice
BRAND_IDENTITY = {
    "character_type": "lifestyle_guide",
    "personality": "Warm, reverent faith guide,like a worship pastor who texts you encouragement. Scripture-grounded, never preachy, never salesy. Real faith woven into everyday life.",
    "value_proposition": "Personalized worship songs for life's biggest moments,baptisms, weddings, grief, milestones",
    "voice_attributes": [
        "Warm and reverent",
        "Scripture-grounded",
        "Encouraging but not preachy",
        "Conversational and authentic"
    ]
}

# Content Pillars (~60% faith/devotional, ~40% gifting/occasions)
CONTENT_PILLARS = [
    # Faith/Devotional (audience builders,high saves)
    "scripture_for_seasons",
    "worship_life",
    "prayer_practices",
    "faith_milestones",
    "church_community",
    "worship_music_appreciation",

    # Behind-the-Scenes (product storytelling)
    "song_stories",
    "worship_songwriting",
    "name_in_worship",

    # Gifting/Occasions (conversion drivers)
    "meaningful_gifts",
    "baptism_celebrations",
    "wedding_and_marriage",
    "comfort_and_grief",
    "milestone_moments",
]

# Quality Thresholds (ported from DTL proven settings)
QUALITY_OVERRIDES = {
    "min_hook_score": 12,
    "max_words_per_slide": 20,
    "optimize_for_saves": True,
    "allow_sensitive_words": False
}

# Hashtag Strategy
HASHTAG_STRATEGY = {
    "primary": ["worship", "worshipmusic", "faith", "christiangifts", "songofworship"],
    "secondary": [
        "christianmusic", "worshipsong", "praiseandworship", "faithjourney",
        "baptism", "christianlife", "prayerlife", "scripture",
        "faithfamily", "churchlife", "worshiplive", "christiancommunity",
        "giftsofgrace", "meaningfulgifts", "personalizedgift"
    ],
    "topic_hashtags": {
        "scripture": ["bibleverse", "scripture", "dailydevotional", "faithjourney"],
        "worship": ["worshipmusic", "praiseandworship", "worshiplive", "christianmusic"],
        "prayer": ["prayerlife", "prayerwarrior", "prayerworks", "faithfamily"],
        "baptism": ["baptism", "baptismday", "faithjourney", "newbeliever"],
        "wedding": ["christianwedding", "faithinlove", "marriagegoals", "weddingblessing"],
        "grief": ["griefandgrace", "comfortinscripture", "faithingrief", "godisgood"],
        "gifts": ["christiangifts", "meaningfulgifts", "personalizedgift", "giftideas"],
        "general": ["christianlife", "faithfamily", "churchlife", "christiancommunity"]
    },
    "max_per_post": 5,
    "style": "simple_hashtags_only"
}

# Color Schemes (matching SongOfWorship site branding: cream, gold, charcoal)
COLOR_SCHEMES = [
    {"bg": "#FBF8F3", "text": "#2D2926", "name": "sanctuary"},
    {"bg": "#FFF8E7", "text": "#2D2926", "name": "golden_hour"},
    {"bg": "#2D2926", "text": "#FBF8F3", "name": "evening_worship"},
    {"bg": "#F0F4EF", "text": "#2D2926", "name": "creation"},
    {"bg": "#FDF0EC", "text": "#2D2926", "name": "grace"},
    {"bg": "#F3EDE4", "text": "#2D2926", "name": "parchment"},
]

# Visual Style
VISUAL_STYLE = {
    "mode": "text_only_slides",
    "font_style": "clean_sans_serif",
    "slide_layout": "minimal_checklist"
}

# Carousel Strategy (ported from DTL: habit_list default, 5 slides)
CAROUSEL_STRATEGY = {
    "content_type": "save_worthy_tips",
    "slide_count_range": (5, 10),
    "default_slide_count": 5,
    "format": "habit_list",
    "cta_focus": "save_this",
    "caption_style": "hashtags_only"
}

# Caption CTA instruction,soft mix strategy
# Faith posts: organic CTAs. Gifting posts: mention product.
CAPTION_CTA_INSTRUCTION = """- For scripture/devotional/worship content: end with an engagement question like 'which verse speaks to you?' or 'save this for Sunday.' Do NOT mention link in bio.
- For gifting/occasion content (baptism, wedding, grief, milestones, meaningful gifts): weave in 'personalized worship songs,link in bio' naturally.
- For song_stories/behind-the-scenes content: mention 'create a worship song for someone you love,link in bio' at the end."""

# Fallback CTA suffix (only appended to gifting/occasion posts if LLM misses it)
CAPTION_CTA_SUFFIX = "personalized worship songs for life's biggest moments,songofworship.com"

# Output Configuration
OUTPUT_CONFIG = {
    "base_directory": "/Users/grantgoldman/Google Drive/My Drive/SongOfWorship",
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

# Hook Formulas (ported from DTL, adapted for faith/worship)
HOOK_FORMULAS = [
    "[Number] [action] to [spiritual benefit]",
    "The one [scripture/song/prayer] that changed [situation]",
    "What I wish someone told me about [faith topic]",
    "This [verse/song] got me through [difficult season]"
]

# QA Rules (per-account)
QA_RULES = {
    "image_qa_prompt": "Check for: reverent and warm atmosphere, no theologically problematic imagery, worship/faith context appropriate, warm golden lighting preferred, no text/letters visible in images.",
}

# Seasonal Topics
SEASONAL_TOPICS_ENABLED = True

# Platform profiles for analytics scraping
PLATFORM_PROFILES = {
    "tiktok": "songofworship",
    "instagram": "songofworship",
}
