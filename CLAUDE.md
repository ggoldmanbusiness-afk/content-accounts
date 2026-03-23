# CLAUDE.md - Content Accounts Framework

> Global workflow is in ~/.claude/CLAUDE.md

## Project Context
- **Repo**: `/Users/grantgoldman/Documents/GitHub/content-accounts`
- **Stack**: Python 3.9+, OpenRouter (Claude Sonnet 4.5), Gemini (image gen), Pilmoji (text overlays)
- **Accounts**: dreamtimelullabies (parenting/activities), slumbersongs (baby sleep/lullabies)
- **Output**: Google Drive auto-sync per account

## Active Accounts

### dreamtimelullabies
- **Focus**: Activities, sensory play, sleep routines for babies/toddlers
- **Top format**: habit_list (3,605 avg views, 5.21% engagement)
- **Top pillar**: Activities & Play (226% of avg views)
- **Proven visuals**: iPhone-authentic, natural lighting, warm golden, outdoor/wide shots
- **Retired pillars**: screen time, picky eater strategies, products & gear

### slumbersongs
- **Focus**: Baby sleep, lullabies, bedtime routines, personalized music
- **Brand**: SlumberSongs — personalized custom lullabies
- **Stage**: Exploration (testing all pillars)
- **CTA requirement**: Must mention slumbersongs.com or "link in bio"

## Content Generation Workflow

1. Run analytics first: `daily_scrape.py` → `--refresh-context` → `weekly_recommend.py` → `--dashboard`
2. Pick topics from performance_context.json tier system (tier 1 = proven, tier 3 = niche/explore)
3. Generate with `python3 -m cli.generate --account NAME --topic "..." --format habit_list`
4. **ALWAYS visually review generated slides before marking as done** — QA only checks text, not images
5. Regenerate broken carousels individually to save tokens

## Critical Rules

### Safe Sleep (BOTH accounts)
- Cribs: empty except baby in sleep sack. NO blankets, sheets, bumpers, pillows, stuffed animals
- Cribs: against a wall, in bedroom/nursery only. Never floating, never in kitchen/living room
- Cribs: must have visible vertical wooden slat bars
- Bath water: lukewarm, never steaming
- One child per scene unless topic is siblings

### Visual Consistency
- Same room, same furniture, same layout across ALL slides in a carousel
- Objects must be proportional (no giant mobiles, oversized furniture)
- No floating/disconnected limbs
- No dirty/murky water in play/bath scenes
- Children in appropriate attire (diaper/swimwear for water play, not fully clothed)

### Text/Content
- Slide 1 MUST be the hook, never "tip 1:"
- No placeholder text ("explanation here", "[hook text]")
- Gender-neutral CTAs ("tired parent" not "tired mama") unless image matches
- SlumberSongs: no emojis on slides

## Known Bugs & Fixes

### JSON Parsing / Missing Hook (fixed 2026-03-01)
**Bug**: habit_list format uses text parser, but LLM sometimes returns JSON. Text parser can't find hook in JSON, slide 1 becomes "tip 1:" or placeholder.
**Fix**: `core/generator.py` `_parse_claude_response()` now tries JSON parsing for ALL formats. Extracts hook from top-level "hook" field, slide with type "hook", or generates fallback.
**File**: `core/generator.py` lines 635-677

### Gemini Rate Limiting
**Issue**: Running 8+ parallel carousels overloads Gemini API, causing image generation failures on later slides.
**Workaround**: Retry failed carousels. Consider batching in groups of 4-5.

### OpenRouter Timeouts
**Issue**: Intermittent `Read timed out` errors from OpenRouter API.
**Workaround**: Retry. Usually succeeds on second attempt.

## Architecture Notes

### QA System
- Programmatic checks (always): word count, slide count, aspect ratio, captions
- LLM image QA (optional, ~$0.10/carousel): uses GPT-4o vision
- qa_learnings.json: per-account, injected into BOTH image generation prompts AND QA checks
- **QA does NOT catch visual issues** — must manually review slides

### Image Generation Pipeline
- Claude generates contextual scene descriptions per slide
- Gemini renders images from descriptions
- Performance data (visual_insights) guides exploit/explore ratio
- qa_learnings appended as "PAST ISSUES TO AVOID" in prompts
- safe_sleep_rules from scenes.json injected for sleep-related content

### Key Config Files Per Account
- `config.py` — account settings, pillars, hashtags
- `content_templates.json` — formats, prompts, CTA examples, hook scoring refs
- `scenes.json` — aesthetic styles, safe_sleep_rules, scene library
- `qa_learnings.json` — visual issues to avoid (injected into generation)
- `performance_context.json` — analytics-driven strategy (auto-updated)
