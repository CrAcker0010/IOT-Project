#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  IOT Robot — One-shot Setup Script (run on Raspberry Pi)
# ═══════════════════════════════════════════════════════════════════
# Usage:  chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  IOT ROBOT — Raspberry Pi Setup"
echo "═══════════════════════════════════════════════════════════"

# ── 1. System packages ────────────────────────────────────────────
echo "[1/5] Installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y \
    python3-pip python3-venv python3-dev \
    python3-smbus i2c-tools \
    libopencv-dev python3-opencv \
    espeak espeak-ng \
    libatlas-base-dev

# ── 2. Enable I2C and Camera ─────────────────────────────────────
echo "[2/5] Enabling I2C and Camera interfaces..."
sudo raspi-config nonint do_i2c 0       2>/dev/null || true
sudo raspi-config nonint do_camera 0    2>/dev/null || true

# ── 3. Python virtual environment ────────────────────────────────
echo "[3/5] Setting up Python virtual environment..."
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages
fi
source venv/bin/activate

# ── 4. Python dependencies ───────────────────────────────────────
echo "[4/5] Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# ── 5. Create logs directory ─────────────────────────────────────
echo "[5/5] Creating logs directory..."
mkdir -p logs

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  Before running, set your Gemini API key:"
echo "    export GEMINI_API_KEY=\"your-key-here\""
echo ""
echo "  Then start the robot:"
echo "    source venv/bin/activate"
echo "    python3 main.py"
echo ""
echo "  Or use the run script:"
echo "    ./run.sh"
echo ""
echo "  Dashboard will be at:  http://<Pi-IP>:5000"
echo "═══════════════════════════════════════════════════════════"
