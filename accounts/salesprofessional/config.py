"""
Sales Professional Configuration
Expert sales tips for traveling sales professionals
"""

from pathlib import Path


# Account Identity
ACCOUNT_NAME = "salesprofessional"
DISPLAY_NAME = "Sales Professional"

# Brand Voice
BRAND_IDENTITY = {
    "character_type": "personal_brand",
    "personality": "Experienced sales expert sharing proven strategies for closing deals and winning clients on the road",
    "value_proposition": "Battle-tested sales tactics that actually work in the field",
    "voice_attributes": [
        "Direct and results-focused",
        "Experience-based",
        "Tactical and actionable",
        "Confident but not arrogant"
    ]
}

# Content Pillars (comprehensive sales topics)
CONTENT_PILLARS = [
    # Prospecting & Lead Generation
    "cold_calling_techniques",
    "linkedin_prospecting",
    "email_outreach_strategies",
    "networking_events",
    "referral_generation",
    "finding_decision_makers",

    # Sales Process
    "qualifying_leads",
    "discovery_questions",
    "needs_analysis",
    "presenting_solutions",
    "handling_objections",
    "closing_techniques",
    "negotiation_tactics",
    "upselling_strategies",

    # Client Relationships
    "building_rapport",
    "active_listening",
    "trust_building",
    "client_retention",
    "managing_expectations",
    "customer_success",

    # Travel & Logistics
    "territory_planning",
    "travel_efficiency",
    "managing_meetings",
    "virtual_selling",
    "time_zone_management",
    "expense_management",

    # Sales Tools & Technology
    "crm_best_practices",
    "sales_automation",
    "presentation_tools",
    "mobile_productivity",
    "email_templates",

    # Mindset & Performance
    "dealing_with_rejection",
    "staying_motivated",
    "goal_setting",
    "time_management",
    "work_life_balance",
    "building_confidence",

    # Industry Knowledge
    "understanding_buyer_psychology",
    "competitive_intelligence",
    "market_research",
    "industry_trends",
    "value_propositions"
]

# Quality Thresholds
QUALITY_OVERRIDES = {
    "min_hook_score": 12,  # Recalibrated: thresholds lowered so 12 is achievable
    "max_words_per_slide": 18,
    "optimize_for_saves": True,
    "allow_sensitive_words": False
}

# Hashtag Strategy
HASHTAG_STRATEGY = {
    "primary": ["sales", "salestips", "b2bsales", "saleslife"],
    "secondary": [
        # Sales Process
        "closing", "prospecting", "coldcalling", "salesstrategy",
        # Professional Development
        "salestraining", "salescoach", "salesmotivation", "salesskills",
        # Industry
        "b2b", "saas", "entrepreneur", "businessdevelopment",
        # Lifestyle
        "salescareer", "roadwarrior", "travelsales", "remotesales"
    ],
    "max_per_post": 4,
    "style": "simple_hashtags_only"
}

# Color Schemes (Professional business theme)
COLOR_SCHEMES = [
    {"bg": "#1E3A5F", "text": "#FFFFFF", "name": "professional_navy"},    # Navy blue
    {"bg": "#2C3E50", "text": "#ECF0F1", "name": "business_gray"},        # Dark gray
    {"bg": "#34495E", "text": "#FFFFFF", "name": "corporate_slate"},      # Slate
    {"bg": "#16A085", "text": "#FFFFFF", "name": "success_teal"},         # Success teal
    {"bg": "#2980B9", "text": "#FFFFFF", "name": "trust_blue"},           # Trust blue
    {"bg": "#95A5A6", "text": "#2C3E50", "name": "neutral_gray"},         # Neutral gray
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
    "slide_count_range": (6, 8),  # 6-8 slides per carousel
    "default_slide_count": 7,
    "format": "step_guide",
    "cta_focus": "save_this",
    "caption_style": "hashtags_only"
}

# Output Configuration
OUTPUT_CONFIG = {
    "base_directory": "/Users/grantgoldman/Google Drive/My Drive/SalesProfessional",
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

# QA Rules (per-account)
QA_RULES = {
    "hook_max_words": 18,
    "image_qa_prompt": "Check for: professional attire and settings, no casual/home environments for business content, clean modern aesthetics, no distracting backgrounds.",
}

# Hook Formulas (sales-focused)
HOOK_FORMULAS = [
    "[Number] ways to [close more deals]",
    "This [technique] helped me close [result]",
    "What top performers do differently with [topic]",
    "The [mistake] that's costing you deals"
]
