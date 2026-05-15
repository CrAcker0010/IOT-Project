#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  IOT Robot — Run Script
#  Target: Raspberry Pi 4  ·  1 GB RAM  ·  32-bit OS
# ═══════════════════════════════════════════════════════════════════
# Usage:  ./run.sh
# ═══════════════════════════════════════════════════════════════════

cd "$(dirname "$0")"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# ── Memory optimisation env vars (1 GB RAM) ──────────────────────
export MALLOC_TRIM_THRESHOLD_=65536   # Return free memory to OS sooner
export PYTHONDONTWRITEBYTECODE=1      # Skip .pyc files (saves disk I/O)
export OPENBLAS_NUM_THREADS=1         # Limit numpy/OpenBLAS to 1 thread
export OMP_NUM_THREADS=1              # Limit OpenMP to 1 thread
export OPENCV_VIDEOIO_PRIORITY_V4L2=1 # Force V4L2 (lightest camera backend)

echo "🤖 Starting IOT Robot (Manual Control)..."
echo "   Dashboard: http://$(hostname -I | awk '{print $1}'):5000"
echo "   Memory: $(free -m | awk '/Mem:/{printf "%dMB free / %dMB total", $4, $2}')"
echo "   Press Ctrl+C to stop."
echo ""

python3 main.py
