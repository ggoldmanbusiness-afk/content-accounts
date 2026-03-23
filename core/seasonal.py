"""
Seasonal/Holiday Topic Injection

Automatically injects hyper-specific seasonal topics into the content pipeline.
Each holiday has a fixed date + seed topics. On first generation during a holiday
window, the LLM generates ~30 niche topics and caches them in performance_context.json.
"""

import json
import logging
import random
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Holiday:
    name: str
    display_name: str
    month: int
    day: int
    lead_days: int = 21
    tail_days: int = 2
    seed_topics: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    # For computed holidays (Easter, Mother's Day, etc.), set month/day to 0
    # and override get_date() via the compute function
    compute_func: Optional[str] = None

    def get_date(self, year: int) -> date:
        """Get the actual date of this holiday for a given year."""
        if self.compute_func == "easter":
            return _compute_easter(year)
        elif self.compute_func == "mothers_day":
            return _nth_weekday(year, 5, 6, 2)  # 2nd Sunday of May
        elif self.compute_func == "fathers_day":
            return _nth_weekday(year, 6, 6, 3)  # 3rd Sunday of June
        elif self.compute_func == "thanksgiving":
            return _nth_weekday(year, 11, 3, 4)  # 4th Thursday of November
        return date(year, self.month, self.day)

    def is_active(self, today: date) -> bool:
        """Check if today falls within this holiday's active window."""
        year = today.year
        holiday_date = self.get_date(year)
        window_start = holiday_date - timedelta(days=self.lead_days)
        window_end = holiday_date + timedelta(days=self.tail_days)
        return window_start <= today <= window_end


def _compute_easter(year: int) -> date:
    """Compute Easter Sunday using the Anonymous Gregorian algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """Find the nth occurrence of a weekday in a month.
    weekday: 0=Monday, 6=Sunday
    """
    first = date(year, month, 1)
    # Days until first occurrence of target weekday
    days_ahead = weekday - first.weekday()
    if days_ahead < 0:
        days_ahead += 7
    first_occurrence = first + timedelta(days=days_ahead)
    return first_occurrence + timedelta(weeks=n - 1)


# ---------------------------------------------------------------------------
# Holiday Calendar
# ---------------------------------------------------------------------------

HOLIDAY_CALENDAR: List[Holiday] = [
    Holiday(
        name="valentines_day", display_name="Valentine's Day",
        month=2, day=14, lead_days=21, tail_days=1,
        seed_topics=["valentine sensory bins for toddlers", "heart-shaped snacks babies can eat",
                     "valentine craft ideas for 1 year olds", "DIY valentine cards with baby footprints"],
        tags=["valentine", "hearts", "love", "pink", "red"],
    ),
    Holiday(
        name="st_patricks_day", display_name="St. Patrick's Day",
        month=3, day=17, lead_days=21, tail_days=1,
        seed_topics=["green sensory bin ideas for babies", "shamrock stamping with toddlers",
                     "st patricks day snacks for baby led weaning", "rainbow activities for 2 year olds"],
        tags=["stpatricks", "green", "rainbow", "shamrock", "lucky"],
    ),
    Holiday(
        name="easter", display_name="Easter",
        month=0, day=0, lead_days=28, tail_days=2, compute_func="easter",
        seed_topics=["easter egg sensory bin for babies", "mess-free easter painting for toddlers",
                     "easter basket ideas for 1 year olds", "egg dyeing safe for babies"],
        tags=["easter", "eggs", "bunny", "spring", "pastel"],
    ),
    Holiday(
        name="mothers_day", display_name="Mother's Day",
        month=0, day=0, lead_days=21, tail_days=1, compute_func="mothers_day",
        seed_topics=["baby footprint gift for mom", "toddler handprint crafts for mothers day",
                     "mothers day breakfast toddler can help make"],
        tags=["mothersday", "mom", "mama"],
    ),
    Holiday(
        name="fathers_day", display_name="Father's Day",
        month=0, day=0, lead_days=21, tail_days=1, compute_func="fathers_day",
        seed_topics=["baby handprint craft for dad", "toddler activities dad can lead",
                     "fathers day gift from baby DIY"],
        tags=["fathersday", "dad", "daddy"],
    ),
    Holiday(
        name="fourth_of_july", display_name="4th of July",
        month=7, day=4, lead_days=21, tail_days=1,
        seed_topics=["baby safe 4th of july sensory play", "red white blue snacks for toddlers",
                     "firework craft for 2 year olds", "noise canceling tips for babies fireworks"],
        tags=["4thofjuly", "fireworks", "redwhiteblue", "patriotic"],
    ),
    Holiday(
        name="halloween", display_name="Halloween",
        month=10, day=31, lead_days=28, tail_days=1,
        seed_topics=["baby safe halloween sensory bin", "pumpkin painting for 1 year olds",
                     "halloween costume ideas baby won't rip off", "spooky snacks for baby led weaning"],
        tags=["halloween", "pumpkin", "spooky", "costume", "trickortreat"],
    ),
    Holiday(
        name="thanksgiving", display_name="Thanksgiving",
        month=0, day=0, lead_days=21, tail_days=1, compute_func="thanksgiving",
        seed_topics=["thanksgiving sensory bin for toddlers", "turkey handprint craft for babies",
                     "thanksgiving foods safe for baby led weaning"],
        tags=["thanksgiving", "turkey", "grateful", "fall"],
    ),
    Holiday(
        name="christmas", display_name="Christmas",
        month=12, day=25, lead_days=28, tail_days=3,
        seed_topics=["baby safe christmas ornament crafts", "toddler gift wrapping station",
                     "christmas sensory bin for 1 year olds", "advent calendar ideas for toddlers"],
        tags=["christmas", "holiday", "santa", "ornament", "gift"],
    ),
    # Seasons
    Holiday(
        name="spring", display_name="Spring",
        month=3, day=20, lead_days=14, tail_days=60,
        seed_topics=["spring sensory bins for babies", "outdoor toddler activities spring",
                     "planting seeds with toddlers", "bug hunt activities for 2 year olds"],
        tags=["spring", "flowers", "garden", "outdoors"],
    ),
    Holiday(
        name="summer", display_name="Summer",
        month=6, day=21, lead_days=14, tail_days=60,
        seed_topics=["water play ideas for babies", "outdoor summer activities toddlers",
                     "mess-free popsicle crafts", "baby pool sensory play"],
        tags=["summer", "water", "sun", "outdoors", "pool"],
    ),
    Holiday(
        name="fall", display_name="Fall",
        month=9, day=22, lead_days=14, tail_days=60,
        seed_topics=["fall leaf sensory bin for babies", "apple stamping craft for toddlers",
                     "pumpkin patch prep with toddler", "cozy indoor activities fall"],
        tags=["fall", "autumn", "leaves", "pumpkin", "cozy"],
    ),
    Holiday(
        name="winter", display_name="Winter",
        month=12, day=21, lead_days=14, tail_days=60,
        seed_topics=["indoor winter activities for toddlers", "snow sensory bin for babies",
                     "hot cocoa play dough recipe", "winter crafts for 1 year olds"],
        tags=["winter", "snow", "cozy", "indoor"],
    ),
]


def get_active_holidays(today: Optional[date] = None) -> List[Holiday]:
    """Return all holidays whose active window includes today."""
    if today is None:
        today = date.today()
    return [h for h in HOLIDAY_CALENDAR if h.is_active(today)]


def generate_seasonal_topics(holiday: Holiday, llm_client) -> List[str]:
    """Use LLM to generate ~30 hyper-specific seasonal topics from seed topics."""
    seeds = ", ".join(holiday.seed_topics)
    prompt = f"""Generate 30 unique, hyper-specific content topics for a parenting TikTok account about {holiday.display_name}, targeting parents of babies and toddlers (0-4 years).

