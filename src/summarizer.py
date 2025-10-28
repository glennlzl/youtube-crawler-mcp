"""AI-powered video summarization"""

import logging
from typing import Optional

from openai import OpenAI

from .config import config
from .models import VideoMetadata, VideoSummary, VideoTranscript

logger = logging.getLogger(__name__)


class VideoSummarizer:
    """Generate AI summaries from video transcripts"""

    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.provider = provider or config.ai_provider
        self.model = config.summary_model
        self.max_tokens = config.max_summary_tokens

        # Initialize client based on provider
        if self.provider == "openai":
            self.api_key = api_key or config.openai_api_key
            if not self.api_key:
                raise ValueError("OpenAI API key is required")
            self.client = OpenAI(api_key=self.api_key)
            if self.model == "gpt-4-turbo-preview":  # Use default
                self.model = "gpt-4-turbo-preview"

        elif self.provider == "deepseek":
            self.api_key = api_key or config.deepseek_api_key
            if not self.api_key:
                raise ValueError("DeepSeek API key is required")
            # DeepSeek uses OpenAI-compatible API
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://api.deepseek.com"
            )
            # Use DeepSeek's model
            if config.summary_model == "gpt-4-turbo-preview":  # Default not changed
                self.model = "deepseek-chat"
            else:
                self.model = config.summary_model

        elif self.provider == "anthropic":
            self.api_key = api_key or config.anthropic_api_key
            if not self.api_key:
                raise ValueError("Anthropic API key is required")
            # For Anthropic, we'll need to import their SDK
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                if config.summary_model == "gpt-4-turbo-preview":
                    self.model = "claude-3-5-sonnet-20241022"
                else:
                    self.model = config.summary_model
            except ImportError:
                raise ImportError(
                    "Anthropic SDK not installed. Install with: pip install anthropic"
                )

        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")

    def summarize_video(
        self,
        video_metadata: VideoMetadata,
        transcript: VideoTranscript,
        include_full_transcript: bool = False,
    ) -> VideoSummary:
        """
        Generate AI summary from video transcript

        Args:
            video_metadata: Video metadata
            transcript: Video transcript
            include_full_transcript: Include full transcript in summary

        Returns:
            VideoSummary object
        """
        try:
            # Generate summary using GPT-4
            summary_result = self._generate_summary(
                title=video_metadata.title,
                description=video_metadata.description,
                transcript_text=transcript.text,
            )

            return VideoSummary(
                video_id=video_metadata.video_id,
                title=video_metadata.title,
                url=f"https://www.youtube.com/watch?v={video_metadata.video_id}",
                published_at=video_metadata.published_at,
                duration_seconds=video_metadata.duration_seconds,
                view_count=video_metadata.view_count,
                summary=summary_result["summary"],
                key_points=summary_result["key_points"],
                highlights=summary_result.get("highlights", []),
                topics=summary_result.get("topics", []),
                has_subtitles=video_metadata.has_subtitles,
                transcript_source=transcript.source,
                transcript_language=transcript.language,
                full_transcript=transcript.text if include_full_transcript else None,
            )

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            raise

    def _generate_summary(
        self, title: str, description: str, transcript_text: str
    ) -> dict:
        """
        Call GPT-4 to generate structured summary

        Args:
            title: Video title
            description: Video description
            transcript_text: Full transcript text

        Returns:
            Dictionary with summary, key_points, highlights, topics
        """
        # Truncate transcript if too long (GPT-4 context limit)
        max_transcript_length = 50000  # characters
        if len(transcript_text) > max_transcript_length:
            transcript_text = transcript_text[:max_transcript_length] + "..."
            logger.warning(
                f"Transcript truncated to {max_transcript_length} characters"
            )

        system_prompt = """You are an expert at analyzing and summarizing YouTube video content.
Given a video's title, description, and transcript, provide a comprehensive summary.

Your response must be in JSON format with the following structure:
{
    "summary": "A 2-3 paragraph summary of the main content",
    "key_points": ["Point 1", "Point 2", "Point 3", ...],
    "highlights": ["Important quote or moment 1", "Important quote or moment 2", ...],
    "topics": ["Topic/Tag 1", "Topic/Tag 2", ...]
}

Guidelines:
- summary: Capture the main message and key insights (2-3 paragraphs)
- key_points: List 3-7 main points discussed (concise bullet points)
- highlights: 2-5 notable quotes, statistics, or moments (if applicable)
- topics: 3-8 relevant tags/categories for content classification
"""

        user_prompt = f"""Title: {title}

Description: {description}

Transcript:
{transcript_text}

Please analyze this video and provide a structured summary."""

        try:
            import json

            if self.provider == "anthropic":
                # Anthropic has different API
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=0.3,
                    system=system_prompt,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )
                result = json.loads(response.content[0].text)

            else:
                # OpenAI-compatible API (OpenAI, DeepSeek)
                api_params = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_tokens": self.max_tokens,
                    "response_format": {"type": "json_object"},
                }

                logger.info(f"Calling {self.provider} API with model {self.model}...")
                response = self.client.chat.completions.create(**api_params)

                # Handle deepseek-reasoner's special response format
                message = response.choices[0].message
                if self.provider == "deepseek" and self.model == "deepseek-reasoner":
                    # deepseek-reasoner returns reasoning_content + content
                    content = message.content
                    logger.info(f"DeepSeek reasoning mode - using final content")
                    logger.info(f"Content length: {len(content) if content else 0}")
                else:
                    content = message.content

                if not content:
                    logger.error(f"Empty content from {self.provider} API")
                    raise ValueError("Empty response from API")

                # Parse JSON from content (might be wrapped in markdown code blocks)
                content = content.strip()
                logger.info(f"Raw content preview: {content[:200]}...")

                if content.startswith("```json"):
                    content = content[7:]  # Remove ```json
                if content.startswith("```"):
                    content = content[3:]  # Remove ```
                if content.endswith("```"):
                    content = content[:-3]  # Remove trailing ```
                content = content.strip()

                result = json.loads(content)

            # Validate required fields
            if "summary" not in result or "key_points" not in result:
                raise ValueError("Invalid summary format from AI")

            # Ensure lists
            result.setdefault("highlights", [])
            result.setdefault("topics", [])

            return result

        except Exception as e:
            logger.error(f"Error calling {self.provider} API: {e}")
            # Return fallback summary
            return {
                "summary": f"Summary generation failed. Title: {title}",
                "key_points": ["Unable to generate summary"],
                "highlights": [],
                "topics": [],
            }

    def batch_summarize(
        self,
        video_metadata_list: list[VideoMetadata],
        transcripts: list[VideoTranscript],
        include_full_transcript: bool = False,
    ) -> list[VideoSummary]:
        """
        Summarize multiple videos (sequential processing)

        Args:
            video_metadata_list: List of video metadata
            transcripts: List of transcripts (same order as metadata)
            include_full_transcript: Include full transcripts

        Returns:
            List of VideoSummary objects
        """
        if len(video_metadata_list) != len(transcripts):
            raise ValueError("Metadata and transcripts lists must have same length")

        summaries = []

        for video_meta, transcript in zip(video_metadata_list, transcripts):
            try:
                summary = self.summarize_video(
                    video_meta, transcript, include_full_transcript
                )
                summaries.append(summary)
            except Exception as e:
                logger.error(f"Failed to summarize video {video_meta.video_id}: {e}")
                # Continue with next video

        return summaries
