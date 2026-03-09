#!/bin/bash

echo "🚀 BunchaTV M3U Service"
echo "======================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker không được cài đặt"
    exit 1
fi

echo "📦 Building Docker image..."
docker-compose build

echo ""
echo "🚀 Chạy service..."
docker-compose up -d

echo ""
echo "✓ Service đã chạy!"
echo ""
echo "📱 Endpoints:"
echo "  - Raw M3U: http://localhost:8080/raw"
echo "  - Download: http://localhost:8080/download"
echo "  - Health: http://localhost:8080/health"
echo ""
echo "📊 Xem logs: docker-compose logs -f"
echo "🛑 Stop: docker-compose down"
