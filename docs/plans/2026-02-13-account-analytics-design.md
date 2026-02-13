# Account Analytics System — Design Document

**Date**: 2026-02-13
**Status**: Approved

## Overview

Add a performance analytics system to content-accounts that scrapes engagement metrics from published posts, analyzes what's working/failing, generates actionable recommendations, and feeds learnings back into the content generator.

## Goals

1. Track real engagement metrics (views, likes, comments, shares, saves) for all published posts
2. Analyze performance by format, topic/pillar, hook style, slide count, and timing
3. Surface actionable insights using marketing psychology frameworks
4. Feed learnings back into the generator via a hybrid approval flow
5. Support ~4 parenting accounts with cross-account comparison

## Architecture

```
core/analytics/
├── db.py              # SQLite schema, migrations, query helpers
├── scraper.py         # Apify-based scraper for own accounts
├── analyzer.py        # Crunches metrics into insights
├── recommender.py     # AI-generated recommendations via Claude
└── dashboard.py       # HTML dashboard generation

cli/analyze.py         # CLI entry point for reports + approval flow

accounts/[name]/performance_context.json  # Learning loop output (generator reads this)
data/analytics.db      # SQLite database (single file)
```

## Data Layer — SQLite Schema

```sql
CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    platform TEXT NOT NULL,           -- tiktok, instagram
    post_id TEXT NOT NULL UNIQUE,     -- platform-specific ID
    post_url TEXT,
    topic TEXT,                       -- from meta.json if matched
    format TEXT,                      -- habit_list, step_guide, scripts, etc.
    hook_text TEXT,                   -- first slide text
    hook_score REAL,                  -- semantic scorer result (0-20)
    slide_count INTEGER,
    content_pillar TEXT,              -- mapped from account config
    published_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE metrics_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id TEXT NOT NULL REFERENCES posts(post_id),
    scraped_at DATETIME NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    saves INTEGER DEFAULT 0,
    engagement_rate REAL DEFAULT 0.0, -- (likes+comments+shares+saves)/views
    UNIQUE(post_id, scraped_at)
);

CREATE TABLE recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',    -- pending, approved, rejected
    category TEXT NOT NULL,           -- format_weight, hook_style, topic_priority,
                                      -- pillar_rebalance, format_experiment,
                                      -- failure_pattern, 80_20_insight, save_vs_share,
                                      -- slide_count, cta_strategy
    insight TEXT NOT NULL,            -- human-readable explanation with data
    proposed_change TEXT NOT NULL,    -- JSON: patch for performance_context.json
    confidence TEXT DEFAULT 'medium', -- high, medium, low (based on sample size)
    approved_at DATETIME
);

-- Views for common queries
CREATE VIEW v_post_performance AS
SELECT
    p.id, p.account_name, p.platform, p.post_id, p.topic, p.format,
    p.hook_text, p.hook_score, p.slide_count, p.content_pillar, p.published_at,
    ms.views, ms.likes, ms.comments, ms.shares, ms.saves, ms.engagement_rate,
    ms.scraped_at
FROM posts p
JOIN metrics_snapshots ms ON p.post_id = ms.post_id
WHERE ms.scraped_at = (
    SELECT MAX(scraped_at) FROM metrics_snapshots WHERE post_id = p.post_id
);

CREATE VIEW v_format_comparison AS
SELECT
    account_name, format,
    COUNT(*) as post_count,
    AVG(views) as avg_views,
    AVG(likes) as avg_likes,
    AVG(saves) as avg_saves,
    AVG(engagement_rate) as avg_engagement_rate
FROM v_post_performance
GROUP BY account_name, format;

CREATE VIEW v_account_summary AS
SELECT
    account_name,
    COUNT(*) as total_posts,
    AVG(views) as avg_views,
    AVG(engagement_rate) as avg_engagement_rate,
    SUM(views) as total_views,
    MAX(views) as best_views
FROM v_post_performance
GROUP BY account_name;
```

### Why SQLite

