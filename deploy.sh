#!/bin/bash
# deploy.sh for AWS production deployment

set -e

echo "🚀 Deploying Kayak Trip Planner (AWS Production)..."

# Create necessary directories
mkdir -p data logs

# Stop existing container
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down || true

# Remove any existing volumes to ensure clean start
echo "Cleaning up old containers and images..."
docker system prune -f || true

# Rebuild and start with production config
echo "Building and starting containers..."
docker-compose -f docker-compose.prod.yml up --build -d

echo "✅ Deployment complete!"
echo ""
echo "📊 Container status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "📝 View logs with:"
echo "  docker-compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 Stop with:"
echo "  docker-compose -f docker-compose.prod.yml down"
