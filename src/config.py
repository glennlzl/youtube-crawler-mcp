"""Configuration management"""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class Config(BaseModel):
    """Application configuration"""

    # API Keys
    youtube_api_key: str = Field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY", ""))
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    anthropic_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY")
    )
    deepseek_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("DEEPSEEK_API_KEY")
    )

    # Whisper Configuration
    whisper_model: str = Field(default_factory=lambda: os.getenv("WHISPER_MODEL", "base"))

    # Directories
    temp_dir: Path = Field(
        default_factory=lambda: Path(os.getenv("TEMP_DIR", "./temp"))
    )

    # MCP Server Configuration
    mcp_server_name: str = Field(
        default_factory=lambda: os.getenv("MCP_SERVER_NAME", "youtube-crawler")
    )
    mcp_server_version: str = Field(
        default_factory=lambda: os.getenv("MCP_SERVER_VERSION", "0.1.0")
    )

    # AI Model Configuration
    ai_provider: str = Field(
        default_factory=lambda: os.getenv("AI_PROVIDER", "openai")
    )  # "openai", "deepseek", "anthropic"
    summary_model: str = Field(
        default_factory=lambda: os.getenv("SUMMARY_MODEL", "gpt-4-turbo-preview")
    )
    max_summary_tokens: int = Field(default=20000)  # Increased for DeepSeek Reasoner

    # Performance
    max_concurrent_downloads: int = Field(default=3)
    cache_enabled: bool = Field(default=True)

    def __init__(self, **data):
        super().__init__(**data)
        # Create temp directory if it doesn't exist
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def validate_keys(self) -> list[str]:
        """Validate required API keys and return list of missing keys"""
        missing = []
        if not self.youtube_api_key:
            missing.append("YOUTUBE_API_KEY")

        # Validate AI provider key
        if self.ai_provider == "openai" and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        elif self.ai_provider == "deepseek" and not self.deepseek_api_key:
            missing.append("DEEPSEEK_API_KEY")
        elif self.ai_provider == "anthropic" and not self.anthropic_api_key:
            missing.append("ANTHROPIC_API_KEY")

        return missing


# Global config instance
config = Config()
