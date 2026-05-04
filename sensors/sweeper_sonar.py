"""
sweeper_sonar.py
================
A single HC-SR04 ultrasonic sensor mounted on the Pan-Tilt servo.

Instead of having separate left/center/right sensors, this module
physically rotates the servo to each angle, takes a distance reading,
then returns the servo to center.

Pan angles used:
  LEFT   → 50°  (adjust if needed)
  CENTER → 90°  (straight ahead)
  RIGHT  → 130° (adjust if needed)

Usage:
    from sensors.sweeper_sonar import SweeperSonar

    sonar = SweeperSonar(sensor, servos)

    # Quick single read (servo stays at current position)
    dist = sonar.read_front()

    # Full 3-direction sweep — returns dict
    scan = sonar.sweep()
    # → {"left": 45.2, "front": 120.0, "right": 30.5}

    # Non-blocking background sweep (updates sonar.last_scan continuously)
    sonar.start_continuous_sweep()
    ...
    data = sonar.last_scan
    sonar.stop_continuous_sweep()
"""

import time
import threading
from utils.logger import get_logger

logger = get_logger("SweeperSonar")

# Pan angles (degrees) for each direction — tune to your servo bracket
PAN_LEFT   = 50    # servo pans to look left
PAN_CENTER = 90    # servo faces straight ahead
PAN_RIGHT  = 130   # servo pans to look right

# Tilt angle — keep sensor level with the ground
TILT_SCAN  = 90

# Seconds to let the servo physically settle before measuring
SERVO_SETTLE_TIME = 0.15

# Continuous sweep interval (seconds between full sweeps)
SWEEP_INTERVAL = 0.4


class SweeperSonar:
    """
    Controls a single HC-SR04 mounted on the Pan-Tilt servo bracket.
    Sweeps left → center → right to simulate 3 independent sensors.
    """

    def __init__(self, sensor, servos):
        """
        Args:
            sensor  : UltrasonicSensor instance (the single HC-SR04)
            servos  : ServoController instance (pan + tilt)
        """
        self.sensor = sensor
        self.servos = servos
        self._lock   = threading.Lock()
        self._running = False
        self._thread  = None

        # Always-available scan result — updated by continuous sweep
        self.last_scan = {"left": 999.0, "front": 999.0, "right": 999.0}

        # Center on init
        self._pan(PAN_CENTER)
        logger.info("SweeperSonar initialized.")

    # ── Low-level helpers ─────────────────────────────────────────
    def _pan(self, angle: int):
        """Move the pan servo and wait for it to settle."""
        self.servos.set_pan(angle)
        time.sleep(SERVO_SETTLE_TIME)

    def _read(self) -> float:
        """Take a distance reading; return -1 on timeout."""
        return self.sensor.get_distance()

    # ── Single direction reads ────────────────────────────────────
    def read_front(self) -> float:
        """Pan to center and return the distance in cm."""
        with self._lock:
            self._pan(PAN_CENTER)
            return self._read()

    def read_left(self) -> float:
        """Pan to left and return the distance in cm."""
        with self._lock:
            self._pan(PAN_LEFT)
            dist = self._read()
            self._pan(PAN_CENTER)   # return to center
            return dist

    def read_right(self) -> float:
        """Pan to right and return the distance in cm."""
        with self._lock:
            self._pan(PAN_RIGHT)
            dist = self._read()
            self._pan(PAN_CENTER)   # return to center
            return dist

    # ── Full sweep ────────────────────────────────────────────────
    def sweep(self) -> dict:
        """
        Physically sweep left → center → right and collect all 3 readings.

        Returns:
            {"left": float, "front": float, "right": float}
            Distances are in cm. -1 means the reading timed out.
        """
        with self._lock:
            # LEFT
            self._pan(PAN_LEFT)
            left = self._read()

            # CENTER (front)
            self._pan(PAN_CENTER)
            front = self._read()

            # RIGHT
            self._pan(PAN_RIGHT)
            right = self._read()

            # Return to center
            self._pan(PAN_CENTER)

        scan = {"left": left, "front": front, "right": right}
        self.last_scan = scan
        logger.debug(f"Sweep: L={left}cm F={front}cm R={right}cm")
        return scan

    # ── Continuous background sweep ───────────────────────────────
    def _sweep_worker(self):
        logger.info("SweeperSonar continuous sweep started.")
        while self._running:
            try:
                self.sweep()
            except Exception as e:
                logger.error(f"Sweep error: {e}")
            time.sleep(SWEEP_INTERVAL)

    def start_continuous_sweep(self):
        """
        Start sweeping in a background thread.
        Access results via self.last_scan at any time.
        """
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._sweep_worker, daemon=True
        )
        self._thread.start()
        logger.info("Continuous sweep started.")

    def stop_continuous_sweep(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        self._pan(PAN_CENTER)
        logger.info("Continuous sweep stopped.")

    def cleanup(self):
        self.stop_continuous_sweep()
        self._pan(PAN_CENTER)