SEED TOPICS (use as inspiration, don't repeat): {seeds}

Rules:
- Each topic: 5-15 words, SPECIFIC enough to be a single TikTok post
- Include age-specific variants (e.g., "for 6 month olds", "for 3 year olds")
- Include craft/DIY topics with specific materials
- Include sensory play ideas themed to {holiday.display_name}
- Include mess-free/easy options for tired parents
- Include food/snack ideas safe for babies
- Include zero-cost/household item versions
- Think TikTok virality: parents should see the topic and think "I NEED to try this"

Return ONLY a JSON array of 30 strings. No explanations."""

    try:
        response = llm_client.chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=2000,
        )
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if not json_match:
            logger.warning(f"Failed to parse seasonal topics for {holiday.name}")
            return holiday.seed_topics[:]
        topics = json.loads(json_match.group())
        # Combine with seeds for a richer pool
        all_topics = list(set(holiday.seed_topics + [t for t in topics if isinstance(t, str)]))
        logger.info(f"🎄 Generated {len(all_topics)} seasonal topics for {holiday.display_name}")
        return all_topics
    except Exception as e:
        logger.warning(f"Failed to generate seasonal topics for {holiday.name}: {e}")
        return holiday.seed_topics[:]


def get_seasonal_pool(context_path: Path, llm_client) -> List[str]:
    """Get or generate cached seasonal topic pool for all active holidays.

    Merges pools for overlapping holidays. Caches in performance_context.json
    under "seasonal_topics" keyed by holiday name + year.
    """
    today = date.today()
    active = get_active_holidays(today)
    if not active:
        return []

    # Load context
    try:
        context = json.loads(context_path.read_text()) if context_path.exists() else {}
    except Exception:
        context = {}

    seasonal_cache = context.get("seasonal_topics", {})
    year = today.year
    merged_pool = []

    for holiday in active:
        cache_key = f"{holiday.name}_{year}"
        if cache_key in seasonal_cache and seasonal_cache[cache_key]:
            merged_pool.extend(seasonal_cache[cache_key])
        else:
            # Generate and cache
            topics = generate_seasonal_topics(holiday, llm_client)
            seasonal_cache[cache_key] = topics
            merged_pool.extend(topics)
            # Write cache immediately
            context["seasonal_topics"] = seasonal_cache
            try:
                context_path.write_text(json.dumps(context, indent=2))
            except Exception as e:
                logger.warning(f"Failed to cache seasonal topics: {e}")

    return merged_pool


def pick_seasonal_topic(
    context_path: Path,
    llm_client,
    recent_topics: set,
    seasonal_ratio: float = 0.25,
) -> Optional[str]:
    """Roll chance for seasonal topic. Returns topic string or None.

    Args:
        context_path: Path to performance_context.json
        llm_client: LLM client for generating topics
        recent_topics: Set of recent topic strings (lowercased) to avoid
        seasonal_ratio: Probability of picking seasonal when holidays are active
    """
    active = get_active_holidays()
    if not active:
        return None

    # Roll the dice
    if random.random() >= seasonal_ratio:
        return None

    pool = get_seasonal_pool(context_path, llm_client)
    if not pool:
        return None

    # Filter out recent topics
    available = [t for t in pool if t.lower() not in recent_topics]
    if not available:
        available = pool  # Fall back to full pool if all used

    return random.choice(available)
