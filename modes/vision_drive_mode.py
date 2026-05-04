"""
vision_drive_mode.py
====================
Camera-Driven Autonomous Mode — combines all three vision functions:
  • LaneFollower          : keeps the robot on a lane/line
  • CameraObstacleDetector: spots obstacles from the camera image
  • YOLODetector          : identifies specific objects (people, stop signs, etc.)

Driving logic priority (highest → lowest):
  1. YOLO stop-sign / red-light detected   → STOP
  2. Camera obstacle threat = 'high'       → back up + turn
  3. Camera obstacle threat = 'medium'     → slow turn away
  4. Lane follower offset                  → steer to stay in lane
  5. Default                               → drive forward

Each vision function is individually callable at any time via the
public methods:
    mode.lane_result()      → latest LaneFollower  result dict
    mode.obstacle_result()  → latest CameraObstacle result dict
    mode.yolo_result()      → latest YOLODetector  result dict
"""

import time
import threading
import cv2
from utils.logger import get_logger
from utils.config import SETTINGS
from vision.camera_vision import LaneFollower, CameraObstacleDetector, YOLODetector

logger = get_logger("VisionDriveMode")

SPEED_NORMAL = SETTINGS.get("MOTOR_SPEED_DEFAULT", 45)
SPEED_SLOW   = max(25, SPEED_NORMAL - 20)

# YOLO classes that should make the robot stop completely
STOP_CLASSES = {"stop sign", "traffic light"}

# YOLO classes the robot should actively avoid / slow down for
CAUTION_CLASSES = {"person", "dog", "cat", "bicycle", "car"}


