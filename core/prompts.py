"""
Prompt Templates
Reusable prompt templates for content generation
"""

from typing import Optional, Dict


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
    content_templates: Optional[Dict] = None
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

    # Build hook instruction based on strategy
    if hook_strategy == "viral":
        retry_warning = ""
        if score_feedback:
            retry_warning = f"""⚠️  PREVIOUS HOOK FAILED (scored {score_feedback['total']}/20, need {score_feedback.get('min_score', 16)}+)
Fix these issues:
"""
            for issue in score_feedback.get("feedback", []):
                retry_warning += f"- {issue}\n"
            retry_warning += "\n"

        hook_instruction = f"""{retry_warning}SLIDE 1 (Hook) - FILL IN THE TEMPLATE:

Use this exact template:
"why your [BLANK 1] keeps failing (the {num_items} things no one talks about)"

BLANK 1 instructions:
- Fill with specific aspect of "{topic}"
- Make it specific to {niche} situations
- NOT generic

Now fill BLANK 1 for "{topic}":
Write the complete hook (≤{max_words} words, all lowercase):"""
    else:
        # Template hook
        hook_instruction = f"""SLIDE 1 (Hook):
Write: {num_items} boring {topic} habits that changed everything
- Use "boring" or similar downplaying words
- Promise transformation
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
    content_templates: Optional[Dict] = None
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
        hook_instruction = f"""SLIDE 1 (Hook) - VIRAL PATTERN:
Choose ONE proven viral hook pattern for "{topic}":

1. "the [topic] order that actually works (most people do this backward)"
2. "why your [topic] keeps failing (the missing step no one talks about)"
3. "how to [goal] by doing less (it's the opposite of what you'd think)"
4. "building a [topic] that works takes [X days]. here's what actually happens"

REQUIREMENTS:
- MUST be ≤{max_words} words
- MUST use lowercase
- MUST include pattern interrupt (backward, opposite, no one talks about)
- MUST create curiosity gap
- MUST be specific (use numbers/times)
- NO quotes or meta-text"""

        if score_feedback:
            hook_instruction += f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n"
            for issue in score_feedback.get("feedback", []):
                hook_instruction += f"- {issue}\n"
    else:
        # Template hook
        hook_instruction = f"""SLIDE 1 (Hook):
Write: how to build a {topic} that actually works
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
