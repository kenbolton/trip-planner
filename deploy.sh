#!/bin/bash
# deploy.sh for AWS production deployment

set -e

echo "🚀 Deploying Kayak Trip Planner (AWS Production)..."

# Create necessary directories
mkdir -p data logs

# Set proper permissions for Docker volumes
# On AWS, the container user (kayakbot) needs write access
sudo chown -R 1000:1000 data logs || {
    echo "Warning: Could not set ownership with sudo, trying without..."
    chown -R 1000:1000 data logs 2>/dev/null || {
        echo "Warning: Could not set ownership. Will try to fix with docker..."
    }
}

chmod -R 755 data logs

# Pull latest changes (if using git)
# git pull origin main

# Stop existing container
echo "Stopping existing containers..."
docker-compose -f docker-compose.prod.yml down || true

# Remove any existing volumes to ensure clean start
echo "Cleaning up old containers and images..."
docker system prune -f || true

# Rebuild and start with production config
echo "Building and starting containers..."
docker-compose -f docker-compose.prod.yml up --build -d

# Fix permissions after container creation if needed
echo "Ensuring correct permissions..."
docker-compose -f docker-compose.prod.yml exec -T kayak-bot sh -c "
    test -w /app/data && test -w /app/logs && echo 'Permissions OK' || {
        echo 'Permission issue detected, attempting to fix...'
        exit 1
    }
" || {
    echo "Fixing permissions by recreating directories in container..."
    docker-compose -f docker-compose.prod.yml down
    sudo chown -R 1000:1000 data logs
    docker-compose -f docker-compose.prod.yml up -d
}

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

echo "✅ Deployment complete!"
echo "📋 Check status: docker-compose logs -f"
