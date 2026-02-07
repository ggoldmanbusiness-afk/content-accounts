"""
Prompt Templates
Reusable prompt templates for content generation
"""

from typing import Optional, Dict, List


def _build_dynamic_hook_instruction(
    topic: str,
    format_identity: str,
    max_words: int,
    num_items: int,
    niche: str = "general content",
    score_feedback: Optional[Dict] = None,
    hook_examples: Optional[Dict] = None,
    hook_formulas: Optional[List[str]] = None,
) -> str:
    """Build a dynamic hook instruction block that lets Claude generate creative hooks."""

    # Build retry warning if previous attempt failed
    retry_warning = ""
    if score_feedback:
        retry_warning = f"""⚠️  PREVIOUS HOOK FAILED (scored {score_feedback['total']}/20, need {score_feedback.get('min_score', 16)}+)
Fix these issues:
"""
        for issue in score_feedback.get("feedback", []):
            retry_warning += f"- {issue}\n"
        retry_warning += "\n"

    # Build examples section from account config
    examples_section = ""
    all_examples = []

    if hook_examples:
        for category, examples in hook_examples.items():
            if isinstance(examples, list):
                all_examples.extend(examples)

    if hook_formulas:
        all_examples.extend(hook_formulas)

    if all_examples:
        formatted = "\n".join(f"- {ex}" for ex in all_examples[:8])
        examples_section = f"""
EXAMPLES OF HOOKS THAT PERFORM WELL (for inspiration, do NOT copy):
{formatted}
"""
    else:
        examples_section = """
EXAMPLES OF HOOKS THAT PERFORM WELL (for inspiration, do NOT copy):
- 5 bedtime mistakes keeping your baby awake
- the one thing that changed our nights
- why your morning routine keeps failing (it's not what you think)
- 3 things to fix tonight for better results
- what I wish I knew about sleep schedules
"""

    return f"""{retry_warning}SLIDE 1 (Hook) - WRITE A CREATIVE, SCROLL-STOPPING HOOK:

This is a {format_identity} carousel about "{topic}" for {niche}.

HOOK REQUIREMENTS:
- MUST be ≤{max_words} words, all lowercase
- MUST be grammatically natural for the topic "{topic}"
- Create a curiosity gap (promise insight without revealing it)
- Feel actionable (clear benefit or transformation)
- Be specific (numbers, details, concrete language)
- Include a pattern interrupt (unexpected angle, contrarian take)
- NO quotes, no meta-text
{examples_section}
Generate an ORIGINAL hook that fits "{topic}" naturally.
Write the complete hook (≤{max_words} words, all lowercase):"""


def build_system_prompt(brand_identity: Dict, content_templates: Optional[Dict] = None) -> str:
    """
    Build system prompt from brand identity and content templates

    Args:
        brand_identity: Dict with personality, voice_attributes, etc.
        content_templates: Optional dict from content_templates.json

    Returns:
        System prompt string
    """
    personality = brand_identity.get("personality", "Expert content creator")
    voice_attrs = brand_identity.get("voice_attributes", [])

    voice_description = ", ".join(voice_attrs[:3]) if voice_attrs else "conversational"

    # Get conversational elements from templates if available
    if content_templates and "style_guidelines" in content_templates:
        style = content_templates["style_guidelines"]
        conversational_elements = style.get("conversational_elements", ["honestly", "yes really", "worth it though"])
        tone = style.get("tone", "conversational but evidence-backed")
        voice = style.get("voice", "like texting a friend")

        elements_str = "', '".join(conversational_elements[:4])

        return f"""{personality}. Your voice is {voice_description}. {voice}. Include phrases like '{elements_str}.' Tone: {tone}. Make it feel conversational, not clinical. Use lowercase, short sentences, and avoid fluff."""

    # Fallback to generic
    return f"""{personality}. Your voice is {voice_description}. Write like you're texting a friend who just asked for advice - warm, personal, with asides and opinions. Include phrases like 'honestly,' 'yes really,' 'worth it though.' Your content is casual but evidence-backed. Make it feel conversational, not clinical. Use lowercase, short sentences, and avoid fluff."""


