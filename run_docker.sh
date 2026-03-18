#!/bin/bash
# run_docker.sh
# 
# Usage Helper:
#   ./run_docker.sh         # Builds and starts the system
#   ./run_docker.sh logs    # Follows all live logs
#   ./run_docker.sh down    # Stops and removes the containers
#   ./run_docker.sh restart # Restarts the system
# ------------------------------------------------------------------

CMD=$1

if [ "$CMD" == "logs" ]; then
    echo "📖 Showing live logs (Press Ctrl+C to exit)..."
    docker-compose logs -f
    exit 0
elif [ "$CMD" == "down" ]; then
    echo "🛑 Stopping PalmX system..."
    docker-compose down
    exit 0
elif [ "$CMD" == "restart" ]; then
    echo "🔄 Restarting PalmX system..."
    docker-compose restart
    exit 0
elif [ -n "$CMD" ]; then
    echo "Unknown command: $CMD"
    echo "Usage: ./run_docker.sh [logs|down|restart]"
    exit 1
fi

echo "🚀 Starting PalmX system via Docker Compose..."

if docker-compose up --build -d; then
    echo ""
    echo "✅ PalmX System is ready!"
    echo "--------------------------------"
    echo "   Chat Interface:  http://localhost:3000"
    echo "   Backend API:     http://localhost:8000"
    echo "   Admin Dashboard: http://localhost:3000/dashboard"
    echo "--------------------------------"
    echo ""
    echo "👉 Useful Hub Commands:"
    echo "   View Logs:   ./run_docker.sh logs"
    echo "   Stop System: ./run_docker.sh down"
    echo "   Restart:     ./run_docker.sh restart"
else
    echo ""
    echo "❌ Failed to start PalmX containers. Please ensure Docker is running and ports 3000/8000 are free."
    exit 1
fi
