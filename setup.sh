#!/bin/bash
# ═══════════════════════════════════════════════════════════════════
#  IOT Robot — One-shot Setup Script (run on Raspberry Pi)
#  Target: Raspberry Pi 4  ·  1 GB RAM  ·  32-bit OS (armv7l)
# ═══════════════════════════════════════════════════════════════════
# Usage:  chmod +x setup.sh && ./setup.sh
# ═══════════════════════════════════════════════════════════════════

set -e

echo "═══════════════════════════════════════════════════════════"
echo "  IOT ROBOT — Raspberry Pi 4 (1 GB / 32-bit) Setup"
echo "═══════════════════════════════════════════════════════════"

# ── 0. Swap file (critical for 1 GB RAM) ─────────────────────────
echo "[0/6] Configuring swap for low-memory system..."
SWAP_SIZE=1024   # 1 GB swap

CURRENT_SWAP=$(free -m | awk '/Swap:/{print $2}')
if [ "$CURRENT_SWAP" -lt "$SWAP_SIZE" ]; then
    echo "  Increasing swap to ${SWAP_SIZE}MB..."
    sudo dphys-swapfile swapoff 2>/dev/null || true
    sudo sed -i "s/^CONF_SWAPSIZE=.*/CONF_SWAPSIZE=${SWAP_SIZE}/" /etc/dphys-swapfile
    sudo dphys-swapfile setup
    sudo dphys-swapfile swapon
    echo "  Swap set to ${SWAP_SIZE}MB."
else
    echo "  Swap already >= ${SWAP_SIZE}MB. Skipping."
fi

# ── 1. System packages ────────────────────────────────────────────
echo "[1/6] Installing system dependencies..."
sudo apt-get update -y
sudo apt-get install -y \
    python3-pip python3-venv python3-dev \
    python3-smbus i2c-tools \
    libatlas-base-dev \
    libjpeg-dev zlib1g-dev libpng-dev \
    libopenjp2-7 libtiff5 \
    libasound-dev portaudio19-dev

# ── OpenCV headless runtime dependencies (32-bit Bullseye/Bookworm)
sudo apt-get install -y \
    libavcodec58 libavformat58 libswscale5 libavutil56 \
    libswresample3 libhdf5-dev \
    2>/dev/null || echo "  (Some codec packages may differ on your OS version — OK)"

# ── 2. Enable I2C and Camera ─────────────────────────────────────
echo "[2/6] Enabling I2C and Camera interfaces..."
sudo raspi-config nonint do_i2c 0       2>/dev/null || true
sudo raspi-config nonint do_camera 0    2>/dev/null || true

# ── 3. GPU memory split (free RAM for CPU) ────────────────────────
echo "[3/6] Optimising GPU memory split for 1 GB system..."
CURRENT_GPU=$(vcgencmd get_mem gpu 2>/dev/null | grep -oP '\d+' || echo "128")
if [ "$CURRENT_GPU" -gt 64 ]; then
    if ! grep -q "^gpu_mem=" /boot/config.txt 2>/dev/null; then
        echo "gpu_mem=64" | sudo tee -a /boot/config.txt >/dev/null
    else
        sudo sed -i 's/^gpu_mem=.*/gpu_mem=64/' /boot/config.txt
    fi
    echo "  GPU memory set to 64 MB (saves RAM for Python)."
    echo "  ⚠  Reboot required for GPU memory change to take effect."
else
    echo "  GPU memory already <= 64 MB. Skipping."
fi

# ── 4. Python virtual environment ────────────────────────────────
echo "[4/6] Setting up Python virtual environment..."
cd "$(dirname "$0")"
if [ ! -d "venv" ]; then
    python3 -m venv venv --system-site-packages
fi
source venv/bin/activate

# ── 5. Python dependencies ───────────────────────────────────────
echo "[5/6] Installing Python packages (this may take a few minutes)..."
pip install --upgrade pip setuptools wheel

# Use piwheels for pre-compiled armv7l wheels (default on RPi OS)
pip install --extra-index-url https://www.piwheels.org/simple \
    -r requirements.txt

# ── 6. Create logs directory ─────────────────────────────────────
echo "[6/6] Creating logs directory..."
mkdir -p logs

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  SETUP COMPLETE!"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "  ⚠  If GPU memory was changed, REBOOT before running:"
echo "      sudo reboot"
echo ""
echo "  Start the robot:"
echo "    source venv/bin/activate"
echo "    python3 main.py"
echo ""
echo "  Or use the run script:"
echo "    ./run.sh"
echo ""
echo "  Dashboard will be at:  http://<Pi-IP>:5000"
echo "═══════════════════════════════════════════════════════════"