def build_habit_list_prompt(
    topic: str,
    num_items: int,
    hook_strategy: str,
    max_words: int,
    score_feedback: Optional[Dict] = None,
    niche: str = "general content",
    content_templates: Optional[Dict] = None,
    hook_examples: Optional[Dict] = None,
    hook_formulas: Optional[List[str]] = None,
) -> str:
    """Build prompt for habit_list format"""

    # Extract style from templates if available
    if content_templates and "style_guidelines" in content_templates:
        style = content_templates["style_guidelines"]
        conversational_elements = style.get("conversational_elements", ["honestly", "yes really", "worth it though"])
        examples = style.get("examples", {})
        bad_example = examples.get("bad_generic", "Generic corporate language")
        good_example = examples.get("good_conversational", "Conversational authentic language")
    else:
        conversational_elements = ["honestly", "yes really", "worth it though"]
        bad_example = "Research indicates that schedules significantly impact outcomes"
        good_example = "turns out timing matters more than effort (who knew?)"

    conv_elements_str = '", "'.join(conversational_elements[:4])

    # Build hook instruction
    if hook_strategy == "viral":
        hook_instruction = _build_dynamic_hook_instruction(
            topic=topic, format_identity="underrated tips/habits list",
            max_words=max_words, num_items=num_items, niche=niche,
            score_feedback=score_feedback, hook_examples=hook_examples,
            hook_formulas=hook_formulas,
        )
    else:
        hook_instruction = f"""SLIDE 1 (Hook):
Write a compelling hook about "{topic}" (≤{max_words} words, all lowercase)
- Promise transformation or reveal
- NO quotes or meta-text"""

    return f"""Generate a TikTok carousel about "{topic}" for {niche}.

FORMAT: Habit/Tip List with {num_items} tips + final CTA slide

{hook_instruction}

SLIDES 2-{num_items + 1} (Tips):
CRITICAL: Each tip MUST start with "tip 1:", "tip 2:", "tip 3:", etc. This is REQUIRED, not meta-text.

Format for each tip:
tip 1: [actionable habit - 3-5 words]

[explanation - 2-4 short sentences explaining WHY it works, with conversational asides like "{conv_elements_str}" etc. Make it feel like texting a friend, not a textbook. Mix short punchy statements with longer explanations.]

EXAMPLE TIP FORMAT:
tip 1: call early morning only

most reps call at 10am when everyone's in meetings. here's the thing - 7-8am catches decision makers at their desk, inbox empty. I tried this for 30 days and connect rate jumped from 12% to 31%. nobody talks about this but timing beats everything.

SLIDE {num_items + 2} (CTA):
save this so you can come back to it when you need it

STYLE RULES:
- REQUIRED: Start each tip with "tip 1:", "tip 2:", etc (this is NOT meta-text to skip)
- All lowercase (except "I")
- Conversational tone like texting a friend
- Include asides and opinions ("{conv_elements_str}")
- Mix short punchy statements with explanations
- Specific details (times, numbers, exact steps)
- NO quotation marks
- NO generic meta-text like "SLIDE X:" or "Hook:" (but "tip N:" is REQUIRED)
- Write ONLY the text that appears on screen

CONVERSATIONAL EXAMPLES:
BAD (too clinical): "{bad_example}"
GOOD (conversational): "{good_example}"

Generate {num_items} tips about "{topic}"."""


