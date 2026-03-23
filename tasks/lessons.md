# Lessons Learned

## 2026-03-01: Visual Review is Non-Negotiable

**Mistake**: Marked carousels as "done" after QA passed without visually reviewing the slides.
**Impact**: Multiple carousels had broken images (floating cribs, steaming baths, duplicate ovens, placeholder text).
**Rule**: ALWAYS open and visually inspect every slide before reporting a carousel as complete. QA only validates text metrics.

## 2026-03-01: Cross-Account Learning Transfer

**Mistake**: SlumberSongs had zero qa_learnings and no safe_sleep_rules, even though DreamtimeLullabies had already solved these problems.
**Impact**: SlumberSongs generated unsafe sleep imagery (sheets, bumpers in cribs), steaming bath water, floating cribs.
**Rule**: When creating content for a new account in a similar domain, transfer relevant qa_learnings and safety rules from existing accounts FIRST.

## 2026-03-01: JSON Parsing Bug for habit_list

**Mistake**: The text parser assumed LLM always returns text format for habit_list. Sometimes it returns JSON.
**Impact**: Slide 1 became "tip 1:" instead of the hook, or slides showed "explanation here" placeholder text.
**Fix**: Updated `_parse_claude_response()` to try JSON parsing for ALL formats, with multi-source hook recovery.
**Rule**: When LLM output format is unpredictable, parse both formats defensively.

## 2026-03-01: Gemini Parallel Rate Limits

**Mistake**: Launched 10 carousels simultaneously, each generating 7 images.
**Impact**: ~50% failure rate from Gemini API errors on later slides.
**Rule**: Batch parallel generations in groups of 4-5 max to avoid Gemini rate limits.

## 2026-03-01: Emoji Execution on SlumberSongs

**Mistake**: CTA examples in content_templates.json included emojis that rendered poorly on slides.
**Rule**: Keep emoji out of CTA examples unless rendering has been verified. Use plain text CTAs.

## 2026-03-01: Gender-Neutral CTAs

**Mistake**: CTA said "tag a tired mama" but Gemini generated an image of a dad.
**Rule**: Use gender-neutral language in CTAs ("tired parent" not "tired mama") unless the image is explicitly controlled.

## 2026-02-28: Niche Topics Drive Engagement

**Insight**: Hyper-specific topics by age + situation + constraint massively outperform generic advice.
**Example**: "water table hack" (52.6K views) vs "picky eater strategies" (1K views).
**Rule**: Tier 3 niche topics should be the majority of content. Generic advice pillars underperform.
