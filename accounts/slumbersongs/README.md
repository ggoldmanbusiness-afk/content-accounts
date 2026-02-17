# SlumberSongs (@slumbersongs)

Custom lullabies with your child's name, personality, and quirks woven in.

## Content Types

1. **Video lullabies** — Generated via `slumbersongs/scripts/generate-content-video.ts`, output to Google Drive
2. **Tip carousels** — Generated via `content-accounts` framework, output to Google Drive

Both output to: `/Users/grantgoldman/Google Drive/My Drive/SlumberSongs/`

## Generate Content

```bash
# Carousel
python -m cli.generate --account slumbersongs --random

# Video (from slumbersongs repo)
cd ~/Documents/GitHub/slumbersongs
npx tsx scripts/generate-content-video.ts --name Sophia --pronouns she --genre classic-lullaby
```

## Analytics

```bash
python -m cli.analyze --account slumbersongs
python -m cli.analyze --account slumbersongs --dashboard
```
