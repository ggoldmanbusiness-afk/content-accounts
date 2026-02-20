"""
Post-Generation QA System for Carousel Generator

Hybrid QA: programmatic checks always run (free, fast),
LLM image review runs only when image_qa=True (~$0.10/carousel via GPT-4o).

No auto-regeneration — flags issues clearly, user decides what to regenerate.
"""

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union

from PIL import Image

logger = logging.getLogger(__name__)

# Structural labels that should never appear in rendered slide text
STRUCTURAL_LABEL_PATTERNS = [
    r"^HOOK:",
    r"^TIP SLIDES?:",
    r"^CTA:",
    r"^SLIDE \d+:",
    r"^CLOSING SLIDE:",
    r"^CAPTION:",
    r"^IMAGE PROMPT:",
]

# Placeholder text patterns
PLACEHOLDER_PATTERNS = [
    r"\[hook text\]",
    r"\[your .+?\]",
    r"\[insert .+?\]",
    r"explanation here",
    r"tip goes here",
    r"text here",
    r"\[TODO\]",
]


class CarouselQAChecker:
    """Run quality checks on generated carousels."""

    def __init__(self, openrouter_api_key: Optional[str] = None, qa_config=None, learnings_path=None):
        self.api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.qa_config = qa_config
        self.learnings_path = Path(learnings_path) if learnings_path else None

    def check(self, output_dir: Union[str, Path], image_qa: bool = False) -> Dict:
        """
        Run QA checks on a single carousel.

        Args:
            output_dir: Path to carousel output directory
            image_qa: If True, run LLM vision checks on images (~$0.10)

        Returns:
            QA report dict with check results
        """
        output_dir = Path(output_dir)
        report = {
            "output_dir": str(output_dir),
            "checks": {},
            "summary": {"pass": 0, "fail": 0, "warn": 0},
        }

        # Load carousel data
        carousel_data = self._load_carousel_data(output_dir)
        slides_dir = output_dir / "slides"

        # Run all programmatic checks
        checks = [
            self._check_slide_count_match(carousel_data, slides_dir),
            self._check_structural_labels(carousel_data),
            self._check_placeholder_text(carousel_data),
            self._check_image_files_exist(carousel_data, slides_dir),
            self._check_caption_exists(output_dir),
            self._check_caption_length(output_dir),
            self._check_hook_word_count(carousel_data),
            self._check_meta_completeness(output_dir),
            self._check_no_duplicate_slides(carousel_data),
            self._check_image_aspect_ratio(slides_dir),
        ]

        # Account-specific checks (only if qa_config provides non-empty lists)
        if self.qa_config:
            if getattr(self.qa_config, 'caption_must_contain', None):
                checks.append(self._check_caption_must_contain(output_dir))
            if getattr(self.qa_config, 'caption_must_not_contain', None):
                checks.append(self._check_caption_must_not_contain(output_dir))
            if getattr(self.qa_config, 'forbidden_slide_words', None):
                checks.append(self._check_forbidden_slide_words(carousel_data))

        for check_result in checks:
            name = check_result["name"]
            report["checks"][name] = check_result
            report["summary"][check_result["status"]] += 1

        # LLM image checks (optional)
        if image_qa:
            image_check = self._check_images_with_llm(output_dir, carousel_data)
            report["checks"]["image_qa"] = image_check
            report["summary"][image_check["status"]] += 1

        # Save report
        report_path = output_dir / "qa_report.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def check_batch(self, output_dirs: List[Union[str, Path]], image_qa: bool = False) -> List[Dict]:
        """Run QA checks on multiple carousels."""
        return [self.check(d, image_qa=image_qa) for d in output_dirs]

    # ── Data Loading ──────────────────────────────────────────────

    def _load_carousel_data(self, output_dir: Path) -> Optional[Dict]:
        carousel_data_path = output_dir / "carousel_data.json"
        if carousel_data_path.exists():
            with open(carousel_data_path) as f:
                return json.load(f)
        return None

    # ── Programmatic Checks ───────────────────────────────────────

    def _check_slide_count_match(self, carousel_data: Optional[Dict], slides_dir: Path) -> Dict:
        """Image count matches slides array length."""
        name = "slide_count_match"
        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        expected = len(carousel_data.get("slides", []))
        pngs = sorted(slides_dir.glob("*.png")) if slides_dir.exists() else []
        actual = len(pngs)

        if actual == expected:
            return {"name": name, "status": "pass", "message": f"{actual} slides match"}
        return {
            "name": name,
            "status": "fail",
            "message": f"Expected {expected} images, found {actual}",
        }

    def _check_structural_labels(self, carousel_data: Optional[Dict]) -> Dict:
        """No structural labels like 'HOOK:', 'TIP SLIDES:' in slide text."""
        name = "structural_labels"
        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        violations = []
        for i, slide in enumerate(carousel_data.get("slides", []), 1):
            text = slide.get("text", "")
            for pattern in STRUCTURAL_LABEL_PATTERNS:
                if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
                    violations.append(f"Slide {i}: matched '{pattern}'")

        if not violations:
            return {"name": name, "status": "pass", "message": "No structural labels found"}
        return {"name": name, "status": "fail", "message": "; ".join(violations)}

    def _check_placeholder_text(self, carousel_data: Optional[Dict]) -> Dict:
        """No placeholder text like '[hook text]', 'explanation here'."""
        name = "placeholder_text"
        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        violations = []
        for i, slide in enumerate(carousel_data.get("slides", []), 1):
            text = slide.get("text", "")
            for pattern in PLACEHOLDER_PATTERNS:
                if re.search(pattern, text, re.IGNORECASE):
                    violations.append(f"Slide {i}: matched '{pattern}'")

        if not violations:
            return {"name": name, "status": "pass", "message": "No placeholders found"}
        return {"name": name, "status": "fail", "message": "; ".join(violations)}

    def _check_image_files_exist(self, carousel_data: Optional[Dict], slides_dir: Path) -> Dict:
        """All expected PNG files exist and are >5KB (not corrupt)."""
        name = "image_files_exist"
        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        expected = len(carousel_data.get("slides", []))
        issues = []

        for i in range(1, expected + 1):
            png_path = slides_dir / f"slide_{i:02d}.png"
            if not png_path.exists():
                issues.append(f"slide_{i:02d}.png missing")
            elif png_path.stat().st_size < 5120:
                issues.append(f"slide_{i:02d}.png too small ({png_path.stat().st_size} bytes)")

        if not issues:
            return {"name": name, "status": "pass", "message": f"All {expected} images present and valid"}
        return {"name": name, "status": "fail", "message": "; ".join(issues)}

    def _check_caption_exists(self, output_dir: Path) -> Dict:
        """caption.txt exists and is non-empty (>20 chars)."""
        name = "caption_exists"
        caption_path = output_dir / "caption.txt"

        if not caption_path.exists():
            return {"name": name, "status": "fail", "message": "caption.txt missing"}

        content = caption_path.read_text().strip()
        if len(content) < 20:
            return {"name": name, "status": "fail", "message": f"Caption too short ({len(content)} chars)"}
        return {"name": name, "status": "pass", "message": f"Caption exists ({len(content)} chars)"}

    def _check_caption_length(self, output_dir: Path) -> Dict:
        """Caption body length check (WARN if outside range)."""
        name = "caption_length"
        min_len, max_len = 200, 500
        if self.qa_config and getattr(self.qa_config, 'caption_length_range', None) is not None:
            min_len, max_len = self.qa_config.caption_length_range

        caption_path = output_dir / "caption.txt"

        if not caption_path.exists():
            return {"name": name, "status": "warn", "message": "caption.txt missing (checked in caption_exists)"}

        content = caption_path.read_text().strip()
        length = len(content)

        if min_len <= length <= max_len:
            return {"name": name, "status": "pass", "message": f"Caption length OK ({length} chars)"}
        return {
            "name": name,
            "status": "warn",
            "message": f"Caption length {length} chars (recommended {min_len}-{max_len})",
        }

    def _check_hook_word_count(self, carousel_data: Optional[Dict]) -> Dict:
        """Hook slide (first slide) word count check."""
        name = "hook_word_count"
        max_words = 20
        if self.qa_config and getattr(self.qa_config, 'hook_max_words', None) is not None:
            max_words = self.qa_config.hook_max_words

        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        slides = carousel_data.get("slides", [])
        if not slides:
            return {"name": name, "status": "fail", "message": "No slides found"}

        hook_text = slides[0].get("text", "")
        word_count = len(hook_text.split())

        if word_count <= max_words:
            return {"name": name, "status": "pass", "message": f"Hook is {word_count} words"}
        return {"name": name, "status": "fail", "message": f"Hook is {word_count} words (max {max_words})"}

    def _check_meta_completeness(self, output_dir: Path) -> Dict:
        """meta.json has all required fields."""
        name = "meta_completeness"
        meta_path = output_dir / "meta.json"

        if not meta_path.exists():
            return {"name": name, "status": "fail", "message": "meta.json missing"}

        with open(meta_path) as f:
            meta = json.load(f)

        required = ["account", "topic", "format", "num_items", "timestamp", "output_dir"]
        missing = [field for field in required if field not in meta]

        if not missing:
            return {"name": name, "status": "pass", "message": "All required fields present"}
        return {"name": name, "status": "fail", "message": f"Missing fields: {', '.join(missing)}"}

    def _check_no_duplicate_slides(self, carousel_data: Optional[Dict]) -> Dict:
        """No two slides have identical text."""
        name = "no_duplicate_slides"
        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        slides = carousel_data.get("slides", [])
        texts = [s.get("text", "").strip().lower() for s in slides]
        seen = {}
        duplicates = []

        for i, text in enumerate(texts, 1):
            if text in seen:
                duplicates.append(f"Slides {seen[text]} and {i}")
            else:
                seen[text] = i

        if not duplicates:
            return {"name": name, "status": "pass", "message": "All slides unique"}
        return {"name": name, "status": "fail", "message": f"Duplicates: {'; '.join(duplicates)}"}

    def _check_image_aspect_ratio(self, slides_dir: Path) -> Dict:
        """Each PNG is 1080x1920."""
        name = "image_aspect_ratio"
        if not slides_dir.exists():
            return {"name": name, "status": "fail", "message": "slides/ directory missing"}

        pngs = sorted(slides_dir.glob("*.png"))
        if not pngs:
            return {"name": name, "status": "fail", "message": "No PNG files found"}

        wrong = []
        for png in pngs:
            try:
                with Image.open(png) as img:
                    w, h = img.size
                    if (w, h) != (1080, 1920):
                        wrong.append(f"{png.name}: {w}x{h}")
            except Exception as e:
                wrong.append(f"{png.name}: error reading ({e})")

        if not wrong:
            return {"name": name, "status": "pass", "message": f"All {len(pngs)} images are 1080x1920"}
        return {"name": name, "status": "fail", "message": "; ".join(wrong)}

    # ── Account-Specific Checks ────────────────────────────────────

    def _check_caption_must_contain(self, output_dir: Path) -> Dict:
        """Caption must contain all required phrases."""
        name = "caption_must_contain"
        caption_path = output_dir / "caption.txt"

        if not caption_path.exists():
            return {"name": name, "status": "fail", "message": "caption.txt missing"}

        content = caption_path.read_text().strip().lower()
        missing = [
            phrase for phrase in self.qa_config.caption_must_contain
            if phrase.lower() not in content
        ]

        if not missing:
            return {"name": name, "status": "pass", "message": "All required phrases found"}
        return {"name": name, "status": "fail", "message": f"Missing required phrases: {', '.join(missing)}"}

    def _check_caption_must_not_contain(self, output_dir: Path) -> Dict:
        """Caption must not contain any forbidden phrases."""
        name = "caption_must_not_contain"
        caption_path = output_dir / "caption.txt"

        if not caption_path.exists():
            return {"name": name, "status": "fail", "message": "caption.txt missing"}

        content = caption_path.read_text().strip().lower()
        found = [
            phrase for phrase in self.qa_config.caption_must_not_contain
            if phrase.lower() in content
        ]

        if not found:
            return {"name": name, "status": "pass", "message": "No forbidden phrases found"}
        return {"name": name, "status": "fail", "message": f"Forbidden phrases found: {', '.join(found)}"}

    def _check_forbidden_slide_words(self, carousel_data: Optional[Dict]) -> Dict:
        """No forbidden words in slide text."""
        name = "forbidden_slide_words"
        if not carousel_data:
            return {"name": name, "status": "fail", "message": "No carousel_data.json found"}

        violations = []
        for i, slide in enumerate(carousel_data.get("slides", []), 1):
            text = slide.get("text", "").lower()
            for word in self.qa_config.forbidden_slide_words:
                if word.lower() in text:
                    violations.append(f"Slide {i}: '{word}'")

        if not violations:
            return {"name": name, "status": "pass", "message": "No forbidden words found"}
        return {"name": name, "status": "fail", "message": f"Forbidden words: {'; '.join(violations)}"}

    # ── LLM Image QA ─────────────────────────────────────────────

    def _check_images_with_llm(self, output_dir: Path, carousel_data: Optional[Dict]) -> Dict:
        """Send all slides to GPT-4o vision for quality review."""
        name = "image_qa"

        if not self.api_key:
            return {"name": name, "status": "warn", "message": "No API key — skipping image QA"}

        slides_dir = output_dir / "slides"
        pngs = sorted(slides_dir.glob("*.png")) if slides_dir.exists() else []
        if not pngs:
            return {"name": name, "status": "fail", "message": "No images to review"}

        # Get topic from carousel data or meta
        topic = ""
        if carousel_data and "meta" in carousel_data:
            topic = carousel_data["meta"].get("topic", "")
        if not topic:
            meta_path = output_dir / "meta.json"
            if meta_path.exists():
                with open(meta_path) as f:
                    topic = json.load(f).get("topic", "")

        # Build QA prompt — use account-specific prompt if available, else generic
        if self.qa_config and getattr(self.qa_config, 'image_qa_prompt', None):
            qa_instructions = self.qa_config.image_qa_prompt
        else:
            qa_instructions = (
                f"Check for:\n"
                f"1. CHILD COUNT: Should be exactly 1 child unless the topic explicitly involves "
                f"multiple children (e.g. 'sibling conflict', 'twins'). Flag if >1 child appears unexpectedly.\n"
                f"2. SCENE MATCH: Does the scene/setting match the topic? Flag mismatches "
                f"(e.g. kitchen scene for a nature walk topic).\n"
                f"3. CLOTHING APPROPRIATE: No inappropriate clothing for the scene "
                f"(e.g. child in overalls in a bathtub).\n"
                f"4. TEXT READABLE: Is any overlay text legible and not cut off?\n"
                f"5. FURNITURE PLACEMENT: No cribs in non-bedroom rooms, no out-of-place furniture."
            )

        # Append learnings from qa_learnings.json
        learnings_block = ""
        if self.learnings_path and self.learnings_path.exists():
            try:
                from core.qa_learnings import load_learnings
                learnings = load_learnings(self.learnings_path.parent)
                if learnings:
                    lines = [f"- \"{l['description']}\" (flagged {l['timestamp'][:10]})" for l in learnings]
                    learnings_block = "\n\nPAST ISSUES (check for these specifically):\n" + "\n".join(lines)
            except Exception:
                pass

        # Build vision message with all slides
        content_parts = [
            {
                "type": "text",
                "text": (
                    f"You are a QA reviewer for Instagram carousel images. "
                    f"The topic of this carousel is: \"{topic}\"\n\n"
                    f"Review these {len(pngs)} slides and {qa_instructions}"
                    f"{learnings_block}\n\n"
                    f"For each issue found, specify which slide number and what the issue is.\n"
                    f"Respond in JSON format:\n"
                    f'{{"issues": [{{"slide": 1, "category": "child_count", "detail": "..."}}], '
                    f'"overall": "pass" or "fail"}}'
                ),
            }
        ]

        for png in pngs:
            img_data = base64.b64encode(png.read_bytes()).decode("utf-8")
            content_parts.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_data}"},
            })

        try:
            from openai import OpenAI

            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=self.api_key)
            response = client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[{"role": "user", "content": content_parts}],
                temperature=0.2,
                max_tokens=1000,
            )

            raw = response.choices[0].message.content.strip()
            # Parse JSON from response (handle markdown code blocks)
            json_match = re.search(r"```json\s*(.*?)\s*```", raw, re.DOTALL)
            json_str = json_match.group(1) if json_match else raw
            result = json.loads(json_str)

            issues = result.get("issues", [])
            overall = result.get("overall", "pass")

            if overall == "pass" and not issues:
                return {"name": name, "status": "pass", "message": "All images passed visual QA", "details": result}

            issue_msgs = [f"Slide {i['slide']}: [{i['category']}] {i['detail']}" for i in issues]
            return {
                "name": name,
                "status": "fail",
                "message": f"{len(issues)} issue(s) found",
                "details": result,
                "issues": issue_msgs,
            }

        except Exception as e:
            logger.warning(f"Image QA failed: {e}")
            return {"name": name, "status": "warn", "message": f"Image QA error: {e}"}
