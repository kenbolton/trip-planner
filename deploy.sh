#!/bin/bash
# deploy.sh

echo "🚀 Deploying Kayak Trip Planner..."

# Create necessary directories
mkdir -p data logs

# Set proper permissions
chmod 755 data logs

# Pull latest changes (if using git)
# git pull origin main

# Stop existing container
docker-compose down

# Rebuild and start
docker-compose up --build -d

echo "✅ Deployment complete!"
echo "📋 Check status: docker-compose logs -f"
