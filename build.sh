#!/usr/bin/env sh

#!/bin/bash
# build.sh

echo "🐳 Building Kayak Trip Planner Docker container..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Copy .env.template and fill in your values."
    exit 1
fi

# Build the image
docker build -t kayak-trip-planner:latest .

echo "✅ Build complete!"
echo "🚀 To run: docker-compose up -d"