- Single file, no server, fits the local-first philosophy
- Great for time-series queries and aggregation
- Easy to back up (it's just a file)
- Python stdlib support (no new dependencies)

## Scraping Layer

### Data Source: Apify

Already in the stack from `clone_post.py`. Uses Apify's TikTok Profile Scraper and Instagram Profile Scraper actors.

### Account Config Addition

Each account config gets an optional `platform_profiles` field:

```python
class AccountConfig(BaseModel):
    # ... existing fields ...
    platform_profiles: dict[str, str] = {}
    # e.g. {"tiktok": "dreamtimelullabies", "instagram": "dreamtimelullabies"}
```

### Scrape Flow

```
Daily cron (e.g., 8am)
  → for each account with platform_profiles:
      → Apify scrape profile (last 20-30 posts)
      → match against posts table by post_id
      → new posts → INSERT into posts table
         → backfill: match against output/ dirs by date/topic for meta.json data
      → all posts → INSERT metrics_snapshot with current numbers
      → log: "Scraped 24 posts for dreamtimelullabies, 3 new"
```

### Backfill Strategy

For posts published before the analytics system existed:
- Scraper finds posts not in the database
- Attempts to match against `accounts/[name]/output/` directories by published date and topic similarity
- If matched: populates topic, format, hook_text, hook_score, slide_count from carousel_data.json
- If unmatched: still tracks the post, just without generation metadata

## Analysis Engine

### core/analytics/analyzer.py

Crunches raw data into structured insights using marketing psychology frameworks.

### Analysis Dimensions

**1. Format Performance (Pareto / 80/20)**
- Average engagement rate, saves, views by format
- Identify the 20% of formats driving 80% of engagement
- Per-account and cross-account

**2. Failure Analysis (Survivorship Bias)**
- Explicitly surface worst-performing posts and patterns
- "Posts with generic question hooks average 40% less engagement"
- What formats/topics/hooks consistently underperform

**3. Content Pillar Performance**
- Map posts to content pillars from account config
- Which pillars drive engagement, which are dead weight
- Pillar rebalancing recommendations

**4. Save vs Share Classification**
- Tag posts by primary engagement type (high-save vs high-share)
- Track which formats/hooks drive each behavior
- Different optimization strategies for each

**5. Hook Analysis**
- Correlate hook_score with actual engagement
- Identify which hook *styles* perform best (numbers, questions, controversy)
- Update reference hooks for the semantic scorer

**6. Slide Count Optimization**
- Performance by slide count
- Optimal range per format

**7. Timing Patterns**
- Day-of-week and time-of-day performance
- Post frequency vs engagement (diminishing returns detection)

**8. Growth Curves**
- Which posts have long tails (keep getting views) vs spike-and-die
- Uses time-series from metrics_snapshots

**9. Cross-Account Patterns**
- What works across all parenting accounts vs account-specific
- Universal hooks/formats vs niche-dependent ones

**10. Exploration vs Exploitation Balance**
- Flag when an account is over-indexing on one format
- Suggest experiments for untested formats/topics
- Prevent local optimum traps

## Recommender

### core/analytics/recommender.py

Takes analyzer output and generates actionable proposals via Claude.

### Recommendation Categories

| Category | Example |
|----------|---------|
| `format_weight` | "step_guide outperforms habit_list by 2.5x on saves. Increase weight." |
| `hook_style` | "Number-specific hooks average 45% more engagement. Add to reference hooks." |
| `topic_priority` | "Sleep content is your highest performer. Increase generation frequency." |
| `pillar_rebalance` | "Sleep is 15% of posts but 40% of saves. Baby products is 20% of posts but 3% of saves." |
| `format_experiment` | "You haven't tried how_to format in 3 weeks. Last 2 performed well." |
| `failure_pattern` | "Posts with 7+ slides consistently underperform 5-slide posts by 35%." |
| `80_20_insight` | "Your top 3 topics account for 72% of total engagement." |
| `save_vs_share` | "High-save posts use scripts format. High-share posts use controversy hooks." |
| `slide_count` | "5-slide posts outperform 7-slide posts by 28%. Adjust default." |
| `cta_strategy` | "save_this CTA drives 2x more saves than comment CTA." |

### Recommendation Structure

Each recommendation includes:
- **Insight**: Human-readable explanation with supporting data
- **Proposed change**: JSON patch for performance_context.json
- **Confidence**: high/medium/low based on sample size
- **Category**: Classification for filtering

### Weekly Cycle

```
Monday cron
  → analyzer.py runs across all accounts
  → recommender.py generates 3-5 recommendations per account
  → saves to recommendations table with status=pending
  → next CLI interaction shows pending recommendations
```

### Approval Flow (Hybrid)

```
$ python -m cli.analyze --account dreamtimelullabies

 You have 4 pending recommendations:

1. [HIGH] format_weight: step_guide outperforms habit_list by 2.5x on saves (47 posts sampled)
   Proposed: Increase step_guide weight to 1.4, decrease habit_list to 0.8
   [y] approve  [n] reject  [s] skip

2. [MEDIUM] pillar_rebalance: Sleep content is 15% of posts but 40% of saves
   Proposed: Add sleep_routines to top_pillars priority list
   [y] approve  [n] reject  [s] skip

...
```

Approved recommendations update `performance_context.json`. Rejected ones are logged for future reference.

## Output Layer

### A. CLI Reports (`cli/analyze.py`)

```bash
# Account overview with pending recommendations
python -m cli.analyze --account dreamtimelullabies

# Cross-account comparison
python -m cli.analyze --all

# Focused reports
python -m cli.analyze --account dreamtimelullabies --focus formats
python -m cli.analyze --account dreamtimelullabies --focus pillars
python -m cli.analyze --account dreamtimelullabies --focus failures
python -m cli.analyze --account dreamtimelullabies --focus hooks
```

### B. HTML Dashboard (`--dashboard` flag)

```bash
python -m cli.analyze --account dreamtimelullabies --dashboard
```

Self-contained HTML file (no server) with:
- Engagement trend line chart (over time)
- Format performance bar chart
- Content pillar heatmap
- Save vs share scatter plot
- Post performance table (sortable)
- Cross-account comparison panel (with `--all`)

Uses inline Chart.js or pure SVG. Single file, opens in browser.

### C. Performance Context (`performance_context.json`)

What the generator reads. Updated only on approved recommendations:

```json
{
  "last_updated": "2026-02-13",
  "sample_size": 47,
  "format_weights": {
    "step_guide": 1.4,
    "habit_list": 0.8,
    "scripts": 1.2,
    "boring_habits": 1.0
  },
  "top_pillars": ["sleep_routines", "tantrum_management", "picky_eating"],
  "underperforming_pillars": ["baby_products"],
  "optimal_slide_count": 5,
  "hook_insights": {
    "best_styles": ["number_specific", "controversy_light"],
    "worst_styles": ["generic_question"],
    "reference_hooks": ["5 boring habits...", "Stop doing this..."]
  },
  "save_vs_share": {
    "high_save_formats": ["scripts", "step_guide"],
    "high_share_formats": ["boring_habits"]
  },
  "experiment_suggestions": ["how_to format untested", "7-slide posts untested"],
  "approved_recommendations": [
    {
      "id": "rec_001",
      "insight": "step_guide 2.5x saves vs habit_list",
      "approved_at": "2026-02-10"
    }
  ]
}
```

### Generator Integration

The generator reads `performance_context.json` and:
- Weights random format selection toward `format_weights`
- Prefers `top_pillars` for topic selection
- Uses `hook_insights.reference_hooks` as additional examples for the semantic scorer
- Occasionally picks from `experiment_suggestions` to maintain exploration

## Automation — Cron Schedule

```
# Daily: scrape metrics (8am)
0 8 * * * cd /path/to/content-accounts && python -m core.analytics.scraper

# Weekly: run analysis + generate recommendations (Monday 9am)
0 9 * * 1 cd /path/to/content-accounts && python -m core.analytics.recommender
```

Set up via macOS `launchd` or crontab.

## Dependencies

- **New**: None beyond Python stdlib (sqlite3 is built-in)
- **Existing**: Apify (already used), OpenRouter/Claude (already used), Chart.js (CDN, inline in HTML)

## Accounts (Initial)

1. dreamtimelullabies
2. mymomskills
3. slumbersongs
4. parentplaybook (eventually)

All parenting niche — cross-account comparison will surface universal patterns.

## File Changes Summary

### New Files
- `core/analytics/db.py`
- `core/analytics/scraper.py`
- `core/analytics/analyzer.py`
- `core/analytics/recommender.py`
- `core/analytics/dashboard.py`
- `core/analytics/__init__.py`
- `cli/analyze.py`
- `data/analytics.db` (created at runtime)
- `accounts/[name]/performance_context.json` (created by recommender)

### Modified Files
- `core/config_schema.py` — add `platform_profiles` field to AccountConfig
- `core/generator.py` — read `performance_context.json` for format/topic weighting
- Account configs — add `platform_profiles` mapping