def build_step_guide_prompt(
    topic: str,
    num_items: int,
    hook_strategy: str,
    max_words: int,
    score_feedback: Optional[Dict] = None,
    niche: str = "general content",
    content_templates: Optional[Dict] = None,
    hook_examples: Optional[Dict] = None,
    hook_formulas: Optional[List[str]] = None,
) -> str:
    """Build prompt for step_guide format"""

    # Extract style from templates if available
    if content_templates and "style_guidelines" in content_templates:
        style = content_templates["style_guidelines"]
        conversational_elements = style.get("conversational_elements", ["honestly", "yes really", "worth it though"])
        examples = style.get("examples", {})
        bad_example = examples.get("bad_generic", "Generic corporate language")
        good_example = examples.get("good_conversational", "Conversational authentic language")
    else:
        conversational_elements = ["honestly", "yes really", "worth it though"]
        bad_example = "Implement consistent protocols for optimal results"
        good_example = "stick to the same approach every time - it actually works (worth it)"

    conv_elements_str = '", "'.join(conversational_elements[:4])

    # Build hook instruction
    if hook_strategy == "viral":
        hook_instruction = _build_dynamic_hook_instruction(
            topic=topic, format_identity="sequential step-by-step action guide",
            max_words=max_words, num_items=num_items, niche=niche,
            score_feedback=score_feedback, hook_examples=hook_examples,
            hook_formulas=hook_formulas,
        )
    else:
        hook_instruction = f"""SLIDE 1 (Hook):
Write a compelling hook about "{topic}" (≤{max_words} words, all lowercase)
- NO quotes or meta-text"""

    return f"""Generate a TikTok carousel about "{topic}" for {niche}.

FORMAT: Step-by-Step Guide with {num_items} steps + final CTA slide

{hook_instruction}

SLIDES 2-{num_items + 1} (Steps):
CRITICAL: Each step MUST start with "step 1:", "step 2:", "step 3:", etc. This is REQUIRED, not meta-text.

Format for each step:
step 1: [action phrase - 3-5 words]

[explanation - 2-4 short sentences explaining the step in conversational tone. Include asides like "{conv_elements_str}" etc. Make it feel like a friend giving advice, not a manual.]

EXAMPLE STEP FORMAT:
step 1: start with research

most people skip this. here's the thing - 10 minutes of research saves hours of wasted effort. I learned this the hard way after building the wrong thing twice. nobody talks about this but understanding the problem beats jumping to solutions.

SLIDE {num_items + 2} (CTA):
save this so you can come back to it when you need it

STYLE RULES:
- REQUIRED: Start each step with "step 1:", "step 2:", etc (this is NOT meta-text to skip)
- All lowercase (except "I")
- Conversational, human tone (like texting a friend)
- Include personal voice ("{conv_elements_str}")
- Specific, actionable steps
- NO quotation marks
- NO generic meta-text like "SLIDE X:" or "Hook:" (but "step N:" is REQUIRED)

CONVERSATIONAL EXAMPLES:
BAD (too clinical): "{bad_example}"
GOOD (conversational): "{good_example}"

Generate {num_items} steps for "{topic}"."""


def build_scripts_prompt(
    topic: str,
    num_categories: int = 4,
    max_words: int = 20,
    niche: str = "general content",
    score_feedback: Optional[Dict] = None,
    hook_examples: Optional[Dict] = None,
    hook_formulas: Optional[List[str]] = None,
    content_templates: Optional[Dict] = None,
) -> str:
    """
    Build prompt for 'Scripts That Work' format
    PROVEN PERFORMANCE: 2,746 views average, 21+ saves
    """
    hook_instruction = _build_dynamic_hook_instruction(
        topic=topic, format_identity="exact-phrases-to-use 'scripts that work' carousel",
        max_words=max_words, num_items=num_categories, niche=niche,
        score_feedback=score_feedback, hook_examples=hook_examples,
        hook_formulas=hook_formulas,
    )

    return f"""Generate a "Scripts That Work" carousel for {topic}.

This format provides exact phrases parents can say immediately - copy-paste solutions they can screenshot and use tonight.

PROVEN PERFORMANCE: 2,746 views average, 21+ saves

FORMAT: {num_categories} script categories + final CTA slide

{hook_instruction}

SLIDES 2-{num_categories + 1} (Script Categories):
CRITICAL: Each category MUST start with "script 1:", "script 2:", etc. This is REQUIRED.

Format for each category:
script 1: when they're [situation]

• [exact phrase to say - ≤8 words]
• [exact phrase to say - ≤8 words]
• [exact phrase to say - ≤8 words]

EXAMPLE:
script 1: when they're upset

• I see you're feeling big feelings
• your feelings are okay
• let's breathe together

SLIDE {num_categories + 2} (CTA):
save this for tonight 💙

STYLE RULES:
- REQUIRED: Start each category with "script 1:", "script 2:", etc
- All lowercase
- Each script phrase ≤8 words
- 3-4 exact phrases per category
- Warm, empathetic but direct tone
- Focus on what TO say (not what NOT to say)
- Make scripts feel natural, not clinical
- Cover {num_categories} different scenarios

Target audience: Exhausted parents who need immediate solutions

Generate {num_categories} script categories for "{topic}"."""


