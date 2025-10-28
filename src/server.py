"""YouTube Crawler MCP Server

A Model Context Protocol server for YouTube data crawling with AI summarization.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .config import config
from .models import TimeRangeQuery
from .summarizer import VideoSummarizer
from .transcript_extractor import TranscriptExtractor
from .youtube_client import YouTubeClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize server
app = Server(config.mcp_server_name)

# Initialize clients
youtube_client: Optional[YouTubeClient] = None
transcript_extractor: Optional[TranscriptExtractor] = None
summarizer: Optional[VideoSummarizer] = None


def initialize_clients():
    """Initialize all API clients"""
    global youtube_client, transcript_extractor, summarizer

    # Validate configuration
    missing_keys = config.validate_keys()
    if missing_keys:
        logger.error(f"Missing required configuration: {', '.join(missing_keys)}")
        logger.error("Please set these in your .env file")
        raise ValueError(f"Missing API keys: {missing_keys}")

    logger.info("Initializing YouTube Crawler MCP Server...")
    youtube_client = YouTubeClient()
    transcript_extractor = TranscriptExtractor()
    summarizer = VideoSummarizer()
    logger.info("All clients initialized successfully")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="get_channel_metadata",
            description="""Get comprehensive metadata for a YouTube channel.

            Retrieves channel information including:
            - Channel name, description, custom URL
            - Avatar and banner images
            - Subscriber count, video count, total views
            - Publication date, country, keywords
            - Social links

            Args:
                username (str): YouTube username (e.g., '@mkbhd'), handle, or channel ID

            Returns:
                ChannelMetadata object with all channel information
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "YouTube username (e.g., '@mkbhd'), handle, or channel ID",
                    }
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="get_latest_videos_summary",
            description="""Get AI-powered summaries of the latest N videos from a channel.

            Features:
            - Fetches the most recent videos from a channel
            - Automatically extracts transcripts (YouTube subtitles OR Whisper ASR)
            - Generates AI summaries with key points, highlights, and topics
            - Supports videos with or without subtitles

            Args:
                username (str): YouTube username, handle, or channel ID
                n (int): Number of latest videos to summarize (default: 5, max: 50)
                include_transcript (bool): Include full transcript in response (default: false)

            Returns:
                List of VideoSummary objects with AI-generated summaries
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "YouTube username, handle, or channel ID",
                    },
                    "n": {
                        "type": "integer",
                        "description": "Number of latest videos to summarize",
                        "default": 5,
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "include_transcript": {
                        "type": "boolean",
                        "description": "Include full transcript in response",
                        "default": False,
                    },
                },
                "required": ["username"],
            },
        ),
        Tool(
            name="get_videos_by_timerange",
            description="""Get AI summaries of videos published within a specific time range.

            Features:
            - Query videos by publication date range
            - Automatic transcript extraction (subtitles or ASR)
            - Batch AI summarization
            - Efficient parallel processing

            Args:
                username (str): YouTube username, handle, or channel ID
                start_date (str): Start date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
                end_date (str): End date in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
                max_videos (int): Maximum number of videos to process (default: 20, max: 100)
                include_transcript (bool): Include full transcripts (default: false)

            Returns:
                List of VideoSummary objects for videos in the time range
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "YouTube username, handle, or channel ID",
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
                    },
                    "max_videos": {
                        "type": "integer",
                        "description": "Maximum number of videos to process",
                        "default": 20,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "include_transcript": {
                        "type": "boolean",
                        "description": "Include full transcripts in response",
                        "default": False,
                    },
                },
                "required": ["username", "start_date", "end_date"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    try:
        if name == "get_channel_metadata":
            return await handle_get_channel_metadata(arguments)
        elif name == "get_latest_videos_summary":
            return await handle_get_latest_videos_summary(arguments)
        elif name == "get_videos_by_timerange":
            return await handle_get_videos_by_timerange(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        logger.error(f"Error handling tool {name}: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_channel_metadata(arguments: dict) -> list[TextContent]:
    """Handle get_channel_metadata tool"""
    username = arguments.get("username")

    if not username:
        return [TextContent(type="text", text="Error: username is required")]

    logger.info(f"Fetching channel metadata for: {username}")

    # Run blocking operation in thread pool
    loop = asyncio.get_event_loop()
    metadata = await loop.run_in_executor(
        None, youtube_client.get_channel_metadata, username
    )

    if not metadata:
        return [
            TextContent(type="text", text=f"Channel not found: {username}")
        ]

    # Format response
    import json

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

    return [TextContent(type="text", text=json.dumps(response, indent=2))]


async def handle_get_latest_videos_summary(arguments: dict) -> list[TextContent]:
    """Handle get_latest_videos_summary tool"""
    username = arguments.get("username")
    n = arguments.get("n", 5)
    include_transcript = arguments.get("include_transcript", False)

    if not username:
        return [TextContent(type="text", text="Error: username is required")]

    logger.info(f"Fetching {n} latest videos for: {username}")

    try:
        # Get channel ID
        loop = asyncio.get_event_loop()

        if username.startswith("UC") and len(username) == 24:
            channel_id = username
        else:
            channel_id = await loop.run_in_executor(
                None, youtube_client.get_channel_id_from_username, username
            )

        if not channel_id:
            return [TextContent(type="text", text=f"Channel not found: {username}")]

        # Get latest videos
        videos = await loop.run_in_executor(
            None, youtube_client.get_latest_videos, channel_id, n
        )

        if not videos:
            return [TextContent(type="text", text="No videos found")]

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
            transcript = await loop.run_in_executor(
                None, transcript_extractor.get_transcript, video.video_id, video_metadata_dict
            )

            if not transcript:
                logger.warning(f"Could not extract transcript for {video.video_id}")
                continue

            # Generate summary
            summary = await loop.run_in_executor(
                None,
                summarizer.summarize_video,
                video,
                transcript,
                include_transcript,
            )

            summaries.append(summary)

        # Format response
        import json

        response = {
            "channel": username,
            "videos_processed": len(summaries),
            "summaries": [
                {
                    "video_id": s.video_id,
                    "title": s.title,
                    "url": s.url,
                    "published_at": s.published_at.isoformat(),
                    "duration_seconds": s.duration_seconds,
                    "view_count": s.view_count,
                    "summary": s.summary,
                    "key_points": s.key_points,
                    "highlights": s.highlights,
                    "topics": s.topics,
                    "transcript_source": s.transcript_source,
                    "full_transcript": s.full_transcript,
                }
                for s in summaries
            ],
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error processing videos: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def handle_get_videos_by_timerange(arguments: dict) -> list[TextContent]:
    """Handle get_videos_by_timerange tool"""
    username = arguments.get("username")
    start_date_str = arguments.get("start_date")
    end_date_str = arguments.get("end_date")
    max_videos = arguments.get("max_videos", 20)
    include_transcript = arguments.get("include_transcript", False)

    if not all([username, start_date_str, end_date_str]):
        return [
            TextContent(
                type="text",
                text="Error: username, start_date, and end_date are required",
            )
        ]

    try:
        # Parse dates
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))

        logger.info(
            f"Fetching videos for {username} from {start_date} to {end_date}"
        )

        # Get channel ID
        loop = asyncio.get_event_loop()

        if username.startswith("UC") and len(username) == 24:
            channel_id = username
        else:
            channel_id = await loop.run_in_executor(
                None, youtube_client.get_channel_id_from_username, username
            )

        if not channel_id:
            return [TextContent(type="text", text=f"Channel not found: {username}")]

        # Get videos in time range
        videos = await loop.run_in_executor(
            None,
            youtube_client.get_videos_by_timerange,
            channel_id,
            start_date,
            end_date,
            max_videos,
        )

        if not videos:
            return [
                TextContent(type="text", text="No videos found in this time range")
            ]

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

            transcript = await loop.run_in_executor(
                None, transcript_extractor.get_transcript, video.video_id, video_metadata_dict
            )

            if not transcript:
                logger.warning(f"Skipping {video.video_id} - no transcript")
                continue

            summary = await loop.run_in_executor(
                None,
                summarizer.summarize_video,
                video,
                transcript,
                include_transcript,
            )

            summaries.append(summary)

        # Format response
        import json

        response = {
            "channel": username,
            "time_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "videos_found": len(videos),
            "videos_processed": len(summaries),
            "summaries": [
                {
                    "video_id": s.video_id,
                    "title": s.title,
                    "url": s.url,
                    "published_at": s.published_at.isoformat(),
                    "summary": s.summary,
                    "key_points": s.key_points,
                    "topics": s.topics,
                    "full_transcript": s.full_transcript,
                }
                for s in summaries
            ],
        }

        return [TextContent(type="text", text=json.dumps(response, indent=2))]

    except Exception as e:
        logger.error(f"Error processing time range query: {e}", exc_info=True)
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def main():
    """Main entry point"""
    try:
        # Initialize clients
        initialize_clients()

        # Run server
        logger.info("Starting YouTube Crawler MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
