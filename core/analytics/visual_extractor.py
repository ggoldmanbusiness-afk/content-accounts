"""
Keyword-based visual attribute extraction from image prompts.

Classifies 7 visual attributes from prose image prompt descriptions:
photography_style, lighting, color_palette, composition, scene_setting,
subject_focus, and mood.

Fast, deterministic, no API cost.
"""

from collections import Counter


# --- Keyword Maps ---
# Each maps an attribute value to a list of keyword phrases.
# Matching is case-insensitive substring search against the prompt text.

PHOTOGRAPHY_STYLE = {
    "iphone_authentic": ["iphone", "phone photo", "authentic", "candid", "real life", "not posed", "casual snapshot"],
    "illustration": ["illustration", "illustrated", "hand drawn", "watercolor", "sketch", "cartoon", "graphic"],
    "studio": ["studio", "professional lighting", "backdrop", "product shot", "white background"],
    "cinematic": ["cinematic", "film still", "movie", "dramatic angle", "widescreen", "anamorphic"],
}

LIGHTING = {
    "golden_hour": ["golden hour", "golden light", "sunset light", "warm sunset"],
    "natural": ["natural light", "daylight", "window light", "sun light", "sunlit"],
    "moody": ["moody light", "low light", "dark", "shadow", "silhouette", "backlit"],
    "soft": ["soft light", "diffused", "overcast", "even lighting", "gentle light"],
    "warm": ["warm light", "warm glow", "lamp light", "cozy light", "candlelight"],
}

COLOR_PALETTE = {
    "cream_navy": ["cream", "navy", "ivory", "off-white", "deep blue"],
    "warm_golden": ["golden", "amber", "honey", "warm tone", "gold"],
    "earth_tones": ["earth tone", "brown", "terracotta", "olive", "sage", "muted green", "rust"],
    "bright": ["bright", "vivid", "saturated", "bold color", "pop of color", "colorful"],
    "pastel": ["pastel", "soft pink", "baby blue", "lavender", "mint", "blush"],
}

COMPOSITION = {
    "closeup": ["close-up", "closeup", "close up", "macro", "detail shot", "tight shot"],
    "overhead": ["overhead", "flat lay", "flatlay", "bird's eye", "birds eye", "top-down", "top down"],
    "low_angle": ["low angle", "looking up", "from below", "upward angle"],
    "profile": ["profile", "side view", "side angle", "from the side"],
    "wide": ["wide shot", "wide angle", "full scene", "establishing shot", "pulled back"],
    "medium": ["medium shot", "waist up", "mid-shot", "three-quarter"],
}

SCENE_SETTING = {
    "playground": ["playground", "park", "swing", "slide", "sandbox", "jungle gym"],
    "bedroom": ["bedroom", "nursery", "crib", "bed", "pillow", "blanket"],
    "kitchen": ["kitchen", "counter", "stove", "cooking", "baking", "highchair", "dining"],
    "living_room": ["living room", "couch", "sofa", "carpet", "tv", "family room", "playroom"],
    "outdoor": ["outdoor", "backyard", "garden", "yard", "porch", "patio", "nature", "trail", "beach"],
    "car": ["car seat", "car", "vehicle", "driving", "backseat"],
}

SUBJECT_FOCUS = {
    "hands_detail": ["hands", "fingers", "holding", "gripping", "reaching", "hand detail"],
    "parent_child": ["parent and child", "parent child", "mother and", "father and", "mom and", "dad and", "holding baby", "carrying"],
    "child_solo": ["child alone", "toddler", "baby solo", "kid playing", "child playing", "little one"],
    "face_expression": ["face", "expression", "smile", "crying", "laughing", "emotion", "eyes", "looking at camera"],
}

MOOD = {
    "warm_cozy": ["warm", "cozy", "comfort", "snuggle", "cuddle", "intimate", "tender"],
    "energetic": ["energetic", "active", "running", "jumping", "playful", "dynamic", "movement", "action"],
    "calm": ["calm", "peaceful", "serene", "quiet", "still", "gentle", "tranquil", "relaxed"],
    "moody_dramatic": ["moody", "dramatic", "intense", "stark", "contrast", "shadow", "tension"],
    "joyful": ["joyful", "happy", "bright", "cheerful", "fun", "delight", "excited", "laughter"],
}

ALL_ATTRIBUTE_MAPS = {
    "photography_style": PHOTOGRAPHY_STYLE,
    "lighting": LIGHTING,
    "color_palette": COLOR_PALETTE,
    "composition": COMPOSITION,
    "scene_setting": SCENE_SETTING,
    "subject_focus": SUBJECT_FOCUS,
    "mood": MOOD,
}


def classify_attribute(text: str, attribute_map: dict[str, list[str]]) -> list[str]:
    """Classify text against a keyword map. Returns list of matched values, ordered by match count."""
    text_lower = text.lower()
    scores = Counter()
    for value, keywords in attribute_map.items():
        for kw in keywords:
            if kw in text_lower:
                scores[value] += 1
    return [val for val, _ in scores.most_common()]


def extract_from_prompt(prompt_str: str) -> dict[str, list[str]]:
    """Extract all 7 visual attributes from a single image prompt string.

    Returns dict mapping attribute name -> list of matched values (ordered by strength).
    """
    result = {}
    for attr_name, attr_map in ALL_ATTRIBUTE_MAPS.items():
        matches = classify_attribute(prompt_str, attr_map)
        if matches:
            result[attr_name] = matches
    return result


def extract_from_post(image_prompts: list[str]) -> dict:
    """Extract visual attributes from all image prompts in a post.

    Returns:
        {
            "dominant": {attr: value, ...},        # most common value across all slides
            "hook": {attr: value, ...},             # attributes from slide 1 (the hook)
            "hook_composition": str|None,           # hook slide composition specifically
            "hook_photography_style": str|None,     # hook slide photography style
            "hook_lighting": str|None,              # hook slide lighting
            "hook_mood": str|None,                  # hook slide mood
            "all_attributes": {attr: Counter, ...}, # full frequency data
        }
    """
    if not image_prompts:
        return {
            "dominant": {},
            "hook": {},
            "hook_composition": None,
            "hook_photography_style": None,
            "hook_lighting": None,
            "hook_mood": None,
            "hook_subject_focus": None,
            "all_attributes": {},
        }

    # Aggregate across all slides
    attribute_counters = {attr: Counter() for attr in ALL_ATTRIBUTE_MAPS}

    for prompt in image_prompts:
        slide_attrs = extract_from_prompt(prompt)
        for attr_name, values in slide_attrs.items():
            # Weight by position: first match in a slide gets more weight
            for i, val in enumerate(values):
                attribute_counters[attr_name][val] += max(1, len(values) - i)

    # Dominant = most common value per attribute across all slides
    dominant = {}
    for attr_name, counter in attribute_counters.items():
        if counter:
            dominant[attr_name] = counter.most_common(1)[0][0]

    # Hook slide = first prompt
    hook_attrs = extract_from_prompt(image_prompts[0]) if image_prompts else {}
    hook = {}
    for attr_name, values in hook_attrs.items():
        if values:
            hook[attr_name] = values[0]

    # Serialize counters for storage
    all_attributes = {
        attr: dict(counter) for attr, counter in attribute_counters.items() if counter
    }

    return {
        "dominant": dominant,
        "hook": hook,
        "hook_composition": hook.get("composition"),
        "hook_photography_style": hook.get("photography_style"),
        "hook_lighting": hook.get("lighting"),
        "hook_mood": hook.get("mood"),
        "hook_subject_focus": hook.get("subject_focus"),
        "all_attributes": all_attributes,
    }
