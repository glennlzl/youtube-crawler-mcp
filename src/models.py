"""Data models for YouTube data"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class ChannelMetadata(BaseModel):
    """YouTube channel metadata"""

    channel_id: str
    username: Optional[str] = None
    title: str
    description: str
    custom_url: Optional[str] = None
    avatar_url: Optional[HttpUrl] = None
    banner_url: Optional[HttpUrl] = None

    # Statistics
    subscriber_count: int = Field(ge=0)
    video_count: int = Field(ge=0)
    view_count: int = Field(ge=0)

    # Timestamps
    published_at: datetime

    # Social links
    social_links: list[str] = Field(default_factory=list)

    # Additional metadata
    country: Optional[str] = None
    keywords: list[str] = Field(default_factory=list)


class VideoMetadata(BaseModel):
    """YouTube video metadata"""

    video_id: str
    title: str
    description: str
    thumbnail_url: Optional[HttpUrl] = None

    # Channel info
    channel_id: str
    channel_title: str

    # Statistics
    view_count: int = Field(ge=0)
    like_count: int = Field(ge=0)
    comment_count: int = Field(ge=0)

    # Timestamps
    published_at: datetime
    duration_seconds: int = Field(ge=0)

    # Content
    tags: list[str] = Field(default_factory=list)
    category_id: Optional[str] = None

    # Availability
    has_subtitles: bool = False
    available_languages: list[str] = Field(default_factory=list)
    default_audio_language: Optional[str] = None  # Language from YouTube metadata


class VideoTranscript(BaseModel):
    """Video transcript data"""

    video_id: str
    language: str
    source: str  # "youtube_subtitles", "whisper_asr", "manual"
    text: str
    segments: Optional[list[dict]] = None  # For timestamped segments


class VideoSummary(BaseModel):
    """AI-generated video summary"""

    video_id: str
    title: str
    url: str

    # Metadata
    published_at: datetime
    duration_seconds: int
    view_count: int

    # Summary content
    summary: str = Field(description="2-3 paragraph summary")
    key_points: list[str] = Field(description="Main topics/points discussed")
    highlights: list[str] = Field(
        default_factory=list, description="Important quotes or moments"
    )
    topics: list[str] = Field(default_factory=list, description="Content tags/categories")

    # Source info
    has_subtitles: bool
    transcript_source: str  # "youtube", "whisper", "none"
    transcript_language: Optional[str] = None

    # Full transcript (optional)
    full_transcript: Optional[str] = None


class TimeRangeQuery(BaseModel):
    """Query parameters for time-range video search"""

    username: str
    start_date: datetime
    end_date: datetime
    max_videos: Optional[int] = Field(default=50, le=100)
    include_transcript: bool = Field(default=False)
