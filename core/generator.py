"""
Base Content Generator
Framework core for generating carousel content with AI images and viral hooks
"""

from pathlib import Path
from typing import Dict, List, Optional
import json
import logging
import random
import re
import io
import os
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageEnhance
from pilmoji import Pilmoji

from core.config_schema import AccountConfig
from core.image_generator import GeminiImageGenerator, ImageGenerator
from core.utils import SlugGenerator, TopicTracker, determine_content_format
from core.llm_client import LLMClient
from core.semantic_scorer import SemanticHookScorer
from core import prompts

logger = logging.getLogger(__name__)


class BaseContentGenerator:
    """Generate carousel content with AI images and viral hooks (account-agnostic)"""

    # Instagram standard size (9:16 ratio)
    SLIDE_WIDTH = 1080
    SLIDE_HEIGHT = 1920

    # Promo registry — maps promo key to product details for soft-sell injection
    PROMO_REGISTRY = {
        "slumbersongs": {
            "product_name": "SlumberSongs",
            "url": "slumbersongs.com",
            "one_liner": "personalized lullabies with your baby's name",
            "cta_slide_text": "create a lullaby with your baby's name at slumbersongs.com",
            "tip_weave_instruction": (
                "Naturally mention SlumberSongs (personalized lullabies featuring the baby's name) "
                "as ONE of several options or tips — never the main focus. Keep it subtle, like a "
                "recommendation from a friend, not an ad. Example tone: 'some parents love having "
                "a personalized lullaby (slumbersongs.com makes them with your baby's name)'"
            ),
        },
    }

    # Character type guidance for image generation
    CHARACTER_TYPE_GUIDANCE = {
        "personal_brand": {
            "camera_angles": ["eye-level", "slight upward angle", "direct composition"],
            "framing_notes": "confident expressions, authentic moments, natural poses, faces clearly visible",
            "avoid": "avoid staged/posed looks, overly formal portraits"
        },
        "faceless_expert": {
            "camera_angles": ["overhead view", "shot from behind", "over the shoulder", "hands-only closeup"],
            "framing_notes": "show activities without showing faces, focus on actions and environment",
            "avoid": "avoid showing faces, no facial features visible"
        },
        "lifestyle_guide": {
            "camera_angles": ["environmental wide shots", "profile angles", "activity-focused"],
            "framing_notes": "emphasize setting and activity over identity, faces optional",
            "avoid": "avoid close-up portraits"
        }
    }

    def __init__(self, account_config: AccountConfig, scenes_path: Optional[Path] = None, content_templates_path: Optional[Path] = None, account_dir: Optional[Path] = None):
        """
        Initialize content generator

        Args:
            account_config: Validated AccountConfig instance
            scenes_path: Optional path to scenes.json (defaults to account directory)
            content_templates_path: Optional path to content_templates.json
            account_dir: Optional path to account directory (for qa_learnings.json)
        """
        self.config = account_config
        self._account_dir = account_dir

        # API keys (from config or environment)
        openrouter_key = account_config.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        gemini_key = account_config.gemini_api_key or os.getenv("GEMINI_API_KEY")

        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY not found in config or environment")

        # Initialize LLM client
        self.llm = LLMClient(api_key=openrouter_key, model=account_config.claude_model)

        # Initialize Gemini image generator (optional)
        self.gemini = None
        if gemini_key:
            self.gemini = GeminiImageGenerator(model="pro", api_key=gemini_key)
        else:
            logger.warning("GEMINI_API_KEY not found - image generation disabled")

        # Load scenes library
        if scenes_path and scenes_path.exists():
            with open(scenes_path, 'r') as f:
                self.scenes = json.load(f)
        else:
            logger.warning("Scenes library not found - using defaults")
            self.scenes = {"scenes": {}, "aesthetic_styles": {}, "safe_sleep_rules": ""}

        # Load content templates (account-specific prompts and style)
        if content_templates_path and content_templates_path.exists():
            with open(content_templates_path, 'r') as f:
                self.content_templates = json.load(f)
        else:
            logger.warning("Content templates not found - using hardcoded defaults")
            self.content_templates = None

        # Initialize semantic hook scorer with niche-specific references
        custom_refs = None
        if self.content_templates:
            custom_refs = self.content_templates.get("scoring_references")
        self.semantic_scorer = SemanticHookScorer(
            api_key=openrouter_key, use_openrouter=True,
            custom_references=custom_refs
        )

        # Initialize utilities
        self.slug_generator = SlugGenerator()
        self.topic_tracker = TopicTracker(
            account_name=account_config.account_name,
            max_history=account_config.topic_tracker_config.max_history
        )

        # Load performance context for data-driven visual guidance
        self.performance_context = None
        self._current_explore_mode = False
        context_path = Path(account_config.output_config.base_directory).parent / "performance_context.json"
        if not context_path.exists() and scenes_path:
            context_path = scenes_path.parent / "performance_context.json"
        self._context_path = context_path
        self._load_performance_context()

    def _load_performance_context(self):
        """Load performance context, auto-refreshing if stale (>1 day old)."""
        from core.analytics.generator_integration import load_performance_context

        ctx = load_performance_context(self._context_path)
        if ctx:
            # Check staleness
            last_updated = ctx.get("last_updated", "")
            try:
                updated_date = datetime.strptime(last_updated, "%Y-%m-%d").date()
                is_stale = (datetime.now().date() - updated_date).days > 1
            except (ValueError, TypeError):
                is_stale = True

            if is_stale or ctx.get("visual_insights") is None:
                # Auto-refresh if stale OR visual_insights are missing
                self._auto_refresh_context()
                ctx = load_performance_context(self._context_path)

            self.performance_context = ctx
        else:
            logger.debug("No performance context found — visual guidance disabled")

    def _auto_refresh_context(self):
        """Auto-refresh performance context from database."""
        try:
            from core.analytics.db import AnalyticsDB
            from core.analytics.analyzer import AccountAnalyzer

            db_path = Path(__file__).parent.parent / "data" / "analytics.db"
            if not db_path.exists():
                logger.debug("Analytics DB not found — skipping auto-refresh")
                return

            db = AnalyticsDB(db_path)
            analyzer = AccountAnalyzer(db=db)
            analyzer.refresh_context(self.config.account_name, self._context_path)
            logger.info("Auto-refreshed performance context (visual insights were missing)")
            db.close()
        except Exception as e:
            logger.warning(f"Failed to auto-refresh performance context: {e}")

    def generate(
        self,
        topic: str = None,
        content_format: str = None,
        num_items: int = 5,
        use_random: bool = False,
        hook_strategy: str = "viral",
        promo: str = None,
    ) -> Dict:
        """
        Generate complete carousel with AI images and text overlays

        Args:
            topic: Topic to generate about (optional if use_random=True)
            content_format: "habit_list" or "step_guide"
            num_items: Number of tips/steps (5-10)
            use_random: Generate random topic from content pillars
            hook_strategy: "viral" (with scoring) or "template" (simple)

        Returns:
            Dict with output_dir, slides, caption, and metadata
        """
        # Auto-replenish explore topics if running low
        if self.performance_context and self._context_path:
            from core.analytics.generator_integration import replenish_explore_topics
            added = replenish_explore_topics(self._context_path, self.llm)
            if added > 0:
                # Reload context with new topics
                self._load_performance_context()

        # Generate random topic if requested
        if use_random:
            topic = self._generate_random_topic()
            logger.info(f"🎲 Generated random topic: '{topic}'")

        if not topic:
            raise ValueError("Topic is required (or use use_random=True)")

        # Intelligent format selection if not specified
        if content_format is None:
            # Use default from config if available, else determine from topic
            content_format = self.config.carousel_strategy.format or determine_content_format(topic)
            logger.info(f"📋 Auto-selected format: {content_format} (based on topic/config)")

        # Validate format - built-in + any cloned formats from content_templates.json
        builtin_formats = ["habit_list", "step_guide", "scripts", "boring_habits", "how_to"]
        cloned_formats = []
        if self.content_templates and "formats" in self.content_templates:
            for fmt_name, fmt_cfg in self.content_templates["formats"].items():
                if fmt_cfg.get("is_cloned_format") and fmt_name not in builtin_formats:
                    cloned_formats.append(fmt_name)
        valid_formats = builtin_formats + cloned_formats
        if content_format not in valid_formats:
            raise ValueError(f"Invalid format: {content_format}. Valid options: {valid_formats}")

        # Cloned formats use their own slide count from config
        if content_format in cloned_formats:
            fmt_cfg = self.content_templates["formats"][content_format]
            num_items = fmt_cfg.get("default_slide_count", num_items)
        elif not (5 <= num_items <= 10):
            raise ValueError(f"Invalid slide count: {num_items}. Must be 5-10.")

        # Cap built-in formats at 5 items to keep carousels concise
        formats_to_cap = ["boring_habits", "habit_list", "step_guide", "scripts", "how_to"]
        if content_format in formats_to_cap and num_items > 5:
            logger.info(f"⚠️  Capping {content_format} from {num_items} to 5 items (max length)")
            num_items = 5

        logger.info(f"Generating {content_format} carousel about: {topic}")
        logger.info(f"Hook strategy: {hook_strategy}, Items: {num_items}")

        # Check for duplicate topic — reroll if random, warn if user-specified
        is_duplicate, similar_topic = self.topic_tracker.is_topic_too_similar(
            topic,
            similarity_threshold=self.config.topic_tracker_config.similarity_threshold
        )

        if is_duplicate and use_random:
            for _reroll in range(10):
                topic = self._generate_random_topic()
                is_dup, sim = self.topic_tracker.is_topic_too_similar(
                    topic,
                    similarity_threshold=self.config.topic_tracker_config.similarity_threshold
                )
                if not is_dup:
                    logger.info(f"🔄 Rerolled to avoid duplicate → '{topic}'")
                    break
            else:
                logger.warning(f"⚠️  Could not find non-duplicate topic after 10 rerolls")
        elif is_duplicate:
            logger.warning(f"⚠️  Topic similar to recent: '{similar_topic}' — proceeding (user-specified)")

        # 1. Generate content using Claude (with viral hook scoring)
        content = self._generate_content_with_claude(
            content_format=content_format,
            topic=topic,
            num_items=num_items,
            hook_strategy=hook_strategy
        )

        # Verify any Bible references in the generated content
        try:
            from core.bible_verify import verify_all_references
            slide_texts = " ".join(
                s.get("text", "") + " " + s.get("caption", "")
                for s in content.get("slides", [])
            )
            if slide_texts.strip():
                verifications = verify_all_references(slide_texts)
                for v in verifications:
                    if v["valid"]:
                        logger.info(f"✅ Bible ref verified: {v['reference']}")
                    else:
                        logger.warning(f"⚠️  Bible ref FAILED: {v['reference']} — {v.get('error', 'unknown')}")
        except Exception as e:
            logger.debug(f"Bible verification skipped: {e}")

        # Apply promo overlay if requested
        if promo:
            content = self._apply_promo(content, promo, topic)

        # 2. Generate contextual image prompts using Claude
        image_prompts = self._get_image_prompts(
            content_format=content_format,
            content=content
        )

        # 3. Generate images (Pexels for proven formats, Gemini for legacy + cloned)
        pexels_formats = ["scripts", "boring_habits", "how_to"]
        is_cloned = content_format in cloned_formats
        use_pexels = content_format in pexels_formats and not is_cloned
        num_slides = len(content["slides"])

        if use_pexels:
            logger.info(f"Fetching {num_slides} Pexels stock photos for {content_format} format...")
            image_gen = ImageGenerator(
                mode="pexels",
                pexels_key=os.getenv("PEXELS_API_KEY")
            )
            image_bytes_list = image_gen.generate_for_carousel(
                topic=topic,
                num_slides=num_slides,
                format_name=content_format
            )

            if not image_bytes_list or len(image_bytes_list) < num_slides:
                logger.error(f"Failed to fetch enough Pexels photos ({len(image_bytes_list)}/{num_slides})")
                return {"error": "Failed to fetch Pexels photos"}

            images = []
            for img_bytes in image_bytes_list:
                img = Image.open(io.BytesIO(img_bytes))
                img = self._resize_to_instagram(img)
                images.append(img)

        else:
            # Gemini generation for existing + cloned formats
            # For cloned formats, use per-slide image prompts from template config
            if is_cloned:
                fmt_cfg = self.content_templates["formats"][content_format]
                template_image_prompts = fmt_cfg.get("image_prompts", [])
                if template_image_prompts:
                    image_prompts = []
                    for ip in template_image_prompts:
                        tmpl = ip.get("template", "")
                        image_prompts.append(tmpl.replace("{topic}", topic))
                    # Pad or trim to match slide count
                    while len(image_prompts) < num_slides:
                        image_prompts.append(f"Scene related to {topic}, clean composition")
                    image_prompts = image_prompts[:num_slides]

            logger.info("Generating images with Gemini (9:16 aspect ratio)...")
            images = []
            reference_image_bytes = None

            for i, prompt in enumerate(image_prompts, 1):
                logger.info(f"Generating slide {i}/{len(image_prompts)}...")
                # Sanitize prompt before sending to Gemini (strip text refs, fix truncation)
                prompt = self._sanitize_image_prompt(prompt)
                full_prompt = f"{prompt}, vertical portrait format, 9:16 aspect ratio"

                if i > 1:
                    full_prompt += ", IMPORTANT: maintain the same visual style, color palette, lighting, and artistic approach as the reference image. Do NOT create picture-in-picture, inset images, or small photos within the scene. ONE single continuous full-frame scene only"

                # CRITICAL: Enforce safe sleep guidelines for any baby/crib/sleep imagery
                sleep_keywords = ["baby", "crib", "sleep", "nursery", "nap", "bedtime"]
                if any(keyword in full_prompt.lower() for keyword in sleep_keywords):
                    safe_sleep = self.scenes.get("safe_sleep_rules", "")
                    if safe_sleep:
                        full_prompt += f", {safe_sleep}"
                        logger.debug("✓ Safe sleep guidelines enforced")

                image_bytes = self.gemini.generate_image(
                    full_prompt,
                    reference_image=reference_image_bytes if i > 1 else None
                )

                if image_bytes:
                    if i == 1:
                        reference_image_bytes = image_bytes
                        logger.info("Saved first image as reference for visual consistency")

                    img = Image.open(io.BytesIO(image_bytes))
                    img = self._resize_to_instagram(img)
                    images.append(img)
                else:
                    logger.error(f"Failed to generate image for slide {i}")
                    return {"error": f"Failed to generate image for slide {i}"}

        # 4. Create output directory
        output_dir = self._create_output_dir(topic)
        slides_dir = output_dir / "slides"
        slides_dir.mkdir(parents=True, exist_ok=True)

        # 5. Add text overlays and save slides
        # Check if account uses pill-style text (TikTok native)
        text_style = "stroke"  # default
        if self.content_templates and "style_guidelines" in self.content_templates:
            text_style = self.content_templates["style_guidelines"].get("text_style", "stroke")

        logger.info(f"Adding text overlays ({text_style} style)...")
        num_slides = len(content["slides"])

        for i, (img, slide_content) in enumerate(zip(images, content["slides"])):
            # First and last slides are hooks/CTAs (centered)
            is_hook = (i == 0) or (i == num_slides - 1)

            # Add text overlay using configured style
            if text_style == "pill":
                img_with_text = self._add_text_overlay_pills(
                    img,
                    slide_content["text"],
                    is_hook=is_hook
                )
            else:
                img_with_text = self._add_text_overlay(
                    img,
                    slide_content["text"],
                    is_hook=is_hook
                )

            # Save slide
            slide_path = slides_dir / f"slide_{i+1:02d}.png"
            img_with_text.save(slide_path, "PNG")
            logger.info(f"Saved: {slide_path.name}")

        # 6. Generate and save caption
        # For cloned formats, use the caption from the format's LLM response (has correct CTA strategy)
        if is_cloned and content.get("caption"):
            caption_text = content["caption"]
            hashtags = self._build_topic_hashtags(topic)
            caption = f"{caption_text}\n\n{hashtags}"
        else:
            caption = self._generate_caption(content, promo=promo)
        caption_path = output_dir / "caption.txt"
        caption_path.write_text(caption)

        # 7. Save metadata
        import hashlib
        hook_text = content["slides"][0].get("text", "") if content.get("slides") else ""
        content_id = hashlib.sha256(
            f"{topic}|{content_format}|{hook_text}".encode()
        ).hexdigest()[:12]
        meta = {
            "account": self.config.account_name,
            "topic": topic,
            "format": content_format,
            "content_id": content_id,
            "hook_text": hook_text,
            "caption": caption,
            "num_items": num_items,
            "hook_strategy": hook_strategy,
            "timestamp": datetime.now().isoformat(),
            "output_dir": str(output_dir)
        }
        meta_path = output_dir / "meta.json"
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)

        # 8. Save full carousel data
        carousel_data = {
            "slides": content["slides"],
            "image_prompts": image_prompts,
            "caption": caption,
            "meta": meta
        }
        carousel_data_path = output_dir / "carousel_data.json"
        with open(carousel_data_path, 'w') as f:
            json.dump(carousel_data, f, indent=2)

        # Track topic
        self.topic_tracker.add_topic(topic, str(output_dir))

        # 9. Run programmatic QA checks
        from core.qa_checker import CarouselQAChecker
        learnings_path = (self._account_dir / "qa_learnings.json") if self._account_dir else None
        qa_checker = CarouselQAChecker(
            qa_config=self.config.qa_config,
            learnings_path=learnings_path,
        )
        qa_report = qa_checker.check(output_dir, image_qa=False)

        # Log QA warnings
        fail_count = qa_report["summary"]["fail"]
        warn_count = qa_report["summary"]["warn"]
        if fail_count:
            logger.warning(f"⚠️  QA: {fail_count} check(s) FAILED")
            for name, result in qa_report["checks"].items():
                if result["status"] == "fail":
                    logger.warning(f"   ❌ {name}: {result['message']}")
        if warn_count:
            for name, result in qa_report["checks"].items():
                if result["status"] == "warn":
                    logger.info(f"   ⚠️  {name}: {result['message']}")

        logger.info(f"✅ Carousel created: {output_dir}")
        logger.info(f"   Slides: {num_slides}")
        logger.info(f"   Caption: {caption_path}")
        logger.info(f"   QA: {qa_report['summary']['pass']} pass, {fail_count} fail, {warn_count} warn")

        return {
            "output_dir": str(output_dir),
            "format": content_format,
            "num_slides": num_slides,
            "slides": [str(slides_dir / f"slide_{i:02d}.png") for i in range(1, num_slides + 1)],
            "caption": caption,
            "meta": meta,
            "qa_report": qa_report
        }

    def _generate_content_with_claude(
        self,
        content_format: str,
        topic: str,
        num_items: int,
        hook_strategy: str = "viral"
    ) -> Dict:
        """
        Generate content using Claude API with viral hook scoring

        Args:
            content_format: "habit_list" or "step_guide"
            topic: Topic to generate about
            num_items: Number of tips/steps
            hook_strategy: "viral" (with scoring) or "template" (simple)

        Returns:
            Dict with slides content
        """
        # Quality settings from config
        min_hook_score = self.config.quality_overrides.min_hook_score
        max_words = self.config.quality_overrides.max_words_per_slide

        # Extract niche from templates or use defaults
        niche = "general content"

        if self.content_templates:
            # Try to extract niche from brand identity value_proposition or personality
            value_prop = self.config.brand_identity.value_proposition or ""
            niche = value_prop if value_prop else self.config.brand_identity.personality

        # Extract hook examples and formulas from account config
        hook_examples = None
        if self.content_templates:
            hook_examples = self.content_templates.get("hook_examples")
        hook_formulas = getattr(self.config, 'hook_formulas', None)

        # Retry hooks for quality - cap proven formats at 3 to save API calls
        proven_formats = ["scripts", "boring_habits", "how_to"]
        if hook_strategy != "viral":
            max_attempts = 1
        elif content_format in proven_formats:
            max_attempts = 3
        else:
            max_attempts = 10
        score_feedback = None

        for attempt in range(max_attempts):
            # Build prompt based on format
            if content_format == "habit_list":
                prompt = prompts.build_habit_list_prompt(
                    topic, num_items, hook_strategy, max_words, score_feedback,
                    niche=niche, content_templates=self.content_templates,
                    hook_examples=hook_examples, hook_formulas=hook_formulas,
                )
            elif content_format == "step_guide":
                prompt = prompts.build_step_guide_prompt(
                    topic, num_items, hook_strategy, max_words, score_feedback,
                    niche=niche, content_templates=self.content_templates,
                    hook_examples=hook_examples, hook_formulas=hook_formulas,
                )
            elif content_format == "scripts":
                prompt = prompts.build_scripts_prompt(
                    topic, num_categories=num_items,
                    max_words=max_words, niche=niche,
                    score_feedback=score_feedback,
                    hook_examples=hook_examples, hook_formulas=hook_formulas,
                    content_templates=self.content_templates,
                )
            elif content_format == "boring_habits":
                prompt = prompts.build_boring_habits_prompt(
                    topic, num_habits=num_items,
                    max_words=max_words, niche=niche,
                    score_feedback=score_feedback,
                    hook_examples=hook_examples, hook_formulas=hook_formulas,
                    content_templates=self.content_templates,
                )
            elif content_format == "how_to":
                prompt = prompts.build_how_to_prompt(
                    topic, num_steps=num_items,
                    max_words=max_words, niche=niche,
                    score_feedback=score_feedback,
                    hook_examples=hook_examples, hook_formulas=hook_formulas,
                    content_templates=self.content_templates,
                )
            elif self.content_templates and content_format in self.content_templates.get("formats", {}):
                # Blueprint-derived (cloned) format
                fmt_cfg = self.content_templates["formats"][content_format]
                if fmt_cfg.get("is_cloned_format"):
                    prompt = prompts.build_blueprint_format_prompt(
                        topic=topic,
                        format_config=fmt_cfg,
                        brand_voice=niche,
                        niche=niche,
                    )
                else:
                    raise ValueError(f"Unsupported format: {content_format}")
            else:
                raise ValueError(f"Unsupported format: {content_format}")

            # Build system prompt from brand identity
            system_prompt = prompts.build_system_prompt(
                self.config.brand_identity.model_dump(),
                content_templates=self.content_templates
            )

            # Call Claude API via LLM client
            content_text = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            parsed_content = self._parse_claude_response(content_text, content_format, topic, num_items)
            slides = parsed_content["slides"]

            # Score hook if using viral strategy (all formats go through scoring)
            if hook_strategy == "viral":
                hook_text = slides[0]["text"]
                score_result = self._score_hook(hook_text, min_hook_score, max_words)

                if score_result["passed"]:
                    logger.info(f"✅ Hook scored {score_result['total']}/20 (Grade: {score_result['grade']})")
                    for feedback in score_result.get("feedback", []):
                        logger.info(f"   Note: {feedback}")
                    break
                else:
                    logger.warning(f"❌ Hook scored {score_result['total']}/20 (need {min_hook_score}+), attempt {attempt + 1}/{max_attempts}")
                    for feedback in score_result.get("feedback", []):
                        logger.warning(f"   {feedback}")

                    if attempt < max_attempts - 1:
                        score_feedback = score_result
                        score_feedback["min_score"] = min_hook_score
                        continue
                    else:
                        logger.warning(f"⚠️  Using best attempt after {max_attempts} tries")
            else:
                # Template strategy - no hook scoring needed
                break

        return {
            "format": content_format,
            "topic": topic,
            "slides": slides,
            "caption": parsed_content.get("caption"),  # Include caption if provided
            "pexels_query": parsed_content.get("pexels_query")
        }


    def _parse_claude_response(
        self,
        content_text: str,
        content_format: str,
        topic: str,
        num_items: int
    ) -> Dict:
        """
        Parse Claude's response into slides

        Returns:
            Dict with 'slides' array and optional 'caption', 'pexels_query' fields
        """
        # Try JSON format first (for proven formats + cloned formats)
        # Check if this is a cloned format
        is_cloned_fmt = False
        if self.content_templates and "formats" in self.content_templates:
            fmt = self.content_templates["formats"].get(content_format, {})
            is_cloned_fmt = fmt.get("is_cloned_format", False)

        # Try JSON parsing for all formats (LLM may return JSON even when not expected)
        try:
            json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                if "slides" in data and isinstance(data["slides"], list) and len(data["slides"]) >= 3:
                    # Convert to expected format
                    slides = []
                    hook_added = False

                    # Find hook text from multiple sources
                    hook_text = data.get("hook")  # Top-level hook field
                    if not hook_text:
                        # Check if any slide has type "hook"
                        for sd in data.get("slides", []):
                            if sd.get("type", "").lower() == "hook":
                                hook_text = sd.get("text", "")
                                break

                    for slide_data in data.get("slides", []):
                        text = slide_data.get("text", "")
                        slide_type = slide_data.get("type", "")
                        # Ensure first slide is the hook, not a tip
                        if not hook_added:
                            if text.lower().startswith(("tip ", "step ")):
                                if hook_text:
                                    # Use recovered hook text
                                    slides.append({"text": hook_text})
                                else:
                                    # Generate fallback hook from topic
                                    fallback_hook = f"{num_items} tips about {topic} that actually work"
                                    logger.warning(f"No hook found in JSON, using fallback: {fallback_hook}")
                                    slides.append({"text": fallback_hook})
                            else:
                                slides.append({"text": text})
                            hook_added = True
                        else:
                            # Skip duplicate of hook if it appears as a later slide too
                            if slide_type.lower() == "hook":
                                continue
                            slides.append({"text": text})

                    # Validate content isn't placeholder text
                    placeholder_patterns = ["explanation here", "[hook text]", "[phrase]", "[situation]", "[action phrase]"]
                    has_placeholder = any(
                        any(p in slide.get("text", "").lower() for p in placeholder_patterns)
                        for slide in slides
                    )
                    if has_placeholder:
                        logger.warning(f"Detected placeholder text in {content_format} JSON response, falling back to text parsing")
                    else:
                        return {
                            "slides": slides,
                            "caption": data.get("caption"),
                            "pexels_query": data.get("pexels_query")
                        }
                elif content_format not in ["scripts", "boring_habits", "how_to"] and not is_cloned_fmt:
                    logger.info(f"JSON found but insufficient slides for {content_format}, falling back to text parsing")
                else:
                    logger.warning(f"No valid slides array in JSON for {content_format}, falling back to text parsing")
        except json.JSONDecodeError as e:
            if content_format in ["scripts", "boring_habits", "how_to"] or is_cloned_fmt:
                logger.warning(f"Failed to parse JSON response for {content_format}: {e}, falling back to text parsing")

        # Legacy text parsing (for habit_list, step_guide)
        slides = []

        # Clean up response - remove meta-text like "# SLIDE 1", "**SLIDE 1:**", "---", etc
        content_text = re.sub(r'\*\*SLIDE\s+\d+\s*(\(.*?\))?\s*\*\*:?\s*', '', content_text, flags=re.IGNORECASE)  # **SLIDE X (Hook):**
        content_text = re.sub(r'#?\s*SLIDE\s+\d+:?\s*(\(.*?\))?\s*', '', content_text, flags=re.IGNORECASE)  # # SLIDE X:
        content_text = content_text.replace('---', '')  # Remove separator lines
        content_text = re.sub(r'^#\s+.*$', '', content_text, flags=re.MULTILINE)  # Remove any line starting with #
        content_text = re.sub(r'^\*\*:\*\*\s*$', '', content_text, flags=re.MULTILINE)  # Remove leftover **:**
        # Remove structural labels that LLM sometimes outputs as slide content
        content_text = re.sub(r'^\s*HOOK:\s*$', '', content_text, flags=re.MULTILINE | re.IGNORECASE)
        content_text = re.sub(r'^\s*TIP SLIDES?:\s*$', '', content_text, flags=re.MULTILINE | re.IGNORECASE)
        content_text = re.sub(r'^\s*CTA SLIDE?:\s*$', '', content_text, flags=re.MULTILINE | re.IGNORECASE)
        content_text = re.sub(r'^\s*CAPTION:\s*$', '', content_text, flags=re.MULTILINE | re.IGNORECASE)
        content_text = re.sub(r'^\s*FINAL SLIDE:\s*$', '', content_text, flags=re.MULTILINE | re.IGNORECASE)

        lines = content_text.strip().split('\n')

        # First non-empty line is the hook (skip numbered tips and CTA)
        hook_text = None
        for line in lines:
            line = line.strip()
            # Skip empty, tip/step/habit/script lines, CTA lines, and all-caps titles
            if line and not line.lower().startswith(('tip ', 'step ', 'habit ', 'script ')) and not line.lower().startswith('save this'):
                # Skip all-caps titles (e.g., "HOW TO HANDLE PICKY EATING")
                if line.isupper():
                    continue
                hook_text = line
                break

        if not hook_text:
            # Fallback hook based on format (grammatically safe)
            if content_format == "habit_list":
                hook_text = f"{num_items} tips about {topic} that actually work"
            elif content_format == "boring_habits":
                hook_text = f"{num_items} simple habits for {topic} that changed everything"
            elif content_format == "scripts":
                hook_text = f"what to say about {topic}"
            elif content_format == "how_to":
                hook_text = f"how to handle {topic}"
            else:
                hook_text = f"the {topic} guide that actually works"

        # Clean hook text
        hook_text = self._clean_text(hook_text)
        slides.append({"text": hook_text})

        # Extract tips/steps
        # Parse based on "tip N:" or "step N:" or dynamic "label:" patterns
        _CTA_MARKERS = ['save this', 'save for later', 'send this', 'try one tonight',
                        'which one are you', 'comment which', 'drop it below', 'come back to it']

        def _is_cta(text: str) -> bool:
            """Check if a line is a CTA slide"""
            t = text.lower()
            return any(m in t for m in _CTA_MARKERS)

        def _is_category_start(text: str) -> bool:
            """Check if a line starts a new tip/step/habit/script/category"""
            t = text.lower()
            if t.startswith(('tip ', 'step ', 'habit ', 'script ')):
                return True
            if ':' in text:
                before = text.split(':')[0].strip()
                if 0 < len(before.split()) <= 3 and len(before) <= 30:
                    return True
            return False

        current_tip = None
        tip_count = 0

        skip_until_idx = 0
        for i, line in enumerate(lines):
            if i < skip_until_idx:
                continue

            line = line.strip()

            # Skip empty lines, separators, meta-text
            if not line or line in ['---', '****', '***', '**', '*']:
                continue
            if line.lower().startswith('slide') or line.startswith('#'):
                continue
            if line == hook_text:  # Skip the hook we already added
                skip_until_idx = i + 1
                continue
            if _is_cta(line):  # Stop at CTA
                break

            # Detect if this line starts a tip/step/habit/script/category
            is_tip_start = _is_category_start(line)

            if not is_tip_start:
                continue  # Skip lines that don't start tips

            # This line starts a tip - collect it + following lines
            tip_lines = [line]
            j = i + 1

            # Gather continuation lines until next tip or CTA
            while j < len(lines):
                continuation_line = lines[j].strip()

                # Empty line - check if followed by new tip
                if not continuation_line:
                    # Look ahead to next non-empty line
                    k = j + 1
                    while k < len(lines) and not lines[k].strip():
                        k += 1

                    if k < len(lines):
                        peek_line = lines[k].strip()
                        # Check if peeked line starts a new tip
                        peek_is_tip = (
                            _is_category_start(peek_line) or
                            _is_cta(peek_line)
                        )
                        if peek_is_tip:
                            # Next real content is a new tip, stop here
                            break

                    # Empty line but not followed by tip, skip it
                    j += 1
                    continue

                # Stop at CTA
                if _is_cta(continuation_line):
                    break

                # Stop at meta-text
                if continuation_line.lower().startswith('slide') or continuation_line.startswith('#'):
                    break

                # Check if this line itself starts a new tip
                if _is_category_start(continuation_line):
                    # This line starts next tip, stop before it
                    break

                # This is a continuation line, add it
                tip_lines.append(continuation_line)
                j += 1

            # Combine lines into one tip
            current_tip = '\n\n'.join(tip_lines)
            current_tip = self._clean_text(current_tip)

            # Only add if non-empty and not a duplicate of hook
            if current_tip and current_tip != hook_text:
                slides.append({"text": current_tip})
                tip_count += 1
                skip_until_idx = j

                # Stop if we have enough tips
                if tip_count >= num_items:
                    break

        # Look for CTA slide
        cta_found = False
        for line in lines:
            if _is_cta(line):
                cta_text = self._clean_text(line)
                if cta_text:
                    slides.append({"text": cta_text})
                    cta_found = True
                    break

        # Ensure correct number of slides (hook + tips + CTA)
        target_slides = num_items + 2

        while len(slides) < target_slides:
            if len(slides) < target_slides - 1:
                slides.append({"text": f"tip {len(slides)}\n\nexplanation here"})
            else:
                from core.prompts import _random_cta
                slides.append({"text": _random_cta(self.content_templates)})

        return {
            "slides": slides[:target_slides],
            "caption": None,  # Legacy formats use generated captions
            "pexels_query": None
        }

    def _score_hook(self, hook_text: str, min_score: int = 16, max_words: int = 20) -> Dict:
        """
        Score hooks using semantic similarity (max 20 points)

        Uses embeddings to evaluate hook quality across 4 dimensions:
        1. Curiosity gap (1-5): Promises insight without revealing
        2. Actionability (1-5): Clear action/transformation
        3. Specificity (1-5): Tangible details
        4. Scroll stop (1-5): Pattern interrupt

        Args:
            hook_text: Hook text to score
            min_score: Minimum passing score
            max_words: Maximum word count

        Returns:
            Dict with total, scores, grade, passed, and feedback
        """
        # FORMAT COMPLIANCE (must pass before scoring)
        word_count = len(hook_text.split())
        if word_count > max_words:
            return {
                "total": 0,
                "scores": {},
                "grade": "F",
                "passed": False,
                "feedback": [f"FAILED: Hook exceeds {max_words} word limit ({word_count} words)"]
            }

        # Use semantic scorer for quality evaluation
        try:
            total, feedback = self.semantic_scorer.score_hook(hook_text)
            dimension_scores = self.semantic_scorer.get_dimension_breakdown(hook_text)
        except Exception as e:
            logger.warning(f"⚠️  Semantic scoring failed ({e}), auto-passing hook")
            return {
                "total": min_score,
                "scores": {},
                "grade": "B",
                "passed": True,
                "feedback": [f"Scoring unavailable — auto-passed"]
            }

        passed = total >= min_score

        # Determine grade
        if total >= 18:
            grade = "A"
        elif total >= 16:
            grade = "B"
        elif total >= 14:
            grade = "C"
        else:
            grade = "F"

        return {
            "total": total,
            "scores": dimension_scores,
            "grade": grade,
            "passed": passed,
            "feedback": feedback
        }

    def _clean_text(self, text: str) -> str:
        """Clean up text by removing artifacts"""
        # Remove meta-text like "**SLIDE X (CTA)**:"
        text = re.sub(r'\*\*SLIDE\s+\d+\s*\([^)]+\)\s*\*\*:?', '', text, flags=re.IGNORECASE)

        # Remove quotes
        text = text.strip('"\'')
        text = text.replace('\\"', '').replace("\\'", '')

        # Remove markdown formatting symbols (# for headings, ** for bold)
        text = re.sub(r'^#+\s*', '', text)  # Remove leading # symbols
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Remove bold ** markers

        # Remove artifacts
        text = text.replace('\n\n---\n\n****', '')
        text = text.replace('\n\n---', '')
        text = text.replace('\n\n****', '')
        text = text.replace('****', '').replace('***', '')

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        # Rejoin with proper spacing
        result = []
        for i, line in enumerate(lines):
            if i == 0:
                result.append(line)
            else:
                # Regular line - add spacing
                if result:
                    result.append('\n\n' + line)
                else:
                    result.append(line)

        return ''.join(result).strip()

    def _get_image_prompts(
        self,
        content_format: str,
        content: Dict
    ) -> List[str]:
        """Generate contextual image prompts using Claude"""
        prompts = []

        # Choose aesthetic style (use override if set, then default_style, then fallback)
        available_styles = list(self.scenes.get("aesthetic_styles", {}).keys())
        if hasattr(self, '_style_override') and self._style_override:
            style = self._style_override
        elif self.scenes.get("default_style") and self.scenes["default_style"] in available_styles:
            style = self.scenes["default_style"]
        elif "iphone_photo_v2" in available_styles:
            style = random.choice(["iphone_photo_v2", "painterly_v2"])
        else:
            style = random.choice(["painterly", "iphone_photo"])
        base_aesthetic = self.scenes["aesthetic_styles"][style]
        logger.info(f"🎨 Using {style} aesthetic style")

        # Decide exploit vs explore mode for visual guidance
        if self.performance_context and self.performance_context.get("visual_insights"):
            from core.analytics.generator_integration import should_explore
            self._current_explore_mode = should_explore(self.performance_context)
            mode_label = "EXPLORE" if self._current_explore_mode else "EXPLOIT"
            logger.info(f"📊 Visual guidance mode: {mode_label}")

        # Slide 1: Generate contextual hook image (not brand anchor)
        topic = content.get("topic", "routine")
        hook_text = content["slides"][0]["text"]
        hook_prompt = self._generate_hook_scene_prompt(hook_text, topic, base_aesthetic)
        prompts.append(hook_prompt)

        # Slides 2-N: Generate contextual prompts
        slides_text = [slide["text"] for slide in content["slides"][1:]]

        contextual_prompts = self._generate_contextual_prompts(
            topic=topic,
            slides_text=slides_text,
            base_aesthetic=base_aesthetic
        )

        prompts.extend(contextual_prompts)

        return prompts

    def _generate_hook_scene_prompt(self, hook_text: str, topic: str, base_aesthetic: str) -> str:
        """Generate contextual scene description for hook image"""
        try:
            # Get niche-specific context
            value_prop = self.config.brand_identity.value_proposition or "expert content"

            # Build visual direction block from performance data — use hook_recipe for hook slides
            visual_direction = ""
            if self.performance_context and self.performance_context.get("visual_insights"):
                from core.analytics.generator_integration import (
                    get_hook_visual_guidance, get_explore_visual_guidance
                )
                if self._current_explore_mode:
                    guidance = get_explore_visual_guidance(self.performance_context)
                    if guidance:
                        visual_direction = f"\n\nVISUAL DIRECTION (testing new approach): {guidance}"
                else:
                    guidance = get_hook_visual_guidance(self.performance_context)
                    if guidance:
                        visual_direction = f"\n\nVISUAL DIRECTION (based on performance data): {guidance}"

            # Append learnings from qa_learnings.json
            learnings_block = ""
            if self._account_dir:
                try:
                    from core.qa_learnings import load_learnings
                    learnings = load_learnings(self._account_dir)
                    if learnings:
                        lines = [f"- {l['description']}" for l in learnings]
                        learnings_block = "\n\nPAST ISSUES TO AVOID:\n" + "\n".join(lines)
                except Exception:
                    pass

            system_prompt = f"""Generate a scene description for a social media hook slide about {value_prop}.

TARGET AESTHETIC (your scene MUST match this style):
{base_aesthetic}

Requirements:
- Scene MUST be set in the same environment/location as the topic
- NEVER default to a nursery, crib, or sleeping baby unless the topic is specifically about sleep or bedtime
- Cribs/bassinets ONLY in bedrooms or nurseries — NEVER in kitchens, living rooms, or other rooms
- Only ONE baby/child in the scene — NEVER two children unless the topic is specifically about siblings
- Children must be seated in chairs, high chairs, or on laps — NEVER sitting on tables or counters
- Use interesting composition and angles to create visual interest
- NO text, writing, labels, clocks, signs, or readable elements in the scene
- NO books with visible pages, no screens with visible text, no written notes
- Keep the scene warm, bright, and inviting — match the target aesthetic above
- Write a COMPLETE scene description (finish your sentences){visual_direction}{learnings_block}

Return ONLY the scene description (2-4 sentences), no additional commentary."""

            user_prompt = f"""Topic: {topic}
Hook text: {hook_text}

Generate a scene that matches this topic and the target aesthetic. Keep it simple, warm, and authentic."""

            # Call Claude API via LLM client
            scene_description = self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=350
            )
            full_prompt = f"{base_aesthetic}, {scene_description}"
            logger.info(f"Generated contextual hook scene for '{topic}'")
            return full_prompt

        except Exception as e:
            logger.error(f"Failed to generate hook scene prompt: {e}")
            logger.info("Falling back to topic-aware generic prompt")
            # Fallback to topic-aware prompt instead of baby-in-crib brand anchor
            return f"{base_aesthetic}, warm authentic parenting moment related to {topic}"

    def _generate_contextual_prompts(
        self,
        topic: str,
        slides_text: List[str],
        base_aesthetic: str
    ) -> List[str]:
        """Generate contextual image prompts using Claude"""
        try:
            # Build slides summary
            slides_summary = "\n".join([
                f"Slide {i+2}: {text[:100]}..." if len(text) > 100 else f"Slide {i+2}: {text}"
                for i, text in enumerate(slides_text)
            ])

            # Derive niche/character from brand identity
            character_type = self.config.brand_identity.character_type or "faceless_expert"
            value_prop = self.config.brand_identity.value_proposition or "expert content"

            # Get visual guidance for character type
            guidance = self.CHARACTER_TYPE_GUIDANCE.get(character_type, None)

            if guidance:
                character_section = f"""CHARACTER FRAMING:
- Type: {character_type}
- Camera angles: {", ".join(guidance["camera_angles"])}
- Framing: {guidance["framing_notes"]}
- Avoid: {guidance["avoid"]}"""
            else:
                # Fallback for unknown character types (backward compatibility)
                character_section = f"- Character type: {character_type}"

            # Build visual direction block from performance data
            visual_direction = ""
            if self.performance_context and self.performance_context.get("visual_insights"):
                from core.analytics.generator_integration import (
                    get_visual_guidance, get_explore_visual_guidance
                )
                if self._current_explore_mode:
                    guidance = get_explore_visual_guidance(self.performance_context)
                    if guidance:
                        visual_direction = f"\n\nVISUAL DIRECTION (testing new approach): {guidance}"
                else:
                    guidance = get_visual_guidance(self.performance_context)
                    if guidance:
                        visual_direction = f"\n\nVISUAL DIRECTION (based on performance data): {guidance}"

            # Append learnings from qa_learnings.json
            learnings_block = ""
            if self._account_dir:
                try:
                    from core.qa_learnings import load_learnings
                    learnings = load_learnings(self._account_dir)
                    if learnings:
                        lines = [f"- {l['description']}" for l in learnings]
                        learnings_block = "\n\nPAST ISSUES TO AVOID:\n" + "\n".join(lines)
                except Exception:
                    pass

            # Add child safety rules only for parenting accounts
            child_safety_rules = ""
            if self.scenes and self.scenes.get("safe_sleep_rules"):
                child_safety_rules = """
- Only ONE baby/child per scene (never show two different babies)
- Children must be seated in chairs, high chairs, or on laps — NEVER sitting on tables or counters
- Cribs should ONLY appear in a child's bedroom or nursery — NEVER in living rooms, kitchens, or other rooms"""

            prompt = f"""Generate image prompts for a carousel about "{topic}" for {value_prop}.

For each slide, create a visual scene that DIRECTLY MATCHES the content.

SLIDES CONTENT:
{slides_summary}

REQUIREMENTS:
- Each scene must visually represent what the slide is about
{character_section}
- Keep scenes authentic, realistic, and on-brand
- Focus on the SPECIFIC action/concept in each slide
- The LAST slide is a CTA (save/share/comment) - make it a warm closing scene related to "{topic}" that fits the brand: {value_prop}. Do NOT reuse characters or scenes from earlier slides — create a distinct warm closing moment.
- NO text, writing, labels, clocks, signs, book pages, or readable elements in any scene{visual_direction}{learnings_block}

CRITICAL - VISUAL CONSISTENCY:
All scenes must maintain CONSISTENT visual style:
- Same lighting quality (golden/warm vs cool/bright)
- Same time of day throughout
- Same color palette and saturation
- Same artistic approach
- Same mood and atmosphere

CRITICAL - EVERY SLIDE MUST HAVE A UNIQUE SCENE:
- Each slide MUST depict a DIFFERENT setting, angle, subject, or moment
- NEVER reuse the same scene description or composition across slides
- Vary: location (church interior, outdoor, home, car, park), camera angle (close-up, wide shot, overhead, profile), subject (hands, face, full body, objects), activity (praying, singing, reading, walking, embracing)
- If the topic is abstract, find CONCRETE visual metaphors that differ per slide
- You MUST return exactly {len(slides_text)} unique scene descriptions

CRITICAL - COMPOSITION RULES:
- ONE clear scene per image with a single focal point
- NO collages, split screens, or composite images
- NEVER include a small inset/picture-in-picture image within the scene — each image must be ONE continuous scene filling the entire frame
- Keep scenes simple and realistic — do not combine objects from different rooms
- Match the SETTING to the topic — every scene should visually relate to the topic
- NEVER describe modern objects (phones, tablets, screens, electronics, cars) — all objects must fit the art style's time period
- NEVER describe text, writing, signs, labels, scrolls with words, or any readable content in scenes — the image generator will render gibberish text{child_safety_rules}

BASE AESTHETIC (always include at end):
{base_aesthetic}

Return ONLY a JSON array of {len(slides_text)} image prompts.
Format: ["Scene description 1", "Scene description 2", ...]

Generate {len(slides_text)} contextual scene descriptions:"""

            # Call Claude API via LLM client
            response_text = self.llm.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are an expert at creating visual scene descriptions for {value_prop}."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=3000
            )

            # Extract JSON array
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                scene_prompts = json.loads(json_match.group())
                # Append aesthetic only if Claude didn't already include it
                aesthetic_snippet = base_aesthetic[:40]
                full_prompts = []
                for p in scene_prompts:
                    if aesthetic_snippet in p:
                        full_prompts.append(p)  # Already has aesthetic
                    else:
                        full_prompts.append(f"{base_aesthetic}, {p}")

                # If Claude returned fewer prompts than needed, pad with unique fallbacks
                if len(full_prompts) < len(slides_text):
                    logger.warning(f"Got {len(full_prompts)} prompts but need {len(slides_text)}, padding with unique scenes")
                    used_scenes = set()
                    for i in range(len(full_prompts), len(slides_text)):
                        fallback = self._match_scene_to_content_unique(slides_text[i], used_scenes)
                        used_scenes.add(fallback)
                        full_prompts.append(f"{base_aesthetic}, {fallback}")

                logger.info(f"Generated {len(full_prompts)} contextual image prompts")
                return full_prompts
            else:
                raise ValueError("No JSON array found in response")

        except Exception as e:
            logger.error(f"Failed to generate contextual prompts: {e}")
            logger.info("Falling back to keyword matching")
            used_scenes = set()
            fallback_prompts = []
            for text in slides_text:
                scene = self._match_scene_to_content_unique(text, used_scenes)
                used_scenes.add(scene)
                fallback_prompts.append(f"{base_aesthetic}, {scene}")
            return fallback_prompts

    @staticmethod
    def _sanitize_image_prompt(prompt: str) -> str:
        """Clean up image prompt before sending to Gemini to prevent common issues."""
        # 1. Truncate at last complete sentence if prompt was cut off mid-sentence
        # Find the last period, exclamation, or closing quote before the aesthetic section
        aesthetic_markers = ["Soft watercolor", "iPhone photo", "iphone photo"]
        aesthetic_start = len(prompt)
        for marker in aesthetic_markers:
            idx = prompt.find(marker)
            if idx > 0:
                aesthetic_start = min(aesthetic_start, idx)

        scene_part = prompt[:aesthetic_start].rstrip(", ")
        aesthetic_part = prompt[aesthetic_start:]

        # If scene part ends mid-sentence (no terminal punctuation), truncate to last complete sentence
        if scene_part and scene_part[-1] not in '.!?"\'':
            last_period = max(scene_part.rfind('.'), scene_part.rfind('!'), scene_part.rfind('"'))
            if last_period > 0:
                scene_part = scene_part[:last_period + 1]

        # 2. Strip text/writing references that Gemini will render as gibberish
        text_patterns = [
            r'(?:visible|showing|reads?|displaying|with)\s+(?:on|the)\s+(?:a\s+)?(?:microwave|oven|clock|timer|screen|phone|label|sign|book|page|note|chart).*?(?:\.|,)',
            r'times?\s+written\s+on\s+(?:masking\s+)?tape.*?(?:\.|,)',
            r'(?:labeled|labelled)\s+bottles?.*?(?:\.|,)',
            r'handwritten\s+(?:feeding\s+)?chart.*?(?:\.|,)',
            r'\([^)]*visible[^)]*\)',  # (visible on microwave clock)
            r'\d+:\d+\s*(?:AM|PM|am|pm)',  # Time references like "2:47 AM"
        ]
        for pattern in text_patterns:
            scene_part = re.sub(pattern, '', scene_part, flags=re.IGNORECASE)

        # 3. Remove references to multiple babies/children (unless "siblings" topic)
        multi_child_patterns = [
            r'two\s+(?:different\s+)?(?:babies|children|kids|toddlers)',
            r'(?:babies|children|kids)\s+(?:sit|play|stand)\s+(?:on\s+)?(?:opposite|different)',
        ]
        for pattern in multi_child_patterns:
            scene_part = re.sub(pattern, 'a child', scene_part, flags=re.IGNORECASE)

        # 4. Clean up double spaces and dangling commas
        scene_part = re.sub(r'\s+', ' ', scene_part)
        scene_part = re.sub(r',\s*,', ',', scene_part)
        scene_part = re.sub(r',\s*\.', '.', scene_part)
        scene_part = scene_part.strip().rstrip(',').strip()

        result = f"{scene_part}, {aesthetic_part}" if aesthetic_part else scene_part
        return result

    def _match_scene_to_content(self, content_text: str) -> str:
        """Match content keywords to scene prompts (fallback)"""
        return self._match_scene_to_content_unique(content_text, set())

    def _match_scene_to_content_unique(self, content_text: str, used_scenes: set) -> str:
        """Match content keywords to scene prompts, avoiding already-used scenes"""
        text_lower = content_text.lower()

        # Try to find matching scene that hasn't been used yet
        for scene_id, scene_data in self.scenes["scenes"].items():
            keywords = scene_data.get("keywords", [])
            for keyword in keywords:
                if keyword in text_lower and scene_data["prompt"] not in used_scenes:
                    return scene_data["prompt"]

        # If best match was already used, try any unused scene
        available_scenes = list(self.scenes["scenes"].values())
        unused = [s["prompt"] for s in available_scenes if s["prompt"] not in used_scenes]
        if unused:
            return random.choice(unused)

        # All scenes used — pick random (better than nothing)
        if available_scenes:
            return random.choice([s["prompt"] for s in available_scenes])

        # Ultimate fallback
        return "Professional setting, modern workspace, authentic moment"

    def _resize_to_instagram(self, img: Image.Image) -> Image.Image:
        """Resize/crop to exact 9:16 aspect ratio (1080x1920)"""
        target_width, target_height = self.SLIDE_WIDTH, self.SLIDE_HEIGHT
        img_width, img_height = img.size

        # Calculate aspect ratios
        target_ratio = target_width / target_height
        img_ratio = img_width / img_height

        if abs(img_ratio - target_ratio) > 0.01:  # Need to crop/resize
            if img_ratio > target_ratio:
                # Image too wide, crop width
                new_width = int(img_height * target_ratio)
                left = (img_width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img_height))
            else:
                # Image too tall, crop height
                new_height = int(img_width / target_ratio)
                top = (img_height - new_height) // 2
                img = img.crop((0, top, img_width, top + new_height))

        # Resize to target dimensions
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)
        return img

    def _apply_hook_visual_drama(self, img: Image.Image) -> Image.Image:
        """Apply minimal processing to keep photo bright and vibrant"""
        # Keep photo bright - only slight darkening for text contrast
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(0.95)  # 5% darker (was 70% darker!)

        # Slight contrast boost to make colors pop
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.1)  # Subtle (was 1.4)

        # Keep warm tones (no color temperature change)
        # Removed: Color desaturation
        # Removed: Heavy vignette effect

        return img

    def _apply_vignette(self, img: Image.Image, intensity: float = 0.3) -> Image.Image:
        """Apply vignette effect (darker edges)"""
        import numpy as np

        # Convert to numpy array
        img_array = np.array(img)
        height, width = img_array.shape[:2]

        # Create radial gradient mask
        center_x, center_y = width / 2, height / 2
        y, x = np.ogrid[:height, :width]

        # Calculate distance from center (normalized)
        max_dist = np.sqrt(center_x**2 + center_y**2)
        dist = np.sqrt((x - center_x)**2 + (y - center_y)**2) / max_dist

        # Create vignette mask (1.0 at center, fades to (1-intensity) at edges)
        vignette = np.clip(1.0 - (dist * intensity), 1.0 - intensity, 1.0)

        # Apply vignette to each channel
        if len(img_array.shape) == 3:
            vignette = vignette[:, :, np.newaxis]

        vignetted = (img_array * vignette).astype(np.uint8)

        return Image.fromarray(vignetted)

    def _add_text_overlay_pills(
        self,
        img: Image.Image,
        text: str,
        is_hook: bool
    ) -> Image.Image:
        """Add TikTok-native per-line pill text overlay (Montserrat font)"""
        import os

        img = img.convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        img_width, img_height = img.size
        center_x = img_width // 2

        # Font paths
        fonts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")
        font_bold_path = os.path.join(fonts_dir, "Montserrat-Bold.ttf")
        font_semi_path = os.path.join(fonts_dir, "Montserrat-SemiBold.ttf")

        # Fallback to system font if Montserrat not found
        if not os.path.exists(font_bold_path):
            font_bold_path = "/System/Library/Fonts/Helvetica.ttc"
            font_semi_path = font_bold_path

        # Pill styling constants
        bg_color = (0, 0, 0, 195)  # ~76% opacity black
        text_color = (255, 255, 255, 255)
        shadow_color = (0, 0, 0, 180)
        pill_radius = 7
        pad_h = 10
        pad_v = 5
        line_gap = 4
        section_gap = 16
        max_text_width = img_width - 120

        # Safe zones
        safe_top = 280
        safe_bottom = img_height - 300

        def _get_text_size(text, font):
            bbox = draw.textbbox((0, 0), text, font=font)
            return bbox[2] - bbox[0], bbox[3] - bbox[1], bbox[1]

        def _wrap(text, font):
            words = text.split()
            lines = []
            current = ""
            for word in words:
                test = f"{current} {word}".strip()
                w, _, _ = _get_text_size(test, font)
                if w <= max_text_width:
                    current = test
                else:
                    if current:
                        lines.append(current)
                    current = word
            if current:
                lines.append(current)
            return lines

        def _draw_pill(text, font, y):
            w, h, y_off = _get_text_size(text, font)
            pill_w = w + pad_h * 2
            pill_h = h + pad_v * 2
            pill_x = center_x - pill_w // 2
            draw.rounded_rectangle(
                [pill_x, y, pill_x + pill_w, y + pill_h],
                radius=pill_radius, fill=bg_color,
            )
            tx = center_x - w // 2
            ty = y + pad_v - y_off
            draw.text((tx + 1, ty + 1), text, font=font, fill=shadow_color)
            draw.text((tx, ty), text, font=font, fill=text_color)
            return y + pill_h

        def _draw_block(lines, font, start_y):
            y = start_y
            for line in lines:
                bottom = _draw_pill(line, font, y)
                y = bottom + line_gap
            return y - line_gap

        def _block_height(lines, font):
            total = 0
            for i, line in enumerate(lines):
                _, h, _ = _get_text_size(line, font)
                total += h + pad_v * 2
                if i < len(lines) - 1:
                    total += line_gap
            return total

        if is_hook:
            # Hook/CTA: single block, larger font
            font = ImageFont.truetype(font_bold_path, 54)
            wrapped = _wrap(text, font)
            total_h = _block_height(wrapped, font)
            start_y = (safe_top + safe_bottom) // 2 - total_h // 2
            start_y = max(safe_top, min(start_y, safe_bottom - total_h))
            _draw_block(wrapped, font, start_y)
        else:
            # Content slide: parse into headline / subtitle / body
            parts = text.split('\n')
            parts = [p.strip() for p in parts if p.strip()]

            # Build sections: first non-empty line = headline, rest = body
            # If first line contains a comma, split into headline + subtitle
            sections = []
            if parts:
                first_line = parts[0]
                if ',' in first_line and len(first_line.split(',')[0]) < 30:
                    # e.g. "philippians 4:6-7, the worry exchange"
                    headline_part = first_line.split(',')[0].strip()
                    subtitle_part = ','.join(first_line.split(',')[1:]).strip()
                    font_h = ImageFont.truetype(font_bold_path, 58)
                    font_s = ImageFont.truetype(font_semi_path, 42)
                    sections.append((_wrap(headline_part, font_h), font_h))
                    sections.append((_wrap(subtitle_part, font_s), font_s))
                else:
                    font_h = ImageFont.truetype(font_bold_path, 58)
                    sections.append((_wrap(first_line, font_h), font_h))

                # Remaining lines as body
                if len(parts) > 1:
                    body_text = ' '.join(parts[1:])
                    font_b = ImageFont.truetype(font_semi_path, 36)
                    sections.append((_wrap(body_text, font_b), font_b))

            # Calculate total height
            total_h = 0
            for wrapped, font in sections:
                total_h += _block_height(wrapped, font)
            total_h += section_gap * max(0, len(sections) - 1)

            start_y = (safe_top + safe_bottom) // 2 - total_h // 2
            start_y = max(safe_top, min(start_y, safe_bottom - total_h))

            y = start_y
            for wrapped, font in sections:
                y = _draw_block(wrapped, font, y)
                y += section_gap

        result = Image.alpha_composite(img, overlay).convert("RGB")
        return result

    def _add_text_overlay(
        self,
        img: Image.Image,
        text: str,
        is_hook: bool
    ) -> Image.Image:
        """Add text overlay with pilmoji (emoji support)"""

        # Apply minimal image adjustments to keep photos bright
        if is_hook:
            # Apply minimal visual adjustments for hooks
            img = self._apply_hook_visual_drama(img)
        else:
            # Keep content slides bright too (minimal darkening)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.95)  # Only 5% darker (was 25% darker)

        # Store original dimensions
        original_width, original_height = img.size

        # Create expanded canvas for emoji rendering (prevent clipping)
        edge_padding = 200
        expanded_width = img.width + (edge_padding * 2)
        expanded_height = img.height + (edge_padding * 2)

        expanded_img = Image.new('RGB', (expanded_width, expanded_height), (0, 0, 0))
        expanded_img.paste(img, (edge_padding, edge_padding))

        img = expanded_img
        img_width = original_width
        img_height = original_height

        # Load fonts
        try:
            font_path = "/System/Library/Fonts/Helvetica.ttc"
            if is_hook:
                font = ImageFont.truetype(font_path, 76)
            else:
                font_title = ImageFont.truetype(font_path, 72)
                font_body = ImageFont.truetype(font_path, 40)
        except Exception as e:
            logger.warning(f"Could not load font: {e}, using default")
            font = ImageFont.load_default()
            font_title = font
            font_body = font

        # Create Pilmoji instance for emoji rendering
        with Pilmoji(img) as pilmoji:
            if is_hook:
                # Center-aligned hook text
                draw = ImageDraw.Draw(img)
                words = text.split()
                lines = []
                current_line = []
                max_width = int(img_width * 0.85)
                line_height = 95

                for word in words:
                    current_line.append(word)
                    test_line = " ".join(current_line)
                    bbox = draw.textbbox((0, 0), test_line, font=font)
                    text_width = bbox[2] - bbox[0]

                    if text_width > max_width:
                        if len(current_line) == 1:
                            lines.append(" ".join(current_line))
                            current_line = []
                        else:
                            current_line.pop()
                            if current_line:
                                lines.append(" ".join(current_line))
                            current_line = [word]

                if current_line:
                    lines.append(" ".join(current_line))

                # Calculate total height and center vertically within safe zones
                # TikTok safe zones: top 150px, bottom 320px, right 120px
                safe_top = 150
                safe_bottom = img_height - 320
                total_height = len(lines) * line_height
                start_y = (img_height - total_height) // 2
                # Clamp within safe zones
                start_y = max(safe_top, min(start_y, safe_bottom - total_height))

                # Draw centered lines with stroke
                y = start_y
                for line in lines:
                    bbox = draw.textbbox((0, 0), line, font=font)
                    text_width = bbox[2] - bbox[0]
                    x = (img_width - text_width) // 2

                    self._draw_text_with_stroke(
                        pilmoji, (x + edge_padding, y + edge_padding), line, font,
                        stroke_width=10  # Increased from 6 for bolder outline like screenshot
                    )
                    y += line_height

            else:
                # Content slides - left-aligned with title + body
                lines = text.split('\n')
                title = lines[0] if lines else ""
                body = '\n'.join(lines[1:]) if len(lines) > 1 else ""

                padding_x = 70
                padding_right = 120  # TikTok safe zone for like/comment/share buttons
                max_width = img_width - padding_x - padding_right

                draw = ImageDraw.Draw(img)

                # Wrap title
                title_lines = []
                if title:
                    words = title.split()
                    current_line = []
                    for word in words:
                        current_line.append(word)
                        test_line = " ".join(current_line)
                        bbox = draw.textbbox((0, 0), test_line, font=font_title)
                        text_width = bbox[2] - bbox[0]

                        if text_width > max_width:
                            if len(current_line) == 1:
                                title_lines.append(" ".join(current_line))
                                current_line = []
                            else:
                                current_line.pop()
                                if current_line:
                                    title_lines.append(" ".join(current_line))
                                current_line = [word]

                    if current_line:
                        title_lines.append(" ".join(current_line))

                # Calculate heights
                title_line_height = 100
                title_height = len(title_lines) * title_line_height if title_lines else 0
                title_spacing = 40

                # Wrap body
                body_lines = []
                if body:
                    words = body.split()
                    current_line = []
                    for word in words:
                        current_line.append(word)
                        test_line = " ".join(current_line)
                        bbox = draw.textbbox((0, 0), test_line, font=font_body)
                        text_width = bbox[2] - bbox[0]

                        if text_width > max_width:
                            if len(current_line) == 1:
                                body_lines.append(" ".join(current_line))
                                current_line = []
                            else:
                                current_line.pop()
                                if current_line:
                                    body_lines.append(" ".join(current_line))
                                current_line = [word]

                    if current_line:
                        body_lines.append(" ".join(current_line))

                body_line_spacing = 55
                body_height = len(body_lines) * body_line_spacing if body_lines else 0

                # Total content height
                total_height = title_height + title_spacing + body_height

                # Center vertically within TikTok safe zones
                # Top: 180px (emoji safe), Bottom: 320px from bottom
                safe_top = 180
                safe_bottom = img_height - 320
                centered_y = (img_height - total_height) // 2
                y = max(safe_top, min(centered_y, safe_bottom - total_height))

                x = padding_x

                # Draw title lines
                for title_line in title_lines:
                    self._draw_text_with_stroke(
                        pilmoji, (x + edge_padding, y + edge_padding), title_line, font_title,
                        stroke_width=8
                    )
                    y += title_line_height

                y += title_spacing

                # Draw body lines
                for body_line in body_lines:
                    self._draw_text_with_stroke(
                        pilmoji, (x + edge_padding, y + edge_padding), body_line, font_body,
                        stroke_width=5
                    )
                    y += body_line_spacing

        # Crop back to original size
        img = img.crop((edge_padding, edge_padding, edge_padding + original_width, edge_padding + original_height))

        return img

    def _draw_text_with_stroke(
        self,
        pilmoji: Pilmoji,
        position: tuple,
        text: str,
        font: ImageFont,
        stroke_width: int = 5
    ):
        """Draw text with multi-directional stroke for contrast"""
        x, y = position

        # Draw stroke in all directions
        for offset_x in range(-stroke_width, stroke_width + 1):
            for offset_y in range(-stroke_width, stroke_width + 1):
                if offset_x == 0 and offset_y == 0:
                    continue
                pilmoji.text(
                    (x + offset_x, y + offset_y),
                    text,
                    font=font,
                    fill=(0, 0, 0, 255)  # Black stroke
                )

        # Draw fill text on top
        pilmoji.text((x, y), text, font=font, fill=(255, 255, 255, 255))  # White text

    def _promo_caption_instruction(self, promo: str = None) -> str:
        """Return caption prompt injection for promo, or empty string."""
        if not promo:
            return ""
        cfg = self.PROMO_REGISTRY.get(promo)
        if not cfg:
            return ""
        return (
            f"\nPROMO MENTION: Naturally weave in a brief mention of {cfg['product_name']} "
            f"({cfg['one_liner']}) — e.g. 'check out {cfg['url']}' or 'link in bio for {cfg['product_name']}'. "
            f"Keep it subtle, one short phrase, not the focus of the caption.\n"
        )

    def _generate_caption(self, content: Dict, promo: str = None) -> str:
        """Generate contextual caption based on carousel content"""
        try:
            # Use consistent caption generation for all formats
            slides = content.get("slides", [])
            if not slides:
                return self._generate_caption_fallback()

            # Build context from slides
            hook = slides[0].get("text", "") if len(slides) > 0 else ""
            tips_summary = []
            for i, slide in enumerate(slides[1:-1], 1):
                tip_text = slide.get("text", "")[:100]
                if tip_text:
                    tips_summary.append(f"{i}. {tip_text}")

            tips_context = "\n".join(tips_summary[:3])

            # Get topic for keyword-rich caption
            topic = content.get("topic", "parenting tips")

            # Get account-specific CTA instruction if configured
            caption_cta_instruction = getattr(self.config, 'caption_cta_instruction', '')

            # Generate contextual caption (200-400 chars for TikTok SEO)
            prompt = f"""Generate a TikTok caption for this parenting carousel about "{topic}".

CAROUSEL HOOK:
{hook}

TIPS INCLUDED:
{tips_context}

REQUIREMENTS:
- 200-400 characters total (this is CRITICAL for TikTok search discovery)
- Format: [Hook sentence] + [1-2 context sentences with keywords] + [CTA question to drive comments]
- Casual, relatable tone - like texting a mom friend
- Include topic-relevant keywords naturally (TikTok search reads captions)
- NO hashtags (those come separately)
- NO emojis
- Lowercase style preferred
{caption_cta_instruction}
{self._promo_caption_instruction(promo)}
CAPTION FORMAT (follow this structure exactly):
[curiosity hook sentence]. [1-2 context sentences with topic keywords]. [link in bio mention if applicable]. [CTA question]

EXAMPLES:
- "the frozen washcloth trick sounds too simple but it changed everything for us during teething. most parents don't realize timing matters more than the method itself. which tip are you trying tonight?"
- "I spent $3000 on baby gear before learning what actually matters. turns out the expensive stuff sits unused while the cheap basics save your sanity every single day. which one surprised you most?"

Generate caption:"""

            caption_text = self.llm.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            ).strip('"\'')

            # Append link-in-bio if account requires it and LLM didn't include it
            caption_cta_suffix = getattr(self.config, 'caption_cta_suffix', '')
            if caption_cta_suffix and 'link in bio' not in caption_text.lower():
                caption_text = f"{caption_text}\n\n{caption_cta_suffix}"

            # Build topic-aware hashtags
            hashtags = self._build_topic_hashtags(topic)
            return f"{caption_text}\n\n{hashtags}"

        except Exception as e:
            logger.error(f"Failed to generate contextual caption: {e}")
            return self._generate_caption_fallback()

    def _generate_caption_fallback(self) -> str:
        """Fallback caption if generation fails"""
        hashtags = self._build_topic_hashtags("general")
        return f"save-worthy tips that actually work\n\n{hashtags}"

    def _build_topic_hashtags(self, topic: str) -> str:
        """Build topic-aware hashtag string: 2 broad + 2-3 topic-specific"""
        topic_lower = topic.lower()

        # Pick 2 broad primary tags
        primary_tags = self.config.hashtag_strategy.primary[:2]

        # Match topic to category for specific tags
        topic_hashtags = getattr(self.config.hashtag_strategy, 'topic_hashtags', None)
        specific_tags = []

        if topic_hashtags and isinstance(topic_hashtags, dict):
            # Keyword matching to find best category
            category_keywords = {
                "sleep": ["sleep", "nap", "bedtime", "wake", "night", "rest"],
                "development": ["development", "milestone", "cognitive", "language", "motor", "growth"],
                "feeding": ["feed", "eating", "meal", "food", "solid", "breastfeed", "bottle", "picky"],
                "behavior": ["tantrum", "discipline", "boundary", "behavior", "emotion", "sibling"],
                "activities": ["play", "activity", "sensory", "outdoor", "game", "craft"],
                "safety": ["safety", "babyproof", "choking", "hazard", "car seat", "first aid"],
                "gear": ["gear", "product", "registry", "must-have", "essential", "budget"],
            }

            matched_category = "general"
            for category, keywords in category_keywords.items():
                if any(kw in topic_lower for kw in keywords):
                    matched_category = category
                    break

            specific_tags = topic_hashtags.get(matched_category, topic_hashtags.get("general", []))

        # Combine: 2 broad + up to 3 specific (no duplicates)
        all_tags = list(primary_tags)
        for tag in specific_tags:
            if tag not in all_tags and len(all_tags) < 5:
                all_tags.append(tag)

        return " ".join([f"#{tag}" for tag in all_tags])

    def _apply_promo(self, content: Dict, promo: str, topic: str) -> Dict:
        """Soft-promote a product by weaving a mention into one tip and replacing the CTA slide.

        Args:
            content: Generated carousel content dict with "slides" list
            promo: Key into PROMO_REGISTRY (e.g. "slumbersongs")
            topic: The carousel topic for context

        Returns:
            Modified content dict with promo woven in
        """
        promo_config = self.PROMO_REGISTRY.get(promo)
        if not promo_config:
            logger.warning(f"⚠️  Unknown promo '{promo}' — skipping. Available: {list(self.PROMO_REGISTRY.keys())}")
            return content

        slides = content.get("slides", [])
        if len(slides) < 3:
            logger.warning("⚠️  Too few slides for promo injection — skipping")
            return content

        logger.info(f"🏷️  Applying '{promo}' promo overlay...")

        # 1. Replace CTA slide (last slide) with promo CTA
        cta_slide = slides[-1]
        cta_slide["text"] = promo_config["cta_slide_text"]
        cta_slide["type"] = "cta"

        # 2. Weave a natural mention into ONE middle tip slide using LLM
        # Pick a random middle slide (not hook, not CTA)
        middle_indices = list(range(1, len(slides) - 1))
        target_idx = random.choice(middle_indices)
        original_text = slides[target_idx]["text"]

        weave_prompt = f"""Rewrite this carousel tip to naturally include a subtle mention of {promo_config['product_name']}.

ORIGINAL TIP:
{original_text}

TOPIC: {topic}

PRODUCT CONTEXT:
{promo_config['tip_weave_instruction']}

RULES:
- Keep the same tip structure and length (within ~10 words of original)
- The mention should feel natural, not forced — like a friend's recommendation
- Do NOT make the product the main point of the tip
- Keep the same formatting style (lowercase if original is lowercase)
- Return ONLY the rewritten tip text, nothing else"""

        try:
            rewritten = self.llm.chat_completion(
                messages=[{"role": "user", "content": weave_prompt}],
                temperature=0.7,
                max_tokens=200,
            ).strip().strip('"\'')

            if rewritten and len(rewritten) > 10:
                slides[target_idx]["text"] = rewritten
                logger.info(f"   Wove promo into slide {target_idx + 1}")
            else:
                logger.warning("   LLM returned empty rewrite — keeping original")
        except Exception as e:
            logger.warning(f"   Failed to weave promo into tip: {e}")

        content["slides"] = slides
        return content

    def _generate_random_topic(self) -> str:
        """Generate random topic from content pillars, guided by tier priorities.

        Skips topics that appear in the last 10 generated topics to avoid repetition.
        """
        # Get last 10 topics (full history window) to avoid repeating
        recent_topics = set()
        try:
            for topic in self.topic_tracker.get_recent_topics(n=10):
                recent_topics.add(topic.lower())
        except Exception:
            pass

        max_attempts = 30

        for attempt in range(max_attempts):
            pillar = None

            # Try tier-based selection if performance context exists
            if self.performance_context:
                from core.analytics.generator_integration import pick_pillar_by_tier
                tier_pick = pick_pillar_by_tier(
                    self.performance_context, self.config.content_pillars,
                    context_path=self._context_path if self.config.seasonal_topics_enabled else None,
                    llm_client=self.llm if self.config.seasonal_topics_enabled else None,
                    recent_topics=recent_topics,
                )
                if tier_pick:
                    if tier_pick in self.config.content_pillars:
                        pillar = tier_pick
                    else:
                        # Raw tier topic (e.g. from tier_3_explore) — use directly
                        if tier_pick.lower() not in recent_topics:
                            logger.info(f"📊 Tier-guided topic (explore): '{tier_pick}'")
                            return tier_pick
                        elif attempt < max_attempts - 1:
                            continue

            if not pillar:
                pillar = random.choice(self.config.content_pillars)

            # Convert pillar to readable topic
            topic = self._pillar_to_topic(pillar)

            if topic.lower() not in recent_topics:
                return topic

            # Topic was recent, retry
            if attempt < max_attempts - 1:
                continue

        # Exhausted retries — use last generated topic anyway
        logger.warning(f"⚠️  Could not find non-recent topic after {max_attempts} attempts, using '{topic}'")
        return topic

    @staticmethod
    def _pillar_to_topic(pillar: str) -> str:
        """Convert a content pillar slug to a readable topic string."""
        topic_map = {
            # Sleep
            "sleep_schedules_and_routines": "age-appropriate sleep schedules",
            "sleep_training_methods": "gentle sleep training methods",
            "nap_transitions": "nap transition guide",
            # Development
            "physical_milestones": "physical development milestones by age",
            "cognitive_development": "cognitive development activities",
            "language_development": "language development tips",
            "social_emotional_skills": "building emotional intelligence in toddlers",
            # Feeding
            "breastfeeding_tips": "breastfeeding tips for new moms",
            "bottle_feeding_guide": "bottle feeding guide and schedule",
            "starting_solids": "starting solids timeline and tips",
            "picky_eating_solutions": "picky eater strategies that work",
            "toddler_meal_ideas": "easy toddler meal ideas",
            # Behavior
            "tantrum_management": "handling toddler tantrums calmly",
            "setting_boundaries": "setting healthy boundaries with toddlers",
            "positive_discipline": "positive discipline techniques",
            "sibling_dynamics": "helping siblings get along",
            # Play
            "age_appropriate_activities": "age-appropriate activities by month",
            "developmental_play": "developmental play ideas",
            "sensory_play_ideas": "sensory play activities for babies",
            "outdoor_activities": "outdoor activities for toddlers",
            # Safety
            "babyproofing_checklist": "complete babyproofing checklist",
            "car_seat_safety": "car seat safety guide",
            "choking_hazards": "choking hazards by age",
            "first_aid_basics": "baby first aid essentials",
            # Health
            "common_illnesses": "common baby illnesses and remedies",
            "teething_relief": "teething relief methods",
            "vaccine_schedules": "vaccine schedule explained",
            "when_to_call_doctor": "when to call the pediatrician",
            # Products
            "must_have_items": "baby must-haves by age",
            "budget_baby_gear": "budget-friendly baby gear",
            "product_comparisons": "baby product comparison guide",
            "registry_essentials": "baby registry essentials",
            # Parenting
            "managing_mom_guilt": "overcoming mom guilt",
            "self_care_for_parents": "self-care tips for new parents",
            "partner_communication": "communicating with your partner",
            "work_life_balance": "work-life balance with baby"
        }
        return topic_map.get(pillar, pillar.replace('_', ' '))

    def _create_output_dir(self, topic: str) -> Path:
        """Create output directory with date/topic structure, appending _v2 etc. if exists."""
        now = datetime.now()
        year = now.strftime("%Y")
        month = now.strftime("%m-%B").lower()
        date = now.strftime("%Y-%m-%d")

        # Generate slug
        topic_slug = self.slug_generator.generate(topic)

        # Build base path
        base_dir = Path(self.config.output_config.base_directory) / year / month
        output_dir = base_dir / f"{date}_{topic_slug}"

        # If dir already has content (slides/), append _v2, _v3, etc.
        if output_dir.exists() and any(output_dir.iterdir()):
            version = 2
            while True:
                versioned_dir = base_dir / f"{date}_{topic_slug}_v{version}"
                if not versioned_dir.exists() or not any(versioned_dir.iterdir()):
                    output_dir = versioned_dir
                    break
                version += 1
            logger.info(f"📁 Output dir existed, using {output_dir.name}")

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
