"""
search_mode.py
==============
Searching Bot Mode — The robot accepts a target object/person name
from the operator (via voice or web UI), then autonomously drives
around and uses the camera + Gemini Vision AI to identify whether
the target is in view.

Behaviour loop:
  1. Operator specifies a search target (e.g. "red bag", "person in blue").
  2. Robot performs a systematic grid/spiral sweep of the area.
  3. Every N frames the current camera frame is sent to Gemini Vision.
     Gemini returns whether the target is visible and where.
  4. If target found → stop, announce location, center servos on target.
  5. If path is blocked → obstacle avoidance.
  6. Runs until target is found or operator calls stop().
"""

import time
import threading
import os
import io
import cv2
import numpy as np
import google.generativeai as genai
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("SearchMode")

OBSTACLE_CM = SETTINGS.get("OBSTACLE_THRESHOLD_CM", 30)
DANGER_CM   = SETTINGS.get("DANGER_THRESHOLD_CM",   15)

# How many loop ticks between Gemini vision checks (10 ticks ≈ 1 second)
VISION_CHECK_INTERVAL = 20   # ~2 seconds

# Sweep pattern: list of (turn_direction, duration_sec) segments
# Builds a rough expanding-square search pattern
SWEEP_PATTERN = [
    ("forward",  1.5),
    ("left",     0.5),
    ("forward",  1.5),
    ("left",     0.5),
    ("forward",  3.0),
    ("right",    0.5),
    ("forward",  3.0),
    ("right",    0.5),
    ("forward",  4.0),
    ("left",     0.5),
    ("forward",  4.0),
    ("left",     0.5),
]


