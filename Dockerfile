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
COPY mcp_config.json ./

# Create temp directory
RUN mkdir -p /app/temp

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TEMP_DIR=/app/temp

# Expose port (MCP uses stdio, but can expose for health checks)
EXPOSE 8080

# Run MCP server
CMD ["python", "-m", "src.server"]
