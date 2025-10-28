"""Extract transcripts from YouTube videos (subtitles or ASR)"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

import yt_dlp
from openai import OpenAI

from .config import config
from .models import VideoTranscript

logger = logging.getLogger(__name__)


class TranscriptExtractor:
    """Extract transcripts from YouTube videos"""

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_dir = temp_dir or config.temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Initialize OpenAI client for Whisper API
        if config.openai_api_key:
            self.openai_client = OpenAI(api_key=config.openai_api_key)
        else:
            self.openai_client = None

    def get_transcript(
        self, video_id: str, video_metadata: Optional[dict] = None, prefer_subtitles: bool = True
    ) -> Optional[VideoTranscript]:
        """
        Get transcript for a video (tries subtitles first, then ASR)

        Args:
            video_id: YouTube video ID
            video_metadata: YouTube API video metadata (for language detection)
            prefer_subtitles: Try to get YouTube subtitles before ASR

        Returns:
            VideoTranscript or None if extraction fails
        """
        if prefer_subtitles:
            # Try YouTube subtitles first
            transcript = self._get_youtube_subtitles(video_id)
            if transcript:
                return transcript

        # Fall back to ASR (Whisper API)
        detected_language = self._detect_language(video_metadata) if video_metadata else None
        return self._get_whisper_transcript(video_id, language=detected_language)

    def _detect_language(self, video_metadata: dict) -> Optional[str]:
        """
        Detect language from YouTube video metadata

        Args:
            video_metadata: YouTube API video metadata

        Returns:
            Language code (zh, en, ja, etc.) or None for auto-detection
        """
        snippet = video_metadata.get("snippet", {})

        # Priority 1: defaultAudioLanguage
        if audio_lang := snippet.get("defaultAudioLanguage"):
            return self._convert_to_whisper_lang(audio_lang)

        # Priority 2: defaultLanguage
        if default_lang := snippet.get("defaultLanguage"):
            return self._convert_to_whisper_lang(default_lang)

        # Let Whisper auto-detect
        logger.info("No language metadata found, Whisper will auto-detect")
        return None

    @staticmethod
    def _convert_to_whisper_lang(youtube_lang: str) -> str:
        """
        Convert YouTube language code to Whisper language code

        Args:
            youtube_lang: YouTube language code (e.g., "zh-CN", "en-US")

        Returns:
            Whisper language code (e.g., "zh", "en")
        """
        # Mapping for common YouTube language codes
        mapping = {
            "zh-CN": "zh",
            "zh-TW": "zh",
            "zh-HK": "zh",
            "en-US": "en",
            "en-GB": "en",
            "ja-JP": "ja",
            "ko-KR": "ko",
            "es-ES": "es",
            "fr-FR": "fr",
            "de-DE": "de",
            "it-IT": "it",
            "pt-BR": "pt",
            "ru-RU": "ru",
            "ar-SA": "ar",
            "hi-IN": "hi",
        }

        # Try direct mapping first
        if youtube_lang in mapping:
            return mapping[youtube_lang]

        # Fall back to base language (e.g., "zh-CN" -> "zh")
        base_lang = youtube_lang.split("-")[0]
        return base_lang

    def _get_youtube_subtitles(self, video_id: str) -> Optional[VideoTranscript]:
        """
        Extract YouTube's native subtitles/captions

        Args:
            video_id: YouTube video ID

        Returns:
            VideoTranscript or None if no subtitles available
        """
        try:
            ydl_opts = {
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en"],  # Prefer English
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
            }

            video_url = f"https://www.youtube.com/watch?v={video_id}"

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)

                # Check for subtitles
                subtitles = info.get("subtitles", {})
                automatic_captions = info.get("automatic_captions", {})

                # Prefer manual subtitles over auto-generated
                available_subs = subtitles or automatic_captions

                if not available_subs:
                    logger.info(f"No subtitles found for video {video_id}")
                    return None

                # Get English subtitles (or first available language)
                language = "en" if "en" in available_subs else list(available_subs.keys())[0]
                sub_formats = available_subs[language]

                # Find JSON format (contains timing info)
                json_format = next(
                    (fmt for fmt in sub_formats if fmt["ext"] == "json3"), None
                )

                if not json_format:
                    # Fall back to any format
                    json_format = sub_formats[0]

                # Download subtitle file
                subtitle_path = self.temp_dir / f"{video_id}_{language}.{json_format['ext']}"

                ydl_opts_download = {
                    "writesubtitles": True,
                    "writeautomaticsub": True,
                    "subtitleslangs": [language],
                    "subtitlesformat": json_format["ext"],
                    "skip_download": True,
                    "outtmpl": str(self.temp_dir / video_id),
                    "quiet": True,
                }

                with yt_dlp.YoutubeDL(ydl_opts_download) as ydl_dl:
                    ydl_dl.download([video_url])

                # Parse subtitle file
                transcript_text = self._parse_subtitle_file(subtitle_path, json_format["ext"])

                # Cleanup
                if subtitle_path.exists():
                    subtitle_path.unlink()

                if transcript_text:
                    source = (
                        "youtube_subtitles"
                        if language in subtitles
                        else "youtube_auto_captions"
                    )

                    return VideoTranscript(
                        video_id=video_id,
                        language=language,
                        source=source,
                        text=transcript_text,
                    )

                return None

        except Exception as e:
            logger.error(f"Error extracting YouTube subtitles: {e}")
            return None

    def _get_whisper_transcript(self, video_id: str, language: Optional[str] = None) -> Optional[VideoTranscript]:
        """
        Use OpenAI Whisper API to transcribe video audio

        Args:
            video_id: YouTube video ID
            language: Language code (zh, en, ja, etc.) or None for auto-detection

        Returns:
            VideoTranscript or None if transcription fails
        """
        try:
            if not self.openai_client:
                logger.error("OpenAI API key not configured. Set OPENAI_API_KEY in .env")
                return None

            logger.info(f"Starting Whisper API transcription for video {video_id}")
            if language:
                logger.info(f"Detected language: {language}")

            # Download audio
            audio_path = self._download_audio(video_id)
            if not audio_path:
                return None

            # Check file size and compress if needed (OpenAI limit: 25MB)
            MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB
            file_size = audio_path.stat().st_size

            if file_size > MAX_FILE_SIZE:
                logger.warning(f"Audio file too large ({file_size / 1024 / 1024:.1f}MB), compressing...")
                audio_path = self._compress_audio(audio_path)
                if not audio_path:
                    return None
                logger.info(f"Compressed to {audio_path.stat().st_size / 1024 / 1024:.1f}MB")

            # Transcribe using OpenAI Whisper API
            logger.info("Calling OpenAI Whisper API...")
            with open(audio_path, "rb") as audio_file:
                transcription_args = {
                    "model": "whisper-1",
                    "file": audio_file,
                    "response_format": "verbose_json",  # Get detailed response with segments
                }

                # Add language parameter if detected
                if language:
                    transcription_args["language"] = language

                result = self.openai_client.audio.transcriptions.create(**transcription_args)

            # Cleanup audio file immediately
            if audio_path.exists():
                audio_path.unlink()
                logger.info(f"Deleted audio file: {audio_path}")

            # Extract transcript text
            transcript_text = result.text.strip()

            # Extract segments with timestamps (if available)
            segments = []
            if hasattr(result, 'segments') and result.segments:
                segments = [
                    {
                        "start": getattr(seg, 'start', 0),
                        "end": getattr(seg, 'end', 0),
                        "text": getattr(seg, 'text', '').strip(),
                    }
                    for seg in result.segments
                ]

            # Get language from result (either detected or specified)
            detected_lang = getattr(result, 'language', language or 'unknown')

            return VideoTranscript(
                video_id=video_id,
                language=detected_lang,
                source="openai_whisper_api",
                text=transcript_text,
                segments=segments if segments else None,
            )

        except Exception as e:
            logger.error(f"Error transcribing with OpenAI Whisper API: {e}")
            return None

    def _compress_audio(self, audio_path: Path) -> Optional[Path]:
        """
        Compress audio file to fit within OpenAI's 25MB limit

        Args:
            audio_path: Path to original audio file

        Returns:
            Path to compressed audio file or None
        """
        try:
            compressed_path = audio_path.parent / f"{audio_path.stem}_compressed.mp3"

            # Use ffmpeg to compress audio (lower bitrate)
            cmd = [
                "ffmpeg",
                "-i", str(audio_path),
                "-b:a", "32k",  # Very low bitrate for compression
                "-ac", "1",     # Convert to mono
                "-ar", "16000", # Lower sample rate
                "-y",           # Overwrite output file
                str(compressed_path)
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            # Delete original file
            if audio_path.exists():
                audio_path.unlink()

            return compressed_path

        except subprocess.CalledProcessError as e:
            logger.error(f"Error compressing audio with ffmpeg: {e.stderr.decode()}")
            return None
        except Exception as e:
            logger.error(f"Error compressing audio: {e}")
            return None

    def _download_audio(self, video_id: str) -> Optional[Path]:
        """
        Download audio from YouTube video

        Args:
            video_id: YouTube video ID

        Returns:
            Path to downloaded audio file or None
        """
        try:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            audio_path = self.temp_dir / f"{video_id}.mp3"

            ydl_opts = {
                "format": "bestaudio/best",
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "64",  # Lower quality to reduce file size
                    }
                ],
                "outtmpl": str(self.temp_dir / video_id),
                "quiet": True,
                "no_warnings": True,
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            if audio_path.exists():
                return audio_path

            logger.error(f"Audio file not found after download: {audio_path}")
            return None

        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None

    @staticmethod
    def _parse_subtitle_file(subtitle_path: Path, ext: str) -> Optional[str]:
        """
        Parse subtitle file and extract text

        Args:
            subtitle_path: Path to subtitle file
            ext: File extension (json3, vtt, srt, etc.)

        Returns:
            Combined transcript text or None
        """
        try:
            if not subtitle_path.exists():
                return None

            if ext == "json3":
                import json

                with open(subtitle_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Extract text from JSON3 format
                events = data.get("events", [])
                texts = []

                for event in events:
                    segs = event.get("segs", [])
                    for seg in segs:
                        text = seg.get("utf8", "").strip()
                        if text:
                            texts.append(text)

                return " ".join(texts)

            elif ext in ["vtt", "srt"]:
                import re

                with open(subtitle_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Remove timestamp lines and formatting
                if ext == "vtt":
                    # Remove WEBVTT header and cues
                    content = re.sub(r"WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
                    content = re.sub(
                        r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*?\n",
                        "",
                        content,
                    )
                else:  # srt
                    # Remove subtitle numbers and timestamps
                    content = re.sub(r"\d+\n", "", content)
                    content = re.sub(
                        r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}\n",
                        "",
                        content,
                    )

                # Clean up
                lines = [line.strip() for line in content.split("\n") if line.strip()]
                return " ".join(lines)

            else:
                logger.warning(f"Unsupported subtitle format: {ext}")
                return None

        except Exception as e:
            logger.error(f"Error parsing subtitle file: {e}")
            return None
