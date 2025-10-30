# YouTube Crawler MCP Server

A Model Context Protocol (MCP) server for YouTube data crawling with AI-powered summarization. Built with **FastMCP** for easy deployment as both local and remote MCP server.

## ✨ Features

- **Channel metadata** retrieval
- **AI video summaries** with automatic transcription (Whisper API)
- **Time-range queries** for videos
- Supports videos with/without subtitles
- Multi-language support with smart language detection
- **Dual transport**: stdio (local) and Streamable HTTP (remote)
- **Cloud-ready**: Deploy to AWS, Google Cloud Run, Fly.io, etc.

## 🚀 Quick Start

### Local Usage (stdio)

```bash
# Install dependencies
pip install -e .

# Configure environment
export YOUTUBE_API_KEY=your_youtube_key
export OPENAI_API_KEY=your_openai_key
export DEEPSEEK_API_KEY=your_deepseek_key

# Run with stdio (for Claude Desktop)
python main.py stdio
```

### Remote Server (Streamable HTTP)

```bash
# Run HTTP server
python main.py streamable-http

# Server will start on http://0.0.0.0:8080
# Use with Claude API, Lambda, or other cloud agents
```

### Docker

```bash
# Build
docker build -t youtube-crawler-mcp .

# Run
docker run -p 8080:8080 \
  -e YOUTUBE_API_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  -e DEEPSEEK_API_KEY=your_key \
  youtube-crawler-mcp
```

## MCP Tools

### 1. Get Channel Metadata
```json
{
  "username": "@channel_name"
}
```

### 2. Get Latest Videos Summary
```json
{
  "username": "@channel_name",
  "n": 5,
  "include_transcript": false
}
```

### 3. Get Videos by Time Range
```json
{
  "username": "@channel_name",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "max_videos": 10
}
```

## Configuration

### AI Providers

- **DeepSeek** (recommended): $0.28/1M tokens input, $0.42/1M output
- **OpenAI**: GPT-4 models
- **Anthropic**: Claude models

Set `AI_PROVIDER` in `.env` to switch providers.

### Transcription

Uses **OpenAI Whisper API** ($0.006/minute) with automatic language detection from YouTube metadata.

## Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "youtube-crawler": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/path/to/youtubeCrawlerMcp"
    }
  }
}
```

## Docker Deployment

### Build and Run Locally

```bash
# Build image
docker build -t youtube-crawler-mcp .

# Run with docker-compose
docker-compose up
```

### Deploy to AWS Fargate

See [DEPLOY.md](DEPLOY.md) for detailed AWS Fargate deployment instructions.

## Testing

```bash
# Test with specific channel
python test_m2story.py
```

## Cost Estimates

- Transcription: ~$0.18 per 30-min video (Whisper API)
- Summary: ~$0.004 per video (DeepSeek)
- **Total**: ~$0.184 per video

## License

MIT
