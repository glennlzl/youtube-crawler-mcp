"""YouTube Crawler MCP Server - FastMCP Implementation

A modern MCP server using FastMCP for YouTube data crawling with AI summarization.
Supports both stdio and Streamable HTTP transports.
"""

import json
import logging
import os
from datetime import datetime
from typing import Optional

from fastmcp import FastMCP

from .config import config
from .summarizer import VideoSummarizer
from .transcript_extractor import TranscriptExtractor
from .youtube_client import YouTubeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get configuration from environment
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")

# Create FastMCP server
mcp = FastMCP(
    name=config.mcp_server_name,
    port=PORT,
    host=HOST,
    debug=True,
    log_level="INFO"
)

# Global clients (initialized on first use)
youtube_client: Optional[YouTubeClient] = None
transcript_extractor: Optional[TranscriptExtractor] = None
summarizer: Optional[VideoSummarizer] = None


def initialize_clients():
    """Initialize all API clients (lazy initialization)"""
    global youtube_client, transcript_extractor, summarizer

    if youtube_client is not None:
        return  # Already initialized

    # Validate configuration
    missing_keys = config.validate_keys()
    if missing_keys:
        logger.error(f"Missing required configuration: {', '.join(missing_keys)}")
        logger.error("Please set these in your .env file or environment variables")
        raise ValueError(f"Missing API keys: {missing_keys}")

    logger.info("Initializing YouTube Crawler MCP Server...")
    youtube_client = YouTubeClient()
    transcript_extractor = TranscriptExtractor()
    summarizer = VideoSummarizer()
    logger.info("All clients initialized successfully")


@mcp.tool()
def get_channel_metadata(username: str) -> str:
    """Get comprehensive metadata for a YouTube channel.

    Retrieves channel information including:
    - Channel name, description, custom URL
    - Avatar and banner images
    - Subscriber count, video count, total views
    - Publication date, country, keywords
    - Social links

    Args:
        username: YouTube username (e.g., '@mkbhd'), handle, or channel ID

    Returns:
        JSON string with channel metadata
    """
    initialize_clients()

    logger.info(f"Fetching channel metadata for: {username}")

    metadata = youtube_client.get_channel_metadata(username)

    if not metadata:
        return json.dumps({"error": f"Channel not found: {username}"})

    # Format response
    response = {
        "channel_id": metadata.channel_id,
        "title": metadata.title,
        "description": metadata.description,
        "custom_url": metadata.custom_url,
        "avatar_url": str(metadata.avatar_url) if metadata.avatar_url else None,
        "statistics": {
            "subscribers": metadata.subscriber_count,
            "videos": metadata.video_count,
            "total_views": metadata.view_count,
        },
        "published_at": metadata.published_at.isoformat(),
        "country": metadata.country,
        "keywords": metadata.keywords,
    }

    return json.dumps(response, indent=2)


