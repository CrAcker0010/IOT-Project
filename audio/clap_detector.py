"""
clap_detector.py
================
Detects clap patterns using the D0 (Digital Out) pin of a
KY-037/KY-038 Sound Sensor Module connected to the Raspberry Pi.

Clap patterns:
  1 clap  → Emergency stop
  2 claps → Toggle autonomous mode on/off
  3 claps → Start/stop rescue mode
  4 claps → Start/stop search mode

The potentiometer on the module must be adjusted so that
D0 goes LOW on a clap and stays HIGH when quiet.
"""

import time
import threading
import RPi.GPIO as GPIO
from utils.config import PINS
from utils.logger import get_logger

logger = get_logger("ClapDetector")

# ── Timing constants ──────────────────────────────────────────────
CLAP_WINDOW       = 1.2    # Max seconds to wait for additional claps
CLAP_DEBOUNCE     = 0.15   # Ignore signals shorter than this apart (noise filter)
MAX_CLAPS         = 4      # Maximum claps in a pattern


class ClapDetector:
    """
    Monitors the sound sensor D0 pin and counts clap patterns.
    On pattern completion, calls a callback with the clap count.
    """

    def __init__(self, callback=None):
        """
        Args:
            callback : function(clap_count: int) — called when a pattern is detected.
        """
        self.pin      = PINS.get("MIC_PIN", 8)
        self.callback = callback
        self.running  = False
        self.thread   = None

        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        logger.info(f"ClapDetector initialized on GPIO {self.pin}.")

    def _wait_for_clap(self, timeout: float) -> bool:
        """Block until D0 goes LOW (clap detected) or timeout expires."""
        start = time.time()
        while time.time() - start < timeout:
            if GPIO.input(self.pin) == 0:   # D0 goes LOW on sound
                return True
            time.sleep(0.01)
        return False

    def _count_pattern(self) -> int:
        """
        After the first clap is detected, wait for additional claps
        within CLAP_WINDOW. Returns the total clap count (1–4).
        """
        count = 1
        last_clap_time = time.time()

        while count < MAX_CLAPS:
            remaining = CLAP_WINDOW - (time.time() - last_clap_time)
            if remaining <= 0:
                break

            # Wait for the pin to go back HIGH (clap ended)
            while GPIO.input(self.pin) == 0 and time.time() - last_clap_time < CLAP_WINDOW:
                time.sleep(0.01)

            # Debounce — wait a short moment
            time.sleep(CLAP_DEBOUNCE)

            # Wait for next clap
            if self._wait_for_clap(remaining):
                count += 1
                last_clap_time = time.time()
                logger.debug(f"Clap #{count} detected.")
            else:
                break

        return count

    def _listen_loop(self):
        """Main detection loop — runs in a background thread."""
        logger.info("ClapDetector listening for claps...")
        while self.running:
            try:
                # Block until first clap
                if GPIO.input(self.pin) == 0:
                    # Debounce
                    time.sleep(CLAP_DEBOUNCE)
                    if GPIO.input(self.pin) == 0 or True:   # Proceed even if brief
                        clap_count = self._count_pattern()
                        logger.info(f"Clap pattern detected: {clap_count} clap(s)")
                        if self.callback:
                            self.callback(clap_count)
                time.sleep(0.02)  # Poll interval
            except Exception as e:
                logger.error(f"ClapDetector error: {e}")
                time.sleep(1)

    # ── Public API ────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread  = threading.Thread(target=self._listen_loop, daemon=True)
        self.thread.start()
        logger.info("ClapDetector started.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("ClapDetector stopped.")
