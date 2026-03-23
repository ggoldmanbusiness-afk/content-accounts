"""
Bible Verse Verification Module
Verifies scripture references are real by calling bible-api.com (free, no auth).
"""

import logging
import re
import urllib.parse
import urllib.request
import json

logger = logging.getLogger(__name__)

# Regex pattern for Bible references
# Handles: "psalm 34:18", "2 timothy 1:7", "philippians 4:6-7", "john 3:16"
_BOOK_PATTERN = r'(?:[123]\s+)?[a-zA-Z]+'
_VERSE_PATTERN = r'\d+:\d+(?:-\d+)?'
_REF_PATTERN = re.compile(
    rf'\b({_BOOK_PATTERN})\s+({_VERSE_PATTERN})\b',
    re.IGNORECASE
)

# Known Bible book names for filtering false positives
_BIBLE_BOOKS = {
    'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
    'joshua', 'judges', 'ruth', '1 samuel', '2 samuel',
    '1 kings', '2 kings', '1 chronicles', '2 chronicles',
    'ezra', 'nehemiah', 'esther', 'job', 'psalm', 'psalms',
    'proverbs', 'ecclesiastes', 'song of solomon',
    'isaiah', 'jeremiah', 'lamentations', 'ezekiel', 'daniel',
    'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah',
    'nahum', 'habakkuk', 'zephaniah', 'haggai', 'zechariah', 'malachi',
    'matthew', 'mark', 'luke', 'john', 'acts', 'romans',
    '1 corinthians', '2 corinthians', 'galatians', 'ephesians',
    'philippians', 'colossians', '1 thessalonians', '2 thessalonians',
    '1 timothy', '2 timothy', 'titus', 'philemon',
    'hebrews', 'james', '1 peter', '2 peter',
    '1 john', '2 john', '3 john', 'jude', 'revelation',
}


def extract_references(text: str) -> list[str]:
    """Extract Bible references from text using regex.

    Handles lowercase, numbered books, verse ranges, and single verses.
    """
    refs = []
    for match in _REF_PATTERN.finditer(text):
        book = match.group(1).strip()
        verse = match.group(2).strip()
        # Validate against known book names
        if book.lower() in _BIBLE_BOOKS:
            refs.append(f"{book} {verse}")
    return refs


def verify_reference(ref: str) -> dict:
    """Verify a single scripture reference by calling bible-api.com.

    Args:
        ref: A reference like "Philippians 4:6-7"

    Returns:
        Dict with valid, reference, text/translation (if valid), or error (if not).
    """
    encoded = urllib.parse.quote(ref.strip())
    url = f"https://bible-api.com/{encoded}"

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bible-verify/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if "error" in data:
            return {"valid": False, "reference": ref, "error": data["error"]}

        return {
            "valid": True,
            "reference": data.get("reference", ref),
            "text": data.get("text", "").strip(),
            "translation": data.get("translation_name", "web"),
        }
    except urllib.error.HTTPError as e:
        return {"valid": False, "reference": ref, "error": f"HTTP {e.code}"}
    except Exception as e:
        return {"valid": False, "reference": ref, "error": str(e)}


def verify_all_references(text: str) -> list[dict]:
    """Extract all scripture references from text and verify each one.

    Args:
        text: Full carousel text string.

    Returns:
        List of verification result dicts.
    """
    refs = extract_references(text)
    return [verify_reference(ref) for ref in refs]
