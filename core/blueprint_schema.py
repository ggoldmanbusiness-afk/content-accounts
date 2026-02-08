"""
Blueprint Schema
Pydantic models for viral post format blueprints.
All analysis fields are Optional to handle diverse post types.
"""

from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class PostType(str, Enum):
    TEXT_HEAVY = "text_heavy"
    HYBRID = "hybrid"
    VISUAL_FIRST = "visual_first"
    PHOTO_DUMP = "photo_dump"
    MEME_QUOTE = "meme_quote"
    INFOGRAPHIC = "infographic"


class ContentType(str, Enum):
    CAROUSEL = "carousel"
    SINGLE_IMAGE = "single_image"
    VIDEO = "video"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"


class PostMetrics(BaseModel):
    """Engagement metrics from the scraped post."""
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    engagement_rate: float = 0.0


class SlideVisualAnalysis(BaseModel):
    """Per-slide visual analysis from GPT-4o."""
    slide_number: int
    text_overlays: List[str] = Field(default_factory=list)
    visual_description: str = ""
    subjects: List[str] = Field(default_factory=list)
    mood: str = ""
    layout: str = ""
    dominant_colors: List[str] = Field(default_factory=list)
    font_style: Optional[str] = None
    text_position: Optional[str] = None


class OverallVisualStyle(BaseModel):
    """Overall visual style of the post."""
    aesthetic: str = ""
    color_palette: List[str] = Field(default_factory=list)
    consistency: str = ""
    visual_narrative: str = ""
    brand_elements: str = ""


class VisualAnalysisResult(BaseModel):
    """Complete visual analysis output."""
    post_type: PostType
    slide_count: int
    slides: List[SlideVisualAnalysis]
    overall_visual_style: OverallVisualStyle
    text_density: str = "none"  # high, medium, low, none


class SlideStructure(BaseModel):
    """Structural analysis of a single slide (for text-heavy/hybrid posts)."""
    slide_number: int
    role: str = ""  # hook, content, example, transition, cta
    pattern: str = ""  # curiosity_gap, numbered_tip, script, etc.
    text_template: str = ""  # abstracted template
    word_count: int = 0


class VisualSequence(BaseModel):
    """Visual storytelling analysis (for visual-first/photo dump posts)."""
    narrative_arc: str = ""
    subject_progression: List[str] = Field(default_factory=list)
    curation_strategy: str = ""


class InformationArchitecture(BaseModel):
    """How information is structured and presented."""
    flow: str = ""
    pacing: str = ""
    content_density: str = ""
    where_value_lives: str = "both"  # slides, caption, both


class FormatAnalysisResult(BaseModel):
    """Complete format analysis output."""
    format_description: str = ""
    slide_structure: Optional[List[SlideStructure]] = None  # text-heavy/hybrid
    visual_sequence: Optional[VisualSequence] = None  # visual-first/photo dump
    information_architecture: InformationArchitecture = Field(
        default_factory=InformationArchitecture
    )


class CopyAnalysisResult(BaseModel):
    """Copywriting analysis of visual slide copy."""
    primary_framework: Optional[str] = None  # PAS, AIDA, BAB, etc.
    framework_confidence: Optional[float] = None
    tone: str = ""
    copy_techniques: List[str] = Field(default_factory=list)
    power_words: List[str] = Field(default_factory=list)


class CaptionAnalysisResult(BaseModel):
    """Copywriting analysis of the post caption."""
    original_caption: str = ""
    primary_framework: Optional[str] = None
    hook_technique: str = ""
    cta_type: str = ""
    hashtag_strategy: str = ""
    hashtag_count: int = 0
    caption_length: str = ""  # micro, short, medium, long
    tone: str = ""


class ViralityInsight(BaseModel):
    """Synthesis of why the post went viral."""
    virality_score: int = Field(default=0, ge=0, le=100)
    key_factors: List[str] = Field(default_factory=list)
    format_contribution: str = ""
    visual_contribution: str = ""
    copy_contribution: str = ""
    replicability: str = ""  # high, medium, low
    replicability_notes: str = ""


class Blueprint(BaseModel):
    """Complete reusable blueprint for a viral post format."""
    # Metadata
    blueprint_id: str
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )
    source_url: str
    source_platform: Platform
    source_author: str
    source_post_id: str
    content_type: ContentType
    post_type: PostType

    # Metrics
    metrics: PostMetrics = Field(default_factory=PostMetrics)

    # Visual analysis
    visual_analysis: VisualAnalysisResult

    # Format analysis
    format_analysis: FormatAnalysisResult = Field(
        default_factory=FormatAnalysisResult
    )

    # Copy analysis (Optional - not all posts have text on slides)
    visual_copy_analysis: Optional[CopyAnalysisResult] = None
    caption_analysis: CaptionAnalysisResult = Field(
        default_factory=CaptionAnalysisResult
    )

    # Virality analysis
    virality: ViralityInsight = Field(default_factory=ViralityInsight)

    # Tags for searchability
    tags: List[str] = Field(default_factory=list)
    niche: str = ""

    class Config:
        validate_assignment = True


class ContentBriefSlide(BaseModel):
    """A single slide in an adapted content brief."""
    slide_number: int
    role: str = ""
    copy: str = ""
    visual_direction: str = ""
    layout: str = ""
    word_count_target: int = 0


class ContentBrief(BaseModel):
    """Adapted content brief for a specific account."""
    brief_id: str
    source_blueprint_id: str
    target_account: str
    adaptation_mode: str  # format_clone, inspired_adaptation
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat()
    )

    slides: List[ContentBriefSlide] = Field(default_factory=list)

    caption: Dict = Field(default_factory=dict)  # text, hashtags

    visual_direction: Dict = Field(default_factory=dict)  # palette, font, aesthetic

    generation_notes: str = ""
