"""
autonomous_mode.py
==================
Obstacle-avoidance navigation using a single HC-SR04 mounted on
the Pan-Tilt servo (SweeperSonar).

Behaviour:
  1. The SweeperSonar continuously sweeps left → front → right.
  2. If the front reading is in the DANGER zone  → reverse + decide.
  3. If the front reading is in the WARNING zone → slow steer.
  4. Otherwise                                   → drive forward.

Turning decision is always based on which side has MORE clearance
from the latest sweep — no separate left/right sensors needed.
"""

import time
import threading
import os
import google.generativeai as genai
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("AutonomousMode")

DANGER_CM   = SETTINGS.get("DANGER_THRESHOLD_CM",   15)
OBSTACLE_CM = SETTINGS.get("OBSTACLE_THRESHOLD_CM", 30)


class AutonomousMode:
    """
    Autonomous driving using a single sweeping ultrasonic sensor (Front),
    a fixed Back sensor, and a fixed Down sensor for cliff detection.
    """

    def __init__(self, motors, sonar, us_back, us_down, speaker=None):
        self.motors  = motors
        self.sonar   = sonar       # SweeperSonar instance
        self.us_back = us_back     # UltrasonicSensor instance
        self.us_down = us_down     # UltrasonicSensor instance
        self.speaker = speaker
        self.running = False
        self.thread  = None

        # ── Gemini navigation commentary ────────────────────────
        self.chat = None
        api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
        if api_key and api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                self.chat = model.start_chat(history=[])
                self.chat.send_message(
                    "You are the intelligent navigation computer of an autonomous car. "
                    "You process sensor data to make quick, logical driving decisions. "
                    "Keep your responses extremely short, technical, and precise. "
                    "Maximum 1 sentence."
                )
                logger.info("Autonomous Mode Gemini initialized.")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")

    # ── AI commentary (optional) ──────────────────────────────────
    def _ai_comment(self, context: str) -> str:
        if not self.chat:
            return ""
        try:
            return self.chat.send_message(context).text.strip()
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            return ""

    # ── Core decision logic ───────────────────────────────────────
    def _decide(self, scan: dict):
        """
        Given a sweep scan dict {left, front, right}, execute
        the appropriate motor command.
        """
        # ── CLIFF DETECTION (Priority 1) ─────────────────────────
        down_dist = self.us_down.get_distance()
        # If distance to floor is > 20cm, we are at a cliff or stairs
        if down_dist > 20 or down_dist < 0:
            logger.error(f"CLIFF DETECTED! Down distance: {down_dist}cm. Stopping.")
            self.motors.stop()
            if self.speaker:
                self.speaker.speak("Cliff detected! Halting for safety.")
            return

        front = scan["front"]
        left  = scan["left"]
        right = scan["right"]

        # Values of -1 mean sensor timed out — treat as very close
        if front < 0: front = 0
        if left  < 0: left  = 0
        if right < 0: right = 0

        # ── DANGER: obstacle extremely close ──────────────────────
        if 0 < front < DANGER_CM:
            logger.warning(f"DANGER! Front={front}cm. Reversing.")
            
            # Check back before reversing
            back_dist = self.us_back.get_distance()
            if back_dist > 15 or back_dist < 0:
                self.motors.backward(speed=50)
                time.sleep(0.5)
            else:
                logger.warning("Cannot reverse! Path blocked.")
            
            self.motors.stop()

            # After reversing, turn toward the clearer side
            if left >= right:
                logger.info("Turning LEFT (more clearance).")
                self.motors.left(speed=60)
            else:
                logger.info("Turning RIGHT (more clearance).")
                self.motors.right(speed=60)
            time.sleep(0.4)
            self.motors.stop()

            if self.speaker:
                self.speaker.speak(
                    self._ai_comment(
                        f"Critical obstacle front at {front}cm. "
                        f"Left clearance: {left}cm. Right: {right}cm. "
                        "Evasive maneuver executed."
                    )
                )

        # ── WARNING: obstacle ahead, steer gently ─────────────────
        elif 0 < front < OBSTACLE_CM:
            logger.info(f"Obstacle ahead at {front}cm. Steering.")
            if left >= right:
                self.motors.left(speed=50)
            else:
                self.motors.right(speed=50)
            time.sleep(0.25)
            self.motors.stop()

        # ── CLEAR: drive forward ──────────────────────────────────
        else:
            self.motors.forward(speed=SETTINGS.get("MOTOR_SPEED_DEFAULT", 50))

    # ── Main loop ─────────────────────────────────────────────────
    def _run_loop(self):
        commentary_tick = 0

        while self.running:
            # Get the latest sweep result
            # We call sweep() directly here so each loop tick triggers
            # a fresh physical measurement. The servo sweeps L→C→R
            # every loop iteration (~0.5 seconds per full sweep).
            scan = self.sonar.sweep()
            self._decide(scan)

            # Every ~30 loops (~15 sec), ask Gemini to comment
            commentary_tick += 1
            if commentary_tick >= 30 and self.speaker:
                commentary_tick = 0
                f, l, r = scan["front"], scan["left"], scan["right"]
                comment = self._ai_comment(
                    f"Route update — Front: {f}cm, Left: {l}cm, Right: {r}cm."
                )
                if comment:
                    self.speaker.speak(comment)

    # ── Public API ────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread  = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Autonomous mode started.")
        if self.speaker:
            self.speaker.speak(
                self._ai_comment(
                    "Starting engine. Beginning autonomous route computation."
                ) or "Autonomous mode activated."
            )

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        self.motors.stop()
        logger.info("Autonomous mode stopped.")
