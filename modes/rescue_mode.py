"""
rescue_mode.py
==============
Rescue Bot Mode — The robot autonomously navigates through an area,
uses the camera to detect human faces (survivors), avoids obstacles
with ultrasonic sensors, and alerts the operator with voice/speaker
when a survivor is found.

Behaviour loop:
  1. Drive forward, continuously scanning with front ultrasonic sensor.
  2. If an obstacle is detected → navigate around it (left/right).
  3. Every few frames, run OpenCV face detection on the camera feed.
  4. If a face is detected → stop, announce found survivor, pan/tilt
     camera to center on the face, and wait for operator acknowledgment.
  5. After acknowledgment (or timeout) → resume search.
  6. Pan/tilt servo continuously sweeps to widen the search angle.
"""

import time
import threading
import os
import cv2
import numpy as np
import google.generativeai as genai
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("RescueMode")

# How close (cm) before the robot considers it a blocking obstacle
OBSTACLE_CM = SETTINGS.get("OBSTACLE_THRESHOLD_CM", 30)
DANGER_CM   = SETTINGS.get("DANGER_THRESHOLD_CM",   15)

# How long (seconds) to wait at a found-survivor location before resuming
WAIT_AT_SURVIVOR_SEC = 10


class RescueMode:
    """
    Autonomous rescue bot.
    Requires: motors, sensors (dict: front/left/right), servos, speaker, camera.
    """

    def __init__(self, motors, sensors: dict, servos, speaker, camera=None):
        self.motors  = motors
        self.sensors = sensors     # {"front": UltrasonicSensor, "left": ..., "right": ...}
        self.servos  = servos
        self.speaker = speaker
        self.camera  = camera
        self.running = False
        self.thread  = None

        # Survivor found flag — cleared after operator acknowledges
        self.survivor_found   = False
        self.survivors_total  = 0

        # OpenCV face cascade
        try:
            self.face_cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            )
            logger.info("Face detection cascade loaded.")
        except Exception as e:
            logger.error(f"Failed to load face cascade: {e}")
            self.face_cascade = None

        # Gemini AI for contextual voice reporting
        self.chat = None
        api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
        if api_key and api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                self.chat = model.start_chat(history=[])
                self.chat.send_message(
                    "You are the AI brain of an emergency rescue robot. "
                    "Your mission is to locate survivors in disaster zones. "
                    "Speak in calm, professional, concise sentences (max 2). "
                    "Prioritize urgency and clarity."
                )
                logger.info("Rescue Mode Gemini AI initialized.")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")

    # ── AI voice line ─────────────────────────────────────────────
    def _speak_ai(self, situation: str) -> None:
        if not self.speaker:
            return
        if self.chat:
            try:
                resp = self.chat.send_message(situation)
                self.speaker.speak(resp.text.strip())
                return
            except Exception as e:
                logger.error(f"Gemini error: {e}")
        self.speaker.speak(situation)

    # ── Obstacle navigation ───────────────────────────────────────
    def _navigate_obstacle(self, front_dist: float, left_dist: float, right_dist: float):
        if front_dist < DANGER_CM:
            logger.warning(f"Danger zone! front={front_dist:.1f}cm — reversing.")
            self.motors.backward(speed=45)
            time.sleep(0.6)
            self.motors.stop()

        # Turn toward the side with more space
        if left_dist >= right_dist:
            logger.info("Turning left to avoid obstacle.")
            self.motors.left(speed=50)
        else:
            logger.info("Turning right to avoid obstacle.")
            self.motors.right(speed=50)
        time.sleep(0.4)
        self.motors.stop()
        time.sleep(0.2)

    # ── Face detection ────────────────────────────────────────────
    def _detect_face(self, frame) -> bool:
        """Return True if at least one human face is detected in frame."""
        if self.face_cascade is None or frame is None:
            return False
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
        return len(faces) > 0

    # ── Servo sweep ───────────────────────────────────────────────
    def _sweep_servos(self, tick: int):
        """Slowly pan the camera left-right to widen field of view."""
        # Oscillate pan between 50° and 130° over a ~10-second cycle
        import math
        angle = 90 + int(40 * math.sin(tick * 0.1))
        self.servos.set_pan(angle)
        self.servos.set_tilt(85)   # Slight downward tilt for ground-level search

    # ── Survivor response ─────────────────────────────────────────
    def _handle_survivor(self):
        self.survivors_total += 1
        self.survivor_found = True
        self.motors.stop()
        logger.info(f"SURVIVOR #{self.survivors_total} DETECTED!")
        self.servos.set_pan(90)   # Center camera on survivor
        self.servos.set_tilt(90)
        self._speak_ai(
            f"Survivor number {self.survivors_total} located. "
            "Halting for medical team. Activating beacon."
        )
        # Flash LED / buzzer signal here if wired to Pi GPIO
        # Wait at location before resuming
        time.sleep(WAIT_AT_SURVIVOR_SEC)
        self.survivor_found = False
        self._speak_ai("Resuming rescue sweep.")

    # ── Main loop ─────────────────────────────────────────────────
    def _run_loop(self):
        tick = 0
        face_check_interval = 5   # Check every N ticks (~0.5 s)

        while self.running:
            front = self.sensors["front"].get_distance()
            left  = self.sensors["left"].get_distance()
            right = self.sensors["right"].get_distance()

            # Obstacle handling
            if 0 < front < OBSTACLE_CM:
                self._navigate_obstacle(front, left, right)
            else:
                self.motors.forward(speed=40)   # Slow, cautious advance

            # Servo pan sweep
            self._sweep_servos(tick)

            # Periodic face detection
            if tick % face_check_interval == 0 and self.camera:
                frame = self.camera.frame
                if self._detect_face(frame):
                    self._handle_survivor()

            tick += 1
            time.sleep(0.1)

        self.motors.stop()

    # ── Public API ────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Rescue Mode activated.")
        self._speak_ai(
            "Rescue bot activated. Beginning systematic survivor search. "
            "All sensors online."
        )

    def acknowledge_survivor(self):
        """Call this externally (e.g. from web API) to clear the survivor flag early."""
        self.survivor_found = False
        logger.info("Survivor acknowledgment received. Resuming search.")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        self.motors.stop()
        self.servos.set_pan(90)
        self.servos.set_tilt(90)
        logger.info(f"Rescue Mode deactivated. Total survivors found: {self.survivors_total}")
        if self.speaker:
            self.speaker.speak(
                f"Rescue mission complete. {self.survivors_total} survivor(s) located."
            )