class VisionDriveMode:
    """
    Full camera-based autonomous driving mode.

    Constructor args:
        motors   : MotorController instance
        camera   : CameraStream instance
        servos   : ServoController instance (optional, for camera levelling)
        speaker  : SpeakerOutput instance (optional)
        use_yolo : bool — whether to run YOLODetector (heavier, ~10 FPS on Pi 4)
    """

    def __init__(self, motors, camera, servos=None, speaker=None,
                 use_yolo: bool = True):
        self.motors  = motors
        self.camera  = camera
        self.servos  = servos
        self.speaker = speaker
        self.running = False
        self.thread  = None

        # ── Vision modules (individually callable) ────────────────
        self.lane_detector     = LaneFollower()
        self.obstacle_detector = CameraObstacleDetector()
        self.yolo              = YOLODetector() if use_yolo else None

        # ── Latest results (thread-safe read) ────────────────────
        self._lane_result     = {}
        self._obstacle_result = {}
        self._yolo_result     = {}
        self._lock            = threading.Lock()

    # ── Public result accessors ────────────────────────────────────
    def lane_result(self) -> dict:
        """Return the latest result from LaneFollower.analyze()."""
        with self._lock:
            return dict(self._lane_result)

    def obstacle_result(self) -> dict:
        """Return the latest result from CameraObstacleDetector.analyze()."""
        with self._lock:
            return dict(self._obstacle_result)

    def yolo_result(self) -> dict:
        """Return the latest result from YOLODetector.analyze()."""
        with self._lock:
            return dict(self._yolo_result)

    # ── Manual single-shot calls (callable from outside at any time) ──
    def run_lane_check(self, frame=None) -> dict:
        """Run lane detection on a single frame and return result."""
        frame = frame if frame is not None else (self.camera.frame if self.camera else None)
        result = self.lane_detector.analyze(frame)
        with self._lock:
            self._lane_result = result
        return result

    def run_obstacle_check(self, frame=None) -> dict:
        """Run camera obstacle detection on a single frame and return result."""
        frame = frame if frame is not None else (self.camera.frame if self.camera else None)
        result = self.obstacle_detector.analyze(frame)
        with self._lock:
            self._obstacle_result = result
        return result

    def run_yolo_check(self, frame=None, filter_classes: list = None) -> dict:
        """Run YOLO object detection on a single frame and return result."""
        if self.yolo is None:
            return {"detections": [], "count": 0, "debug_frame": frame}
        frame = frame if frame is not None else (self.camera.frame if self.camera else None)
        result = self.yolo.analyze(frame, filter_classes=filter_classes)
        with self._lock:
            self._yolo_result = result
        return result

    # ── Driving decision engine ───────────────────────────────────
    def _make_drive_decision(self, lane: dict, obstacle: dict, yolo: dict):
        """
        Combine all three vision results into a single motor command.
        Returns: action string ('forward'|'left'|'right'|'backward'|'stop')
        """
        # Priority 1 — YOLO stop-class detected
        if yolo:
            for det in yolo.get("detections", []):
                if det["label"] in STOP_CLASSES and det["confidence"] > 0.6:
                    logger.warning(f"STOP CLASS detected: {det['label']}")
                    if self.speaker:
                        self.speaker.speak(f"{det['label']} detected. Stopping.")
                    return "stop"

        # Priority 2 — High obstacle threat from camera
        obs_threat = obstacle.get("threat", "none")
        obs_dir    = obstacle.get("direction", "none")

        if obs_threat == "high":
            logger.warning(f"High camera obstacle threat — direction: {obs_dir}")
            # Back up briefly (handled in loop), then turn away from obstacle
            if obs_dir == "left":
                return "right"
            elif obs_dir == "right":
                return "left"
            else:
                return "backward"   # Centre/full-width obstacle

        # Priority 3 — Medium obstacle threat
        if obs_threat == "medium":
            if obs_dir == "center":
                return "left"       # Default: turn left when blocked ahead
            elif obs_dir == "left":
                return "right"
            elif obs_dir == "right":
                return "left"

        # Priority 4 — YOLO caution class nearby (slow / steer around)
        if yolo:
            for det in yolo.get("detections", []):
                if det["label"] in CAUTION_CLASSES and det["confidence"] > 0.55:
                    cx = det["centre"][0]
                    frame_w = (self.camera.frame.shape[1]
                               if self.camera and self.camera.frame is not None else 640)
                    if cx < frame_w / 3:
                        return "right"    # Object on left → steer right
                    elif cx > 2 * frame_w / 3:
                        return "left"     # Object on right → steer left
                    else:
                        return "stop"     # Object dead ahead

        # Priority 5 — Lane following
        lane_action = lane.get("action", "forward")
        return lane_action

    # ── Main drive loop ───────────────────────────────────────────
    def _run_loop(self):
        backup_until = 0    # Timestamp until which we keep reversing

        if self.servos:
            self.servos.set_pan(90)
            self.servos.set_tilt(85)   # Slight downward tilt for road view

        tick = 0
        while self.running:
            frame = self.camera.frame if self.camera else None

            # Run vision analyses
            lane     = self.run_lane_check(frame)
            obstacle = self.run_obstacle_check(frame)
            yolo     = self.run_yolo_check(frame) if self.yolo else {}

            # Force backup window
            if time.time() < backup_until:
                self.motors.backward(speed=SPEED_SLOW)
                time.sleep(0.1)
                continue

            action = self._make_drive_decision(lane, obstacle, yolo)

            # Execute motor action
            if action == "forward":
                self.motors.forward(speed=SPEED_NORMAL)
            elif action == "left":
                self.motors.left(speed=SPEED_SLOW)
            elif action == "right":
                self.motors.right(speed=SPEED_SLOW)
            elif action == "backward":
                backup_until = time.time() + 0.6   # Reverse for 0.6 s
                self.motors.backward(speed=SPEED_SLOW)
            elif action == "stop":
                self.motors.stop()

            logger.debug(
                f"VisionDrive tick={tick} | "
                f"lane={lane.get('action','?')}({lane.get('offset',0):+.2f}) | "
                f"obs={obstacle.get('threat','?')} dir={obstacle.get('direction','?')} | "
                f"yolo={yolo.get('count',0)} objs | → {action}"
            )
            tick += 1
            time.sleep(0.1)

        self.motors.stop()

    # ── Public start / stop ───────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread  = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("VisionDriveMode started — camera-based autonomous driving active.")
        if self.speaker:
            self.speaker.speak(
                "Vision drive mode activated. Using camera for autonomous navigation."
            )

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=3)
        self.motors.stop()
        logger.info("VisionDriveMode stopped.")
        if self.speaker:
            self.speaker.speak("Vision drive mode deactivated.")
