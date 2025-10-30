FROM python:3.11-slim

# Install system dependencies for ffmpeg (required by yt-dlp)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY src/ ./src/
COPY main.py ./
COPY mcp_config.json ./

# Create temp directory
RUN mkdir -p /app/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/app/temp
ENV MCP_TRANSPORT=streamable-http
ENV PORT=8080
ENV HOST=0.0.0.0

# Expose port for HTTP server
EXPOSE 8080

# Run FastMCP server with Streamable HTTP transport
CMD ["python", "main.py", "streamable-http"]
