"""
Framework Defaults
Default values and constants for the framework
"""

# Slide dimensions (Instagram 9:16 ratio)
SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1920

# Content formats
CONTENT_FORMATS = ["habit_list", "step_guide"]

# Character types
CHARACTER_TYPES = [
    "personal_brand",      # Visible faces, human connection
    "faceless_expert",     # No faces, strategic camera angles
    "lifestyle_guide",     # Faces optional, environment-focused
    "educational_coach"    # Professional setting (legacy)
]

# Default color schemes (can be customized per account)
DEFAULT_COLOR_SCHEMES = [
    {"bg": "#E8F4F8", "text": "#2C3E50", "name": "soft_blue"},
    {"bg": "#F5E6D3", "text": "#2C3E50", "name": "warm_cream"},
    {"bg": "#C8E6C9", "text": "#2C3E50", "name": "soft_green"},
]

# Default quality thresholds
DEFAULT_MIN_HOOK_SCORE = 16
DEFAULT_MAX_WORDS_PER_SLIDE = 20

# Slide count constraints
MIN_SLIDES = 5
MAX_SLIDES = 10
DEFAULT_SLIDES = 5
