# AWS Fargate Deployment Guide

## Quick Deployment Steps

### 1. Build Docker Image

```bash
# Build the image
docker build -t youtube-crawler-mcp:latest .

# Test locally
docker-compose up
```

### 2. Push to AWS ECR

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Create ECR repository
aws ecr create-repository --repository-name youtube-crawler-mcp --region us-east-1

# Tag image
docker tag youtube-crawler-mcp:latest YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/youtube-crawler-mcp:latest

# Push image
docker push YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/youtube-crawler-mcp:latest
```

### 3. Store API Keys in AWS Secrets Manager

Create the following secrets in AWS Console:
- `youtube-api-key`
- `openai-api-key`
- `deepseek-api-key`

### 4. Create Fargate Task in ECS Console

1. **Task Definition**:
   - Launch type: Fargate
   - CPU: 1 vCPU (1024)
   - Memory: 2 GB (2048)
   - Container image: Your ECR URI

2. **Environment Variables**:
   - `AI_PROVIDER=deepseek`
   - `SUMMARY_MODEL=deepseek-reasoner`
   - `TEMP_DIR=/app/temp`

3. **Secrets** (from Secrets Manager):
   - `YOUTUBE_API_KEY`
   - `OPENAI_API_KEY`
   - `DEEPSEEK_API_KEY`

4. **Networking**:
   - VPC: Select your VPC
   - Subnets: Choose public subnets
   - Security Group: Allow outbound traffic (for API access)

### 5. Run Task

Run your Task Definition in an ECS Cluster.

## Cost Estimates

### Fargate Cost
- **CPU**: 1 vCPU @ $0.04048/hour
- **Memory**: 2 GB @ $0.004445/GB/hour
- **Total**: ~$0.049/hour (~$35/month for 24/7)

### API Cost
- **Whisper**: $0.006/min → $0.18 per 30-min video
- **DeepSeek**: ~$0.001 per summary
- **Total per video**: ~$0.181

## Optimization Tips

1. **On-demand execution**: Use Lambda or Step Functions to trigger tasks instead of 24/7 running
2. **Use Fargate Spot**: Save up to 70% on compute costs
3. **Cache transcripts**: Avoid reprocessing the same videos

## Monitoring

CloudWatch Logs automatically collects container logs:
- Log Group: `/ecs/youtube-crawler-mcp`
- View all MCP calls and errors in real-time

## Architecture

```
Client (Claude Desktop, etc.)
    ↓ MCP Protocol (stdio)
AWS Fargate Container
    ├── YouTube API (metadata)
    ├── OpenAI Whisper API (transcription)
    └── DeepSeek API (summarization)
```

## Security Best Practices

- ✅ Store API keys in Secrets Manager (never in code)
- ✅ Use IAM roles for ECS task permissions
- ✅ Enable CloudWatch Logs for monitoring
- ✅ Use private subnets with NAT gateway (recommended)
- ✅ Implement secrets rotation policy
