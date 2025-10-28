"""YouTube Data API v3 client"""

import logging
from datetime import datetime
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .config import config
from .models import ChannelMetadata, VideoMetadata

logger = logging.getLogger(__name__)


class YouTubeClient:
    """Client for YouTube Data API v3"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or config.youtube_api_key
        if not self.api_key:
            raise ValueError("YouTube API key is required")

        self.youtube = build("youtube", "v3", developerKey=self.api_key)

    def get_channel_id_from_username(self, username: str) -> Optional[str]:
        """
        Get channel ID from username or custom URL

        Args:
            username: YouTube username (e.g., '@mkbhd' or 'mkbhd')

        Returns:
            Channel ID or None if not found
        """
        # Remove @ if present
        username = username.lstrip("@")

        try:
            # Try custom URL first
            request = self.youtube.channels().list(
                part="id", forUsername=username, maxResults=1
            )
            response = request.execute()

            if response.get("items"):
                return response["items"][0]["id"]

            # Try searching by handle
            search_request = self.youtube.search().list(
                part="snippet", q=username, type="channel", maxResults=1
            )
            search_response = search_request.execute()

            if search_response.get("items"):
                return search_response["items"][0]["snippet"]["channelId"]

            return None

        except HttpError as e:
            logger.error(f"Error fetching channel ID: {e}")
            return None

    def get_channel_metadata(self, username: str) -> Optional[ChannelMetadata]:
        """
        Get comprehensive channel metadata

        Args:
            username: YouTube username, handle, or channel ID

        Returns:
            ChannelMetadata object or None if not found
        """
        try:
            # Get channel ID
            if username.startswith("UC") and len(username) == 24:
                # Already a channel ID
                channel_id = username
            else:
                channel_id = self.get_channel_id_from_username(username)

            if not channel_id:
                logger.error(f"Channel not found: {username}")
                return None

            # Fetch channel details
            request = self.youtube.channels().list(
                part="snippet,statistics,contentDetails,brandingSettings",
                id=channel_id,
            )
            response = request.execute()

            if not response.get("items"):
                return None

            item = response["items"][0]
            snippet = item["snippet"]
            statistics = item["statistics"]
            branding = item.get("brandingSettings", {})

            # Extract thumbnails (best quality available)
            thumbnails = snippet.get("thumbnails", {})
            avatar_url = (
                thumbnails.get("high", {}).get("url")
                or thumbnails.get("medium", {}).get("url")
                or thumbnails.get("default", {}).get("url")
            )

            # Extract banner
            banner_url = branding.get("image", {}).get("bannerExternalUrl")

            # Extract social links
            social_links = []
            for link in branding.get("channel", {}).get("unsubscribedTrailer", []):
                if isinstance(link, str):
                    social_links.append(link)

            return ChannelMetadata(
                channel_id=channel_id,
                username=username if not username.startswith("UC") else None,
                title=snippet["title"],
                description=snippet["description"],
                custom_url=snippet.get("customUrl"),
                avatar_url=avatar_url,
                banner_url=banner_url,
                subscriber_count=int(statistics.get("subscriberCount", 0)),
                video_count=int(statistics.get("videoCount", 0)),
                view_count=int(statistics.get("viewCount", 0)),
                published_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
                social_links=social_links,
                country=snippet.get("country"),
                keywords=branding.get("channel", {}).get("keywords", "").split(","),
            )

        except HttpError as e:
            logger.error(f"Error fetching channel metadata: {e}")
            return None

    def get_latest_videos(
        self, channel_id: str, max_results: int = 10
    ) -> list[VideoMetadata]:
        """
        Get latest videos from a channel

        Args:
            channel_id: YouTube channel ID
            max_results: Maximum number of videos to fetch (max 50 per request)

        Returns:
            List of VideoMetadata objects
        """
        try:
            # Get uploads playlist ID
            channel_request = self.youtube.channels().list(
                part="contentDetails", id=channel_id
            )
            channel_response = channel_request.execute()

            if not channel_response.get("items"):
                return []

            uploads_playlist_id = channel_response["items"][0]["contentDetails"][
                "relatedPlaylists"
            ]["uploads"]

            # Fetch videos from uploads playlist
            videos = []
            next_page_token = None

            while len(videos) < max_results:
                playlist_request = self.youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=min(50, max_results - len(videos)),
                    pageToken=next_page_token,
                )
                playlist_response = playlist_request.execute()

                video_ids = [
                    item["contentDetails"]["videoId"]
                    for item in playlist_response.get("items", [])
                ]

                if video_ids:
                    # Get detailed video information
                    videos_request = self.youtube.videos().list(
                        part="snippet,statistics,contentDetails", id=",".join(video_ids)
                    )
                    videos_response = videos_request.execute()

                    for item in videos_response.get("items", []):
                        videos.append(self._parse_video_metadata(item))

                next_page_token = playlist_response.get("nextPageToken")
                if not next_page_token:
                    break

            return videos[:max_results]

        except HttpError as e:
            logger.error(f"Error fetching latest videos: {e}")
            return []

    def get_videos_by_timerange(
        self,
        channel_id: str,
        start_date: datetime,
        end_date: datetime,
        max_results: int = 50,
    ) -> list[VideoMetadata]:
        """
        Get videos within a time range

        Args:
            channel_id: YouTube channel ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            max_results: Maximum number of videos

        Returns:
            List of VideoMetadata objects
        """
        try:
            videos = []
            next_page_token = None

            while len(videos) < max_results:
                search_request = self.youtube.search().list(
                    part="id",
                    channelId=channel_id,
                    type="video",
                    publishedAfter=start_date.isoformat(),
                    publishedBefore=end_date.isoformat(),
                    maxResults=min(50, max_results - len(videos)),
                    order="date",
                    pageToken=next_page_token,
                )
                search_response = search_request.execute()

                video_ids = [
                    item["id"]["videoId"] for item in search_response.get("items", [])
                ]

                if video_ids:
                    videos_request = self.youtube.videos().list(
                        part="snippet,statistics,contentDetails", id=",".join(video_ids)
                    )
                    videos_response = videos_request.execute()

                    for item in videos_response.get("items", []):
                        videos.append(self._parse_video_metadata(item))

                next_page_token = search_response.get("nextPageToken")
                if not next_page_token:
                    break

            return videos[:max_results]

        except HttpError as e:
            logger.error(f"Error fetching videos by time range: {e}")
            return []

    def _parse_video_metadata(self, item: dict) -> VideoMetadata:
        """Parse YouTube API response into VideoMetadata"""
        snippet = item["snippet"]
        statistics = item.get("statistics", {})
        content_details = item.get("contentDetails", {})

        # Parse ISO 8601 duration (PT1H2M3S -> seconds)
        duration = self._parse_duration(content_details.get("duration", "PT0S"))

        # Check for subtitles
        has_subtitles = content_details.get("caption") == "true"

        return VideoMetadata(
            video_id=item["id"],
            title=snippet["title"],
            description=snippet["description"],
            thumbnail_url=snippet.get("thumbnails", {})
            .get("high", {})
            .get("url"),
            channel_id=snippet["channelId"],
            channel_title=snippet["channelTitle"],
            view_count=int(statistics.get("viewCount", 0)),
            like_count=int(statistics.get("likeCount", 0)),
            comment_count=int(statistics.get("commentCount", 0)),
            published_at=datetime.fromisoformat(
                snippet["publishedAt"].replace("Z", "+00:00")
            ),
            duration_seconds=duration,
            tags=snippet.get("tags", []),
            category_id=snippet.get("categoryId"),
            has_subtitles=has_subtitles,
            default_audio_language=snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
        )

    @staticmethod
    def _parse_duration(duration_str: str) -> int:
        """
        Parse ISO 8601 duration to seconds

        Example: PT1H2M10S -> 3730 seconds
        """
        import re

        pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
        match = re.match(pattern, duration_str)

        if not match:
            return 0

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)

        return hours * 3600 + minutes * 60 + seconds
