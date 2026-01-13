#!/bin/bash

echo "🚀 Starting Zakerly Platform..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p uploads logs

# Start infrastructure services first (database, redis, monitoring)
echo "🗄️  Starting infrastructure services..."
docker compose up -d postgres redis prometheus grafana pgadmin

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 30

# Check if database is ready
echo "🔍 Checking database connection..."
until docker compose exec postgres pg_isready -U zakerly_user -d zakerly_db; do
    echo "Waiting for database..."
    sleep 5
done

echo "✅ Database is ready!"

# Build and start application services
echo "🏗️  Building and starting application services..."
docker compose up -d --build ingestion-service chat-service api-gateway

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 20

# Start frontend
echo "🎨 Starting frontend..."
docker compose up -d frontend

# Display status
echo ""
echo "🎉 Zakerly Platform Status:"
echo ""
docker compose ps

echo ""
echo "📱 Access Points:"
echo "   Frontend:     http://localhost:3000"
echo "   API Gateway:  http://localhost:8000"
echo "   pgAdmin:      http://localhost:8080 (admin@zakerly.com / admin123)"
echo "   Prometheus:   http://localhost:9090"
echo "   Grafana:      http://localhost:3001 (admin / admin123)"
echo ""
echo "🔧 Management Commands:"
echo "   View logs:    docker compose logs -f [service-name]"
echo "   Stop all:     docker compose down"
echo "   Restart:      docker compose restart [service-name]"
echo ""

echo "✨ Zakerly is now running! Open http://localhost:3000 to get started!"