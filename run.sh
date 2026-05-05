#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  IOT Robot — Run Script
# ═══════════════════════════════════════════════════════════════════
# Usage:  ./run.sh
# ═══════════════════════════════════════════════════════════════════

cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "🤖 Starting IOT Robot (Manual Control)..."
echo "   Dashboard: http://$(hostname -I | awk '{print $1}'):5000"
echo "   Press Ctrl+C to stop."
echo ""

python3 main.py