class SearchMode:
    """
    Autonomous searching bot.
    Requires: motors, sensors (dict: front/left/right), servos, speaker, camera.
    """

    def __init__(self, motors, sonar, servos, speaker, camera=None):
        self.motors  = motors
        self.sonar   = sonar       # SweeperSonar
        self.servos  = servos
        self.speaker = speaker
        self.camera  = camera
        self.running = False
        self.thread  = None

        self.search_target = "any object or person of interest"
        self.target_found  = False

        # Gemini Vision model (multimodal)
        self.vision_model = None
        # Gemini Chat for voice lines
        self.chat = None

        api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
        if api_key and api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=api_key)
                # Vision: use gemini-1.5-flash (supports inline image bytes)
                self.vision_model = genai.GenerativeModel("gemini-1.5-flash")
                # Text chat for announcements
                text_model = genai.GenerativeModel("gemini-1.5-flash")
                self.chat = text_model.start_chat(history=[])
                self.chat.send_message(
                    "You are the AI system of an autonomous search robot. "
                    "Your job is to find a specific target in an unknown area. "
                    "Speak in short, confident, mission-style sentences (max 2). "
                )
                logger.info("Search Mode Gemini AI initialized.")
            except Exception as e:
                logger.error(f"Gemini init failed: {e}")

    # ── AI voice ──────────────────────────────────────────────────
    def _speak_ai(self, situation: str):
        if not self.speaker:
            return
        if self.chat:
            try:
                resp = self.chat.send_message(situation)
                self.speaker.speak(resp.text.strip())
                return
            except Exception as e:
                logger.error(f"Gemini chat error: {e}")
        self.speaker.speak(situation)

    # ── Gemini Vision: check if target is in frame ────────────────
    def _vision_check(self, frame) -> tuple[bool, str]:
        """
        Send the current camera frame to Gemini Vision.
        Returns (found: bool, description: str).
        """
        if self.vision_model is None or frame is None:
            return False, "No vision model available."
        try:
            # Encode frame as JPEG bytes, then wrap as PIL Image
            _, buf = cv2.imencode(".jpg", frame)
            image_bytes = buf.tobytes()

            from PIL import Image
            import io
            pil_image = Image.open(io.BytesIO(image_bytes))

            prompt = (
                f"The search robot is looking for: '{self.search_target}'. "
                "Look at this image and answer: "
                "1) Is the target visible? (yes/no) "
                "2) If yes, where in the frame (left/center/right, near/far)? "
                "Keep your answer under 2 sentences."
            )

            response = self.vision_model.generate_content([prompt, pil_image])
            text = response.text.strip().lower()
            found = "yes" in text
            return found, response.text.strip()

        except Exception as e:
            logger.error(f"Gemini Vision error: {e}")
            return False, "Vision check failed."

    # ── Obstacle avoidance ────────────────────────────────────────
    def _avoid_obstacle(self, front: float, left: float, right: float):
        if front < DANGER_CM:
            self.motors.backward(speed=45)
            time.sleep(0.5)
            self.motors.stop()
        if left >= right:
            self.motors.left(speed=50)
        else:
            self.motors.right(speed=50)
        time.sleep(0.35)
        self.motors.stop()
        time.sleep(0.15)

    # ── Servo scan pan ────────────────────────────────────────────
    def _scan_servos(self, tick: int):
        import math
        # Slow horizontal sweep
        pan = 90 + int(35 * math.sin(tick * 0.08))
        self.servos.set_pan(pan)
        self.servos.set_tilt(88)

    # ── Target found handler ──────────────────────────────────────
    def _handle_found(self, description: str):
        self.target_found = True
        self.motors.stop()
        self.servos.set_pan(90)
        self.servos.set_tilt(90)
        logger.info(f"TARGET FOUND! Description: {description}")
        self._speak_ai(
            f"Target '{self.search_target}' located. "
            f"{description} Halting for operator."
        )

    # ── Sweep pattern executor ────────────────────────────────────
    def _execute_sweep_step(self, step_index: int) -> int:
        """Execute one step of the sweep pattern; returns next step index."""
        direction, duration = SWEEP_PATTERN[step_index % len(SWEEP_PATTERN)]
        end_time = time.time() + duration

        while time.time() < end_time and self.running and not self.target_found:
            # Single sonar does a physical sweep each call
            scan  = self.sonar.sweep()
            front = scan["front"]
            left  = scan["left"]
            right = scan["right"]

            if 0 < front < OBSTACLE_CM and direction == "forward":
                self._avoid_obstacle(front, left, right)
                break   # Re-plan after avoidance

            if direction == "forward":
                self.motors.forward(speed=38)
            elif direction == "left":
                self.motors.left(speed=45)
            elif direction == "right":
                self.motors.right(speed=45)

            time.sleep(0.1)

        self.motors.stop()
        return (step_index + 1) % len(SWEEP_PATTERN)

    # ── Main loop ─────────────────────────────────────────────────
    def _run_loop(self):
        tick       = 0
        step_index = 0

        while self.running and not self.target_found:
            # Vision check on interval
            if tick % VISION_CHECK_INTERVAL == 0 and self.camera:
                frame = self.camera.frame
                found, description = self._vision_check(frame)
                if found:
                    self._handle_found(description)
                    break
                else:
                    logger.info(f"Vision check — target not found. ({description})")

            # Servo scan
            self._scan_servos(tick)

            # Execute sweep movement step
            step_index = self._execute_sweep_step(step_index)
            tick += 1

        self.motors.stop()

    # ── Public API ────────────────────────────────────────────────
    def set_target(self, target: str):
        """Set the object/person to search for before calling start()."""
        self.search_target = target
        logger.info(f"Search target set to: '{target}'")

    def start(self, target: str = None):
        if self.running:
            return
        if target:
            self.set_target(target)
        self.target_found = False
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info(f"Search Mode activated. Target: '{self.search_target}'")
        self._speak_ai(
            f"Search mission started. Looking for: {self.search_target}. "
            "Initiating area sweep."
        )

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        self.motors.stop()
        self.servos.set_pan(90)
        self.servos.set_tilt(90)
        status = "Target was found." if self.target_found else "Target not found. Mission aborted."
        logger.info(f"Search Mode deactivated. {status}")
        if self.speaker:
            self.speaker.speak(f"Search mode ended. {status}")
