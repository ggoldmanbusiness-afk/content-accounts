"""Functions for integrating performance context into the content generator."""
import json
import logging
import random
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_performance_context(context_path: Path) -> Optional[dict]:
    """Load performance_context.json if it exists."""
    if not context_path.exists():
        return None
    try:
        return json.loads(context_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def weighted_format_choice(available_formats: list[str], format_weights: dict[str, float]) -> str:
    """Choose a format weighted by performance data."""
    weights = [format_weights.get(fmt, 1.0) for fmt in available_formats]
    return random.choices(available_formats, weights=weights, k=1)[0]


def get_reference_hooks(context: dict) -> list[str]:
    """Get high-performing hooks to use as reference examples in the semantic scorer."""
    return context.get("hook_insights", {}).get("reference_hooks", [])


def get_top_pillars(context: dict) -> list[str]:
    """Get top-performing content pillars."""
    return context.get("top_pillars", [])


def get_experiment_suggestion(context: dict) -> Optional[str]:
    """Get an experiment suggestion (exploration)."""
    suggestions = context.get("experiment_suggestions", [])
    return random.choice(suggestions) if suggestions else None


def get_visual_guidance(context: dict) -> Optional[str]:
    """Build prose string from top_performing visual attributes for exploit mode."""
    insights = context.get("visual_insights", {})
    top = insights.get("top_performing", {})
    if not top:
        return None

    # Map attribute keys to readable labels
    labels = {
        "photography_style": "style",
        "lighting": "lighting",
        "color_palette": "color palette",
        "composition": "composition",
        "scene_setting": "setting",
        "subject_focus": "subject focus",
        "mood": "mood",
    }

    parts = []
    for attr, value in top.items():
        label = labels.get(attr, attr)
        parts.append(f"{value.replace('_', ' ')} {label}")

    return "Data shows best performance with: " + ", ".join(parts)


def get_explore_visual_guidance(context: dict) -> Optional[str]:
    """Pick random untested combo from explore_targets for explore mode."""
    targets = context.get("explore_targets", {})
    if not targets:
        return None

    # Pick one random untested value per attribute that has blind spots
    combo = {}
    for attr, values in targets.items():
        if values:
            combo[attr] = random.choice(values)

    if not combo:
        return None

    labels = {
        "photography_style": "style",
        "lighting": "lighting",
        "color_palette": "color palette",
        "composition": "composition",
        "scene_setting": "setting",
        "subject_focus": "subject focus",
        "mood": "mood",
    }

    parts = []
    for attr, value in combo.items():
        label = labels.get(attr, attr)
        parts.append(f"{value.replace('_', ' ')} {label}")

    return "Testing new visual approach: " + ", ".join(parts)


def should_explore(context: dict) -> bool:
    """Roll random float against exploration_ratio to decide exploit vs explore."""
    ratio = context.get("exploration_ratio", 0.40)
    return random.random() < ratio


def pick_pillar_by_tier(context: dict, all_pillars: list[str]) -> Optional[str]:
    """Pick a content pillar using tier-based selection.

    Exploit mode: pick from tier_1_proven (broad categories matched to pillars).
    Explore mode: pick from tier_3_explore if populated, else tier_2_promising.
    Returns None if no tier data exists (caller falls back to random).
    """
    tiers = context.get("pillar_priority_tiers")
    if not tiers:
        return None

    exploring = should_explore(context)

    if exploring:
        # Explore: try tier 3 first, then tier 2
        pool = tiers.get("tier_3_explore", []) or tiers.get("tier_2_promising", [])
    else:
        # Exploit: use proven pillars
        pool = tiers.get("tier_1_proven", [])

    if not pool:
        return None

    # Pick a broad tier topic, then fuzzy-match to an actual content pillar
    tier_topic = random.choice(pool)
    tier_words = set(tier_topic.lower().split())

    # Score each pillar by keyword overlap with the tier topic
    scored = []
    for pillar in all_pillars:
        pillar_words = set(pillar.replace("_", " ").lower().split())
        overlap = len(tier_words & pillar_words)
        if overlap > 0:
            scored.append((overlap, pillar))

    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        # Pick randomly from top matches (all with max overlap)
        max_score = scored[0][0]
        top_matches = [p for s, p in scored if s == max_score]
        return random.choice(top_matches)

    # No fuzzy match — return the tier topic directly (generator will use it as-is)
    return tier_topic


def replenish_explore_topics(context_path: Path, llm_client, min_threshold: int = 10,
                             replenish_count: int = 20) -> int:
    """Auto-replenish tier_3_explore when it drops below threshold.

    Uses LLM to brainstorm new topics based on what's performing well.
    Returns number of new topics added (0 if no replenish needed).
    """
    context = load_performance_context(context_path)
    if not context:
        return 0

    tiers = context.get("pillar_priority_tiers", {})
    explore = tiers.get("tier_3_explore", [])

    if len(explore) >= min_threshold:
        return 0

    logger.info(f"📊 Tier 3 has {len(explore)} topics (below {min_threshold}) — auto-replenishing...")

    # Gather all existing topics to avoid duplicates
    all_existing = set()
    for tier_key in ("tier_1_proven", "tier_2_promising", "tier_3_explore"):
        for t in tiers.get(tier_key, []):
            all_existing.add(t.lower())
    for t in context.get("retire_pillars", []):
        all_existing.add(t.lower())

    # Build context about what performs well
    content_angle = context.get("content_angle", "actionable activities over advice")
    tier_1 = tiers.get("tier_1_proven", [])

    prompt = f"""Generate {replenish_count} unique content topic categories for a parenting TikTok/Instagram account targeting parents of babies and toddlers (0-4 years).

WHAT PERFORMS BEST: {content_angle}
TOP CATEGORIES: {', '.join(tier_1)}

Rules:
- Each topic: 2-6 words, broad enough for 5-10 posts
- Lean toward hands-on, actionable, activity-based content
- Do NOT include any of these existing topics: {', '.join(sorted(all_existing))}
- No generic/vague categories — be specific enough to inspire content
- Mix of evergreen and trending parenting topics

Return ONLY a JSON array of {replenish_count} strings. No explanations.
Example: ["topic one", "topic two"]"""

    try:
        response = llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=800
        )

        # Parse JSON array from response
        import re
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if not json_match:
            logger.warning("Failed to parse replenish response — no JSON array found")
            return 0

        new_topics = json.loads(json_match.group())

        # Deduplicate against all existing
        unique_new = [t for t in new_topics if t.lower() not in all_existing]

        # Append to tier 3
        explore.extend(unique_new)
        tiers["tier_3_explore"] = explore
        context["pillar_priority_tiers"] = tiers

        # Write back
        context_path.write_text(json.dumps(context, indent=2))
        logger.info(f"📊 Added {len(unique_new)} new explore topics (tier 3 now has {len(explore)})")
        return len(unique_new)

    except Exception as e:
        logger.warning(f"Failed to replenish explore topics: {e}")
        return 0
