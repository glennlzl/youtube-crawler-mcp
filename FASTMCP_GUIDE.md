# FastMCP Implementation Guide

This is a complete rewrite of the YouTube Crawler MCP Server using **FastMCP** - the official, modern way to build MCP servers with Python.

## ✨ What's New

### Before (Old Implementation)
- Manual `Server` class from `mcp.server`
- Manual JSON-RPC handling
- Complex FastAPI integration
- More boilerplate code

### After (FastMCP Implementation)
- Simple `@mcp.tool()` decorators
- Automatic JSON-RPC handling
- Built-in Streamable HTTP support
- Clean, Pythonic code
- **One line to switch transports**: `mcp.run(transport="streamable-http")`

## 🚀 Quick Start

### Local Testing (stdio)

```bash
# Install dependencies
pip install -e .

# Run with stdio (for Claude Desktop)
python main.py stdio

# Or simply
python main.py
```

### Remote Server (Streamable HTTP)

```bash
# Run HTTP server on port 8080
python main.py streamable-http

# Custom port
PORT=3000 python main.py streamable-http
```

## 📁 New File Structure

```
youtubeCrawlerMcp/
├── src/
│   ├── fastmcp_server.py    # ✨ NEW: FastMCP server implementation
│   ├── server.py             # OLD: Original stdio server (kept for reference)
│   ├── http_server.py        # OLD: Manual FastAPI server (can be removed)
│   └── ... (other modules unchanged)
├── main.py                   # ✨ NEW: Universal entry point
├── pyproject.toml            # Updated: Added fastmcp dependency
└── Dockerfile                # Updated: Uses FastMCP
```

## 🔧 Configuration

### Environment Variables

```bash
# API Keys (required)
YOUTUBE_API_KEY=your_key
OPENAI_API_KEY=your_key
DEEPSEEK_API_KEY=your_key

# Server Configuration
MCP_TRANSPORT=streamable-http  # or "stdio"
PORT=8080
HOST=0.0.0.0

# Optional
AI_PROVIDER=deepseek
SUMMARY_MODEL=deepseek-reasoner
TEMP_DIR=/app/temp
```

### Claude Desktop Configuration

For **local stdio** mode:

```json
{
  "mcpServers": {
    "youtube-crawler": {
      "command": "python",
      "args": ["/path/to/youtubeCrawlerMcp/main.py", "stdio"],
      "env": {
        "YOUTUBE_API_KEY": "your_key",
        "OPENAI_API_KEY": "your_key",
        "DEEPSEEK_API_KEY": "your_key"
      }
    }
  }
}
```

For **remote HTTP** mode:

```json
{
  "mcpServers": {
    "youtube-crawler": {
      "url": "http://localhost:8080",
      "transport": "streamable-http"
    }
  }
}
```

## 🐳 Docker Usage

### Build

```bash
docker build -t youtube-crawler-mcp .
```

### Run Locally

```bash
docker run -p 8080:8080 \
  -e YOUTUBE_API_KEY=your_key \
  -e OPENAI_API_KEY=your_key \
  -e DEEPSEEK_API_KEY=your_key \
  youtube-crawler-mcp
```

### Deploy to ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 --profile news-account | \
  docker login --username AWS --password-stdin 383681097411.dkr.ecr.us-east-1.amazonaws.com

# Tag
docker tag youtube-crawler-mcp:latest \
  383681097411.dkr.ecr.us-east-1.amazonaws.com/mcp/youtube-crawler-mcp:latest

# Push
docker push 383681097411.dkr.ecr.us-east-1.amazonaws.com/mcp/youtube-crawler-mcp:latest
```

## 🧪 Testing

### Test with MCP Inspector

```bash
# Install MCP dev tools
pip install mcp[dev]

# Test your server
mcp dev main.py
```

### Test HTTP Endpoint

```bash
# Health check (if FastMCP provides one)
curl http://localhost:8080/health

# List tools (MCP JSON-RPC)
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list"
  }'
```

## 🔌 Using with Claude API

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": "分析 @mkbhd 最新的5个视频"
    }],
    mcp_servers=[{
        "type": "url",
        "name": "youtube-crawler",
        "url": "https://your-server-url.com"  # Your deployed server
    }],
    betas=["mcp-client-2025-04-04"]
)

print(response.content)
```

## 📊 Available Tools

### 1. `get_channel_metadata`

Get comprehensive channel information.

```json
{
  "username": "@mkbhd"
}
```

### 2. `get_latest_videos_summary`

Get AI summaries of latest N videos.

```json
{
  "username": "@mkbhd",
  "n": 5,
  "include_transcript": false
}
```

### 3. `get_videos_by_timerange`

Get AI summaries of videos in a date range.

```json
{
  "username": "@mkbhd",
  "start_date": "2025-01-01",
  "end_date": "2025-01-31",
  "max_videos": 20,
  "include_transcript": false
}
```

## 🚢 Deployment Options

### Option 1: AWS ECS/Fargate (Current)

**Pros**:
- Fully managed
- Scalable
- Integration with AWS services

**Cons**:
- Complex networking (Secrets Manager, VPC)
- Higher cost (~$26/month)
- Requires NAT Gateway or VPC Endpoints

**Status**: Infrastructure ready, networking issues to resolve

### Option 2: Google Cloud Run (Recommended)

**Pros**:
- Simplest deployment
- Auto HTTPS
- Pay per request
- Built-in secrets management
- Lowest cost (<$5/month)

**Cons**:
- Different cloud provider

**Steps**:
```bash
# Build and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT/youtube-crawler-mcp

# Deploy
gcloud run deploy youtube-crawler-mcp \
  --image gcr.io/YOUR_PROJECT/youtube-crawler-mcp \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars YOUTUBE_API_KEY=xxx,OPENAI_API_KEY=xxx,DEEPSEEK_API_KEY=xxx
```

### Option 3: Fly.io

**Pros**:
- Simple deployment
- Free tier available
- Good for side projects

```bash
fly launch
fly deploy
```

### Option 4: Local (Free)

Run on your machine and use with Claude Desktop (stdio mode).

## 🔍 Debugging

### Check logs

```bash
# Docker logs
docker logs <container-id>

# Local run
python main.py streamable-http

# With debug logging
LOG_LEVEL=DEBUG python main.py streamable-http
```

### Common Issues

**Issue**: Module not found
```bash
# Solution: Install in editable mode
pip install -e .
```

**Issue**: Missing API keys
```bash
# Solution: Set environment variables
export YOUTUBE_API_KEY=your_key
export OPENAI_API_KEY=your_key
export DEEPSEEK_API_KEY=your_key
```

**Issue**: Port already in use
```bash
# Solution: Use different port
PORT=3000 python main.py streamable-http
```

## 📚 FastMCP Resources

- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)

## 🎯 Next Steps

1. **Test locally**: `python main.py streamable-http`
2. **Deploy to Cloud Run**: Simplest option
3. **Test with Claude API**: Verify remote access
4. **Optional**: Resolve AWS ECS networking if you prefer AWS

---

**Key Benefits of FastMCP Rewrite**:
- ✅ Cleaner, more maintainable code
- ✅ Official standard approach
- ✅ Better community support
- ✅ Easier debugging
- ✅ Faster development
- ✅ Built-in transport switching
