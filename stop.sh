#!/bin/bash
# Stop Cortex Orchestrator Backend

echo "🛑 Stopping Cortex Orchestrator..."

# Find the process
PIDS=$(pgrep -f "orchestrator.main" || true)

if [ -z "$PIDS" ]; then
    echo "ℹ️  Orchestrator is not running"
    exit 0
fi

# Stop gracefully
echo "📋 Found process(es): $PIDS"
for PID in $PIDS; do
    echo "   Stopping PID $PID..."
    kill -TERM "$PID" 2>/dev/null || true
done

# Wait for graceful shutdown
sleep 2

# Check if still running
REMAINING=$(pgrep -f "orchestrator.main" || true)
if [ -n "$REMAINING" ]; then
    echo "⚠️  Process still running, forcing shutdown..."
    kill -9 $REMAINING 2>/dev/null || true
fi

echo "✅ Orchestrator stopped"
