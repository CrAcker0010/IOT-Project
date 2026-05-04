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

# Check for Gemini API key
if [ -z "$GEMINI_API_KEY" ] || [ "$GEMINI_API_KEY" = "YOUR_API_KEY_HERE" ]; then
    echo "⚠  GEMINI_API_KEY not set. AI features will be disabled."
    echo "   Set it with: export GEMINI_API_KEY=\"your-key-here\""
    echo ""
fi

echo "🤖 Starting IOT Robot..."
echo "   Dashboard: http://$(hostname -I | awk '{print $1}'):5000"
echo "   Press Ctrl+C to stop."
echo ""

python3 main.py
