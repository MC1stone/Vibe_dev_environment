#!/bin/bash

# Simple test script to verify .env file is working

echo "📁 Current directory: $(pwd)"
echo "📁 Files in current directory:"
ls -la | grep -E "(\.env|docker-compose)"

echo ""
echo "🔍 Checking for .env file..."
if [ -f ".env" ]; then
    echo "✅ .env file exists"
    echo "📄 .env file size: $(wc -c < .env) bytes"
    echo "📄 .env file lines: $(wc -l < .env) lines"
    echo ""
    echo "🔍 Loading .env file..."
    set -o allexport
    source .env
    set +o allexport
    echo "✅ .env file loaded"
    echo ""
    echo "📋 Environment variables from .env:"
    echo "   DJANGO_SECRET_KEY: ${DJANGO_SECRET_KEY:-NOT_SET}"
    echo "   POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-NOT_SET}"
    echo "   DATABASE_URL: ${DATABASE_URL:-NOT_SET}"
else
    echo "❌ .env file not found"
    echo "💡 Available .env files:"
    ls -la .env* 2>/dev/null || echo "   No .env* files found"
fi