#!/bin/bash

# Script to fix Docker build issues with missing static directory

echo "🔧 Fixing Docker build issues..."

# Create static directory if it doesn't exist
if [ ! -d "static" ]; then
    echo "📁 Creating static directory..."
    mkdir -p static
fi

# Create other required directories
for dir in media logs reports uploads data; do
    if [ ! -d "$dir" ]; then
        echo "📁 Creating $dir directory..."
        mkdir -p "$dir"
    fi
done

# Check if Docker is available
if command -v docker &> /dev/null; then
    echo "🐳 Docker is available"
    
    # Clean up any previous builds
    echo "🧹 Cleaning up previous builds..."
    docker-compose down 2>/dev/null || true
    docker system prune -f 2>/dev/null || true
    
    # Rebuild with no cache
    echo "🔨 Rebuilding Docker containers..."
    docker-compose build --no-cache
    
    # Start services
    echo "🚀 Starting services..."
    docker-compose up -d
    
    # Check status
    echo "📊 Service status:"
    docker-compose ps
else
    echo "❌ Docker is not available in this environment"
    echo "Please run this script on a machine with Docker installed"
fi

echo "✅ Fix script completed"