"""
voice_brain.py
==============
Clap-based emergency stop.

Clap patterns:
  1 clap  → Emergency stop (motors off)
  2 claps → Log sensor readings to LCD

All driving is done from the web dashboard (manual control).
"""

from audio.clap_detector import ClapDetector
from utils.logger import get_logger

logger = get_logger("VoiceBrain")


class VoiceBrain:

    def __init__(self, robot=None):
        self.robot   = robot
        self.running = False
        self.clap_detector = ClapDetector(callback=self._on_clap)

    # ── Clap handler ──────────────────────────────────────────────
    def _on_clap(self, clap_count: int):
        logger.info(f"Clap pattern received: {clap_count} clap(s)")
        r = self.robot

        if clap_count == 1:
            # Emergency stop
            if r:
                r.motors.stop()
            logger.info("Emergency stop triggered by clap.")
            if r and hasattr(r, 'lcd'):
                r.lcd.show_voice_command("1 clap: STOP")

        elif clap_count >= 2:
            # Log sensor distances to LCD
            if r:
                front = r.us_front.get_distance()
                back  = r.us_back.get_distance()
                logger.info(f"Sensors — Front: {front}cm, Back: {back}cm")
                if hasattr(r, 'lcd'):
                    r.lcd.show_sensor_data(front=front)

    # ── Public API ────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.clap_detector.start()
        logger.info("VoiceBrain started (clap input only).")

    def stop(self):
        self.running = False
        self.clap_detector.stop()
        logger.info("VoiceBrain stopped.")
