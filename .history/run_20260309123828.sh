#!/bin/bash

echo "🚀 BunchaTV M3U Service"
echo "======================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker không được cài đặt"
    exit 1
fi

IMAGE_NAME="bunchatv-m3u"
CONTAINER_NAME="bunchatv-m3u-service"

# Stop container cũ nếu có
echo "🛑 Dừng container cũ (nếu có)..."
docker stop $CONTAINER_NAME 2>/dev/null
docker rm $CONTAINER_NAME 2>/dev/null

# Tạo file M3U nếu chưa có
if [ ! -f "bunchatv_streams.m3u" ]; then
    echo "📝 Tạo file M3U..."
    touch bunchatv_streams.m3u
fi

echo "📦 Building Docker image..."
docker build -t $IMAGE_NAME .

echo ""
echo "🚀 Chạy service..."
docker run -d \
  --name $CONTAINER_NAME \
  -p 8080:8080 \
  -e PYTHONUNBUFFERED=1 \
  -v "$(pwd)/bunchatv_streams.m3u:/app/bunchatv_streams.m3u" \
  $IMAGE_NAME

echo ""
echo "✓ Service đã chạy!"
echo ""
echo "📱 Endpoints:"
echo "  - Web: http://localhost:8080/"
echo "  - Raw M3U: http://localhost:8080/raw"
echo "  - Download: http://localhost:8080/download"
echo "  - Health: http://localhost:8080/health"
echo ""
echo "📊 Xem logs: docker logs -f $CONTAINER_NAME"
echo "🛑 Stop: docker stop $CONTAINER_NAME"