def build_boring_habits_prompt(
    topic: str,
    num_habits: int = 5,
    max_words: int = 20,
    niche: str = "general content",
    score_feedback: Optional[Dict] = None,
    hook_examples: Optional[Dict] = None,
    hook_formulas: Optional[List[str]] = None,
    content_templates: Optional[Dict] = None,
) -> str:
    """
    Build prompt for 'X Boring Habits That Changed Everything' format
    PROVEN PERFORMANCE: 1,386 views average
    """
    hook_instruction = _build_dynamic_hook_instruction(
        topic=topic, format_identity="simple unglamorous habits with outsized impact",
        max_words=max_words, num_items=num_habits, niche=niche,
        score_feedback=score_feedback, hook_examples=hook_examples,
        hook_formulas=hook_formulas,
    )

    return f"""Generate a "Boring Habits That Changed Everything" carousel for {topic}.

This format focuses on simple, unglamorous habits that have outsized impact - NOT flashy tips.

PROVEN PERFORMANCE: 1,386 views average

FORMAT: {num_habits} habits + final CTA slide

{hook_instruction}

SLIDES 2-{num_habits + 1} (Habits):
CRITICAL: Each habit MUST start with "habit 1:", "habit 2:", etc. This is REQUIRED.

Format for each habit:
habit 1: [boring habit - 3-6 words]
([scientific reason in parentheses])

[1-2 sentences explaining why this boring thing actually works. Keep it conversational and brief.]

EXAMPLE:
habit 1: same wake time daily
(even on weekends)

yes I know it sounds too simple. but circadian rhythm needs consistency. their nervous system learns to predict the day. cortisol regulation improves. honestly it's the most boring advice that actually works.

SLIDE {num_habits + 2} (CTA):
try one tonight 💙

STYLE RULES:
- REQUIRED: Start each habit with "habit 1:", "habit 2:", etc
- All lowercase (except "I")
- Conversational, honest tone ("I know this sounds...", "honestly", "yes really")
- Each habit header ≤6 words
- Focus on boring/obvious things parents skip
- Make it feel doable

Generate {num_habits} boring habits about "{topic}"."""


def build_how_to_prompt(
    outcome: str,
    num_steps: int = 5,
    max_words: int = 20,
    niche: str = "general content",
    score_feedback: Optional[Dict] = None,
    hook_examples: Optional[Dict] = None,
    hook_formulas: Optional[List[str]] = None,
    content_templates: Optional[Dict] = None,
) -> str:
    """
    Build prompt for 'How to [Outcome]' format
    PROVEN PERFORMANCE: 2,049 views average
    """
    hook_instruction = _build_dynamic_hook_instruction(
        topic=outcome, format_identity="how-to guide providing a clear roadmap to a specific outcome",
        max_words=max_words, num_items=num_steps, niche=niche,
        score_feedback=score_feedback, hook_examples=hook_examples,
        hook_formulas=hook_formulas,
    )

    return f"""Generate a "How to" step-by-step carousel about {outcome}.

This format delivers a clear roadmap to achieve a specific outcome parents want.

PROVEN PERFORMANCE: 2,049 views average

FORMAT: {num_steps} sequential steps + final CTA slide

{hook_instruction}

SLIDES 2-{num_steps + 1} (Steps):
CRITICAL: Each step MUST start with "step 1:", "step 2:", etc. This is REQUIRED.

Format for each step:
step 1: [action phrase - 3-6 words]
(brief scientific reason in parentheses)

[1-2 sentences explaining why this step works. Keep it clear and confident.]

EXAMPLE:
step 1: start bedtime at same time
(every single night)

consistency cues circadian rhythm. their body learns when sleep is coming. melatonin production syncs up. yes it means weekends too but it works.

SLIDE {num_steps + 2} (CTA):
save for later 💙

STYLE RULES:
- REQUIRED: Start each step with "step 1:", "step 2:", etc
- All lowercase (except "I")
- Each step header ≤6 words
- Steps must be sequential (order matters)
- Include brief "why" in parentheses
- Clear, confident, actionable tone
- Avoid negative framing

Target outcome: {outcome}

Generate {num_steps} sequential steps for "{outcome}"."""
