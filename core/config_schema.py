"""
Pydantic Configuration Schema
Validates account configurations with type safety
"""

from typing import List, Dict, Optional
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator


class BrandIdentity(BaseModel):
    """Brand voice and personality"""
    character_type: str = Field(..., description="Account persona type")
    personality: str = Field(..., min_length=10, description="Brand personality description")
    value_proposition: str = Field(..., min_length=10, description="Core value to audience")
    voice_attributes: List[str] = Field(..., min_length=2, description="Voice characteristics")


class HashtagStrategy(BaseModel):
    """Hashtag usage configuration"""
    primary: List[str] = Field(..., min_length=1, description="Always-used hashtags")
    secondary: List[str] = Field(default_factory=list, description="Rotating hashtags")
    max_per_post: int = Field(default=4, ge=1, le=30, description="Max hashtags per post")
    style: str = Field(default="simple_hashtags_only", description="Hashtag style")


class ColorScheme(BaseModel):
    """Color palette for slides"""
    bg: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$', description="Background hex color")
    text: str = Field(..., pattern=r'^#[0-9A-Fa-f]{6}$', description="Text hex color")
    name: str = Field(..., min_length=1, description="Scheme name")


class QualityOverrides(BaseModel):
    """Quality thresholds and preferences"""
    min_hook_score: int = Field(default=16, ge=0, le=20, description="Min viral hook score")
    max_words_per_slide: int = Field(default=20, ge=5, le=50, description="Max words per slide")
    optimize_for_saves: bool = Field(default=True, description="Optimize for save behavior")
    allow_sensitive_words: bool = Field(default=False, description="Allow sensitive language")


class CarouselStrategy(BaseModel):
    """Carousel content strategy"""
    content_type: str = Field(..., description="Primary content type")
    slide_count_range: tuple[int, int] = Field(default=(5, 10), description="Slide count range")
    default_slide_count: int = Field(default=5, ge=5, le=10, description="Default slides")
    format: str = Field(default="checklist_framework", description="Content format")
    cta_focus: str = Field(default="save_this", description="CTA type")
    caption_style: str = Field(default="hashtags_only", description="Caption style")


class VisualStyle(BaseModel):
    """Visual design preferences"""
    mode: str = Field(default="text_only_slides", description="Slide mode")
    font_style: str = Field(default="clean_sans_serif", description="Font preference")
    slide_layout: str = Field(default="minimal_checklist", description="Layout style")


class OutputConfig(BaseModel):
    """Output directory configuration"""
    base_directory: str = Field(..., description="Base output directory (absolute path)")
    structure: str = Field(
        default="{year}/{month}/{date}_{topic}",
        description="Directory structure template"
    )
    include_metadata: bool = Field(default=True, description="Include metadata files")

    @field_validator('base_directory')
    @classmethod
    def validate_directory(cls, v: str) -> str:
        """Validate directory exists or is creatable"""
        path = Path(v)
        if not path.is_absolute():
            raise ValueError("base_directory must be an absolute path")
        # Note: We don't create it here, just validate it's absolute
        # Directory creation happens at generation time
        return v


class TopicTrackerConfig(BaseModel):
    """Topic tracking configuration"""
    max_history: int = Field(default=10, ge=1, le=100, description="Max topics to track")
    similarity_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Topic similarity threshold"
    )


class AccountConfig(BaseModel):
    """Complete account configuration"""
    # Identity
    account_name: str = Field(
        ...,
        pattern=r'^[a-z0-9_]+$',
        min_length=3,
        max_length=50,
        description="Account name (lowercase, alphanumeric + underscores)"
    )
    display_name: str = Field(..., min_length=3, description="Display name")

    # Brand
    brand_identity: BrandIdentity

    # Content
    content_pillars: List[str] = Field(
        ...,
        min_length=5,
        max_length=50,
        description="Content topic pillars"
    )

    # Visual
    color_schemes: List[ColorScheme] = Field(
        ...,
        min_length=3,
        description="Color palettes (min 3)"
    )
    visual_style: VisualStyle = Field(default_factory=VisualStyle)

    # Strategy
    hashtag_strategy: HashtagStrategy
    carousel_strategy: CarouselStrategy = Field(default_factory=CarouselStrategy)

    # Quality
    quality_overrides: QualityOverrides = Field(default_factory=QualityOverrides)

    # Output
    output_config: OutputConfig

    # Topic Tracking
    topic_tracker_config: TopicTrackerConfig = Field(default_factory=TopicTrackerConfig)

    # API Configuration (optional - can be from env)
    openrouter_api_key: Optional[str] = Field(default=None, description="OpenRouter API key")
    gemini_api_key: Optional[str] = Field(default=None, description="Gemini API key")
    claude_model: str = Field(
        default="anthropic/claude-sonnet-4.5",
        description="Claude model identifier"
    )

    # Hook formulas (optional)
    hook_formulas: List[str] = Field(default_factory=list, description="Custom hook templates")

    @field_validator('content_pillars')
    @classmethod
    def validate_pillars(cls, v: List[str]) -> List[str]:
        """Validate content pillars are unique and non-empty"""
        if len(v) != len(set(v)):
            raise ValueError("content_pillars must be unique")
        if any(not pillar.strip() for pillar in v):
            raise ValueError("content_pillars cannot contain empty strings")
        return v

    @field_validator('color_schemes')
    @classmethod
    def validate_colors(cls, v: List[ColorScheme]) -> List[ColorScheme]:
        """Validate color schemes are unique by name"""
        names = [scheme.name for scheme in v]
        if len(names) != len(set(names)):
            raise ValueError("color_schemes must have unique names")
        return v

    @model_validator(mode='after')
    def validate_slide_counts(self) -> 'AccountConfig':
        """Validate carousel strategy slide counts are consistent"""
        min_slides, max_slides = self.carousel_strategy.slide_count_range
        default = self.carousel_strategy.default_slide_count

        if min_slides > max_slides:
            raise ValueError("slide_count_range min must be <= max")

        if not (min_slides <= default <= max_slides):
            raise ValueError(
                f"default_slide_count ({default}) must be within "
                f"slide_count_range ({min_slides}, {max_slides})"
            )

        return self

    class Config:
        """Pydantic config"""
        validate_assignment = True
        extra = 'forbid'  # Catch typos in config files