@mcp.tool()
def get_latest_videos_summary(
    username: str,
    n: int = 5,
    include_transcript: bool = False
) -> str:
    """Get AI-powered summaries of the latest N videos from a channel.

    Features:
    - Fetches the most recent videos from a channel
    - Automatically extracts transcripts (YouTube subtitles OR Whisper ASR)
    - Generates AI summaries with key points, highlights, and topics
    - Supports videos with or without subtitles

    Args:
        username: YouTube username, handle, or channel ID
        n: Number of latest videos to summarize (default: 5, max: 50)
        include_transcript: Include full transcript in response (default: false)

    Returns:
        JSON string with video summaries
    """
    initialize_clients()

    if n < 1 or n > 50:
        return json.dumps({"error": "n must be between 1 and 50"})

    logger.info(f"Fetching {n} latest videos for: {username}")

    try:
        # Get channel ID
        if username.startswith("UC") and len(username) == 24:
            channel_id = username
        else:
            channel_id = youtube_client.get_channel_id_from_username(username)

        if not channel_id:
            return json.dumps({"error": f"Channel not found: {username}"})

        # Get latest videos
        videos = youtube_client.get_latest_videos(channel_id, n)

        if not videos:
            return json.dumps({"error": "No videos found"})

        logger.info(f"Found {len(videos)} videos, extracting transcripts...")

        # Extract transcripts and generate summaries
        summaries = []

        for video in videos:
            logger.info(f"Processing video: {video.title}")

            # Prepare video metadata for language detection
            video_metadata_dict = {
                "snippet": {
                    "defaultAudioLanguage": video.default_audio_language,
                }
            }

            # Get transcript with language detection
            transcript = transcript_extractor.get_transcript(
                video.video_id, video_metadata_dict
            )

            if not transcript:
                logger.warning(f"Could not extract transcript for {video.video_id}")
                continue

            # Generate summary
            summary = summarizer.summarize_video(
                video,
                transcript,
                include_transcript,
            )

            summaries.append({
                "video_id": summary.video_id,
                "title": summary.title,
                "url": summary.url,
                "published_at": summary.published_at.isoformat(),
                "duration_seconds": summary.duration_seconds,
                "view_count": summary.view_count,
                "summary": summary.summary,
                "key_points": summary.key_points,
                "highlights": summary.highlights,
                "topics": summary.topics,
                "transcript_source": summary.transcript_source,
                "full_transcript": summary.full_transcript,
            })

        # Format response
        response = {
            "channel": username,
            "videos_processed": len(summaries),
            "summaries": summaries,
        }

        return json.dumps(response, indent=2)

    except Exception as e:
        logger.error(f"Error processing videos: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_videos_by_timerange(
    username: str,
    start_date: str,
    end_date: str,
    max_videos: int = 20,
    include_transcript: bool = False
) -> str:
    """Get AI summaries of videos published within a specific time range.

    Features:
    - Query videos by publication date range
    - Automatic transcript extraction (subtitles or ASR)
    - Batch AI summarization
    - Efficient parallel processing

    Args:
        username: YouTube username, handle, or channel ID
        start_date: Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        end_date: End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        max_videos: Maximum number of videos to process (default: 20, max: 100)
        include_transcript: Include full transcripts (default: false)

    Returns:
        JSON string with video summaries for the time range
    """
    initialize_clients()

    if max_videos < 1 or max_videos > 100:
        return json.dumps({"error": "max_videos must be between 1 and 100"})

    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))

        logger.info(f"Fetching videos for {username} from {start_dt} to {end_dt}")

        # Get channel ID
        if username.startswith("UC") and len(username) == 24:
            channel_id = username
        else:
            channel_id = youtube_client.get_channel_id_from_username(username)

        if not channel_id:
            return json.dumps({"error": f"Channel not found: {username}"})

        # Get videos in time range
        videos = youtube_client.get_videos_by_timerange(
            channel_id,
            start_dt,
            end_dt,
            max_videos,
        )

        if not videos:
            return json.dumps({"error": "No videos found in this time range"})

        logger.info(f"Found {len(videos)} videos, processing...")

        # Process videos
        summaries = []

        for video in videos:
            logger.info(f"Processing: {video.title}")

            # Prepare video metadata for language detection
            video_metadata_dict = {
                "snippet": {
                    "defaultAudioLanguage": video.default_audio_language,
                }
            }

            transcript = transcript_extractor.get_transcript(
                video.video_id, video_metadata_dict
            )

            if not transcript:
                logger.warning(f"Skipping {video.video_id} - no transcript")
                continue

            summary = summarizer.summarize_video(
                video,
                transcript,
                include_transcript,
            )

            summaries.append({
                "video_id": summary.video_id,
                "title": summary.title,
                "url": summary.url,
                "published_at": summary.published_at.isoformat(),
                "summary": summary.summary,
                "key_points": summary.key_points,
                "topics": summary.topics,
                "full_transcript": summary.full_transcript,
            })

        # Format response
        response = {
            "channel": username,
            "time_range": {
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
            },
            "videos_found": len(videos),
            "videos_processed": len(summaries),
            "summaries": summaries,
        }

        return json.dumps(response, indent=2)

    except ValueError as e:
        return json.dumps({"error": f"Invalid date format: {str(e)}"})
    except Exception as e:
        logger.error(f"Error processing time range query: {e}", exc_info=True)
        return json.dumps({"error": str(e)})


# Startup message
logger.info(f"YouTube Crawler MCP Server initialized")
logger.info(f"Server name: {config.mcp_server_name}")
logger.info(f"Port: {PORT}")
logger.info(f"Host: {HOST}")
