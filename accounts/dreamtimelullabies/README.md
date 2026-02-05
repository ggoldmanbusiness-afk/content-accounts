# Dreamtime Lullabies

Parenting content account focused on baby sleep and child development.

## Account Info

- **Display Name**: Dreamtime Lullabies
- **Niche**: Baby sleep, parenting tips, child development
- **Character Type**: Faceless expert
- **Brand Voice**: Clear, direct, evidence-based, practical

## Content Pillars

40+ topics covering:
- Sleep schedules and routines
- Development milestones
- Feeding & nutrition
- Behavior & discipline
- Play & activities
- Safety, health, products, general parenting

## Generation

```bash
# Random carousel
python -m cli.generate --account dreamtimelullabies --random

# Specific topic
python -m cli.generate --account dreamtimelullabies --topic "sleep schedules"

# Batch generation
python -m cli.generate --account dreamtimelullabies --random --count 5
```

## Output

Generated content is saved to:
```
/Users/grantgoldman/Google Drive/My Drive/DreamtimeLullabies/
├── YYYY/
│   └── MM-month/
│       └── YYYY-MM-DD_topic-slug/
│           ├── slides/
│           ├── caption.txt
│           └── meta.json
```

## History

Topic history tracked in `output/history/topic_history.json` (max 10 topics).
