#!/bin/bash
# Start Cortex Orchestrator Backend

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting Cortex Orchestrator..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -e .
else
    source venv/bin/activate
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env file with your settings"
fi

# Check if database is accessible
echo "🔍 Checking database connection..."
python -c "from orchestrator.config import settings; print(f'Database URL: {settings.database_url}')" || {
    echo "❌ Failed to load configuration"
    exit 1
}

# Start the application
echo "✅ Starting orchestrator on http://0.0.0.0:${API_PORT:-8004}"
echo "   (Upstream nginx handles SSL offload)"
echo ""
echo "📊 Logs will appear below. Press Ctrl+C to stop."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Run the application
python -m orchestrator.main
