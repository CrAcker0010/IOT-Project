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

        if not r or not hasattr(r, 'motors'):
            return

        speed = 50
        if clap_count == 1:
            r.motors.stop()
            logger.info("1 clap: STOP")
            if hasattr(r, 'lcd') and r.lcd: r.lcd.show_text("STOP", "Clap Control")
        elif clap_count == 2:
            r.motors.forward(speed)
            logger.info("2 claps: FORWARD")
            if hasattr(r, 'lcd') and r.lcd: r.lcd.show_text("FORWARD", "Clap Control")
        elif clap_count == 3:
            r.motors.backward(speed)
            logger.info("3 claps: BACKWARD")
            if hasattr(r, 'lcd') and r.lcd: r.lcd.show_text("BACKWARD", "Clap Control")
        elif clap_count == 4:
            r.motors.left(speed)
            logger.info("4 claps: LEFT")
            if hasattr(r, 'lcd') and r.lcd: r.lcd.show_text("LEFT", "Clap Control")
        elif clap_count == 5:
            r.motors.right(speed)
            logger.info("5 claps: RIGHT")
            if hasattr(r, 'lcd') and r.lcd: r.lcd.show_text("RIGHT", "Clap Control")

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
