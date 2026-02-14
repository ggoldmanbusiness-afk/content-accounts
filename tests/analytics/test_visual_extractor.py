import pytest
from core.analytics.visual_extractor import (
    classify_attribute,
    extract_from_prompt,
    extract_from_post,
    PHOTOGRAPHY_STYLE,
    LIGHTING,
    COLOR_PALETTE,
    COMPOSITION,
    SCENE_SETTING,
    SUBJECT_FOCUS,
    MOOD,
)


SAMPLE_PROMPT = (
    "Close-up of a laptop screen showing a pricing proposal email with a bright red "
    "DECLINED notification banner across it, the reflection of a frustrated entrepreneur's "
    "face visible in the dark screen, their hand frozen mid-reach toward the keyboard. "
    "Behind them, a wall covered in sticky notes with crossed-out pricing strategies and "
    "coffee rings staining the desk, golden hour light cutting dramatically through "
    "venetian blinds creating stark shadows across the rejection message, creating a "
    "moment of defeat every service provider has experienced but rarely talks about. "
    "iPhone photography, professional business setting, natural office lighting, "
    "authentic moment, slightly grainy, real business life, NOT posed"
)

PLAYGROUND_PROMPT = (
    "Wide shot of a toddler running across a colorful playground, mother watching from "
    "a park bench in the background, warm golden hour sunlight, bright saturated colors "
    "of the jungle gym, joyful energetic movement captured mid-stride, iPhone photography, "
    "candid authentic moment"
)

BEDROOM_PROMPT = (
    "Overhead view of a baby sleeping peacefully in a crib, soft pastel blanket, "
    "gentle diffused window light creating calm serene atmosphere, close-up of tiny "
    "hands gripping a stuffed animal, warm cozy nursery setting, tender intimate moment"
)


class TestClassifyAttribute:
    def test_photography_style(self):
        result = classify_attribute(SAMPLE_PROMPT, PHOTOGRAPHY_STYLE)
        assert "iphone_authentic" in result

    def test_lighting(self):
        result = classify_attribute(SAMPLE_PROMPT, LIGHTING)
        assert "golden_hour" in result

    def test_composition_closeup(self):
        result = classify_attribute(SAMPLE_PROMPT, COMPOSITION)
        assert "closeup" in result

    def test_composition_wide(self):
        result = classify_attribute(PLAYGROUND_PROMPT, COMPOSITION)
        assert "wide" in result

    def test_scene_playground(self):
        result = classify_attribute(PLAYGROUND_PROMPT, SCENE_SETTING)
        assert "playground" in result

    def test_scene_bedroom(self):
        result = classify_attribute(BEDROOM_PROMPT, SCENE_SETTING)
        assert "bedroom" in result

    def test_subject_focus_hands(self):
        result = classify_attribute(BEDROOM_PROMPT, SUBJECT_FOCUS)
        assert "hands_detail" in result

    def test_subject_focus_face(self):
        result = classify_attribute(SAMPLE_PROMPT, SUBJECT_FOCUS)
        assert "face_expression" in result

    def test_mood_warm_cozy(self):
        result = classify_attribute(BEDROOM_PROMPT, MOOD)
        assert "warm_cozy" in result
        assert "calm" in result

    def test_mood_energetic(self):
        result = classify_attribute(PLAYGROUND_PROMPT, MOOD)
        assert "energetic" in result
        assert "joyful" in result

    def test_color_palette(self):
        result = classify_attribute(PLAYGROUND_PROMPT, COLOR_PALETTE)
        assert "warm_golden" in result
        assert "bright" in result

    def test_empty_text_returns_empty(self):
        result = classify_attribute("", PHOTOGRAPHY_STYLE)
        assert result == []

    def test_no_match_returns_empty(self):
        result = classify_attribute("abstract geometric shapes", SCENE_SETTING)
        assert result == []


class TestExtractFromPrompt:
    def test_extracts_multiple_attributes(self):
        result = extract_from_prompt(SAMPLE_PROMPT)
        assert "photography_style" in result
        assert "lighting" in result
        assert "composition" in result

    def test_bedroom_prompt_attributes(self):
        result = extract_from_prompt(BEDROOM_PROMPT)
        assert result["scene_setting"][0] == "bedroom"
        assert "calm" in result["mood"]
        assert "hands_detail" in result["subject_focus"]

    def test_empty_prompt(self):
        result = extract_from_prompt("")
        assert result == {}


class TestExtractFromPost:
    def test_multi_slide_dominant_selection(self):
        prompts = [PLAYGROUND_PROMPT, BEDROOM_PROMPT, PLAYGROUND_PROMPT]
        result = extract_from_post(prompts)
        # Playground appears 2x, bedroom 1x — playground scene should dominate
        assert result["dominant"].get("scene_setting") == "playground"

    def test_hook_attributes_from_first_slide(self):
        prompts = [SAMPLE_PROMPT, PLAYGROUND_PROMPT, BEDROOM_PROMPT]
        result = extract_from_post(prompts)
        assert result["hook"].get("photography_style") == "iphone_authentic"
        assert result["hook_composition"] == "closeup"

    def test_all_attributes_populated(self):
        prompts = [PLAYGROUND_PROMPT, BEDROOM_PROMPT]
        result = extract_from_post(prompts)
        assert "dominant" in result
        assert "hook" in result
        assert "all_attributes" in result
        # all_attributes should have frequency counts
        assert isinstance(result["all_attributes"].get("mood", {}), dict)

    def test_single_slide(self):
        result = extract_from_post([BEDROOM_PROMPT])
        assert result["dominant"].get("scene_setting") == "bedroom"
        assert result["hook"].get("scene_setting") == "bedroom"

    def test_empty_list(self):
        result = extract_from_post([])
        assert result["dominant"] == {}
        assert result["hook"] == {}
        assert result["hook_composition"] is None

    def test_hook_specific_fields(self):
        result = extract_from_post([PLAYGROUND_PROMPT])
        assert result["hook_photography_style"] == "iphone_authentic"
        assert result["hook_mood"] in ("joyful", "energetic")
        assert result["hook_composition"] == "wide"
