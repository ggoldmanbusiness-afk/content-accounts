"""
Content Format Templates
Defines structure for different proven carousel types
"""

FORMATS = {
    "scripts": {
        "name": "Scripts That Work",
        "description": "Exact phrases parents can use immediately",
        "proven_performance": "2,746 views average, 21+ saves",
        "structure": [
            {
                "slide": 1,
                "type": "hook",
                "template": "{Topic} Scripts That Work\n(What to Say)",
                "max_words": 8
            },
            {
                "slide": "2-N",
                "type": "category",
                "template": "When They're {Situation}\n• Script 1\n• Script 2\n• Script 3",
                "max_words_per_bullet": 8
            },
            {
                "slide": "last",
                "type": "cta",
                "template": "Save this for {context} 💙",
                "max_words": 6
            }
        ],
        "example_topics": [
            "toddler tantrums",
            "bedtime resistance",
            "picky eating",
            "sibling rivalry",
            "morning rush"
        ],
        "caption_format": "hashtags_only",
        "recommended_hashtags": ["parentingscripts", "gentleparenting", "toddlermom"],
        "pexels_keywords": ["parent comforting child", "toddler parent calm", "family gentle"]
    },

    "boring_habits": {
        "name": "5 Boring Habits That Changed Everything",
        "description": "Simple, unglamorous habits with big impact",
        "proven_performance": "1,386 views average",
        "structure": [
            {
                "slide": 1,
                "type": "hook",
                "template": "5 boring {topic} habits that changed everything",
                "max_words": 8
            },
            {
                "slide": "2-6",
                "type": "habit",
                "template": "{number}. {Habit name}\n({Why it works})",
                "max_words": 12
            },
            {
                "slide": "last",
                "type": "cta",
                "template": "Try one tonight 💙",
                "max_words": 6
            }
        ],
        "example_topics": [
            "emotional safety",
            "picky eating",
            "toddler tantrums",
            "bedtime routine",
            "sleep schedules"
        ],
        "caption_format": "hashtags_only",
        "recommended_hashtags": ["gentleparenting", "toddlermom", "parentingtips"],
        "pexels_keywords": ["parent child peaceful", "morning routine", "family calm"]
    },

    "how_to": {
        "name": "How to [Outcome]",
        "description": "Step-by-step guide to achieve specific result",
        "proven_performance": "2,049 views average",
        "structure": [
            {
                "slide": 1,
                "type": "hook",
                "template": "How to {outcome}",
                "max_words": 6
            },
            {
                "slide": "2-N",
                "type": "step",
                "template": "Step {n}: {Action}\n({Why it works})",
                "max_words": 10
            },
            {
                "slide": "last",
                "type": "cta",
                "template": "Save for later 💙",
                "max_words": 6
            }
        ],
        "example_topics": [
            "get baby sleeping through the night",
            "handle bedtime resistance",
            "transition to one nap",
            "stop early morning wakings",
            "establish bedtime routine"
        ],
        "caption_format": "hashtags_only",
        "recommended_hashtags": ["babysleep", "sleeptips", "newmom"],
        "pexels_keywords": ["baby sleeping peaceful", "nursery calm", "parent baby gentle"]
    }
}


def get_format(format_name: str) -> dict:
    """Get format configuration by name"""
    if format_name not in FORMATS:
        raise ValueError(f"Unknown format: {format_name}. Available: {list(FORMATS.keys())}")
    return FORMATS[format_name]


def get_pexels_query(format_name: str, topic: str) -> str:
    """
    Generate Pexels search query for a format + topic combination

    Args:
        format_name: Format type (scripts, boring_habits, how_to)
        topic: Content topic

    Returns:
        Optimized Pexels search query
    """
    format_config = get_format(format_name)
    keywords = format_config.get("pexels_keywords", ["parent child"])

    # Topic-specific mappings
    topic_mappings = {
        "sleep": "baby sleeping peaceful nursery",
        "tantrum": "parent comforting upset toddler calm",
        "feeding": "baby eating parent gentle",
        "bedtime": "parent child bedtime cozy",
        "routine": "family morning routine peaceful",
        "sibling": "parent children playing together",
        "picky eating": "toddler eating table parent",
    }

    # Find best match
    topic_lower = topic.lower()
    for key, query in topic_mappings.items():
        if key in topic_lower:
            return query

    # Fallback: use format keywords + topic
    return f"{keywords[0]} {topic}"
