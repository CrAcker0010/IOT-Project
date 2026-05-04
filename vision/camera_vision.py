"""
camera_vision.py
================
Three independent, callable camera-vision functions for the robot:

  1. LaneFollower          — OpenCV line detection → steering command
  2. CameraObstacleDetector— Contour-based obstacle detection → threat level + direction
  3. YOLODetector          — YOLOv8-nano real-time object detection → labelled detections

All three classes share the same call interface:
    result = vision_object.analyze(frame)  →  returns a dict

Usage example:
    from vision.camera_vision import LaneFollower, CameraObstacleDetector, YOLODetector
    from vision.camera_stream import CameraStream

    cam    = CameraStream(); cam.start()
    lane   = LaneFollower()
    obs    = CameraObstacleDetector()
    yolo   = YOLODetector()

    frame  = cam.frame
    print(lane.analyze(frame))      # {'action': 'left', 'offset': -0.23, 'debug_frame': ...}
    print(obs.analyze(frame))       # {'threat': 'high', 'direction': 'center', 'debug_frame': ...}
    print(yolo.analyze(frame))      # {'detections': [{'label':'person','conf':0.92,...}], ...}
"""

import cv2
import numpy as np
from utils.logger import get_logger

logger = get_logger("CameraVision")


# ══════════════════════════════════════════════════════════════════
# 1.  LANE / LINE FOLLOWER
# ══════════════════════════════════════════════════════════════════
class LaneFollower:
    """
    Detects a line/lane on the floor using Canny edge detection +
    Hough Line Transform and recommends a steering command.

    analyze(frame) → dict:
        action      : 'forward' | 'left' | 'right' | 'stop'
        offset      : float  (-1.0 = hard left … 0 = centre … +1.0 = hard right)
        confidence  : float  (0-1, fraction of lines detected)
        debug_frame : annotated BGR frame for streaming/debugging
    """

    def __init__(self,
                 roi_top_ratio: float = 0.55,   # Upper boundary of region-of-interest
                 canny_low: int = 50,
                 canny_high: int = 150,
                 hough_threshold: int = 30,
                 steer_dead_zone: float = 0.08):
        self.roi_top      = roi_top_ratio
        self.canny_low    = canny_low
        self.canny_high   = canny_high
        self.hough_thresh = hough_threshold
        self.dead_zone    = steer_dead_zone   # offset range considered "straight"

    # ── Internal helpers ──────────────────────────────────────────
    def _region_of_interest(self, edges, h, w):
        mask    = np.zeros_like(edges)
        top_y   = int(h * self.roi_top)
        polygon = np.array([[
            (0,     h),
            (w,     h),
            (w,     top_y),
            (0,     top_y),
        ]], dtype=np.int32)
        cv2.fillPoly(mask, polygon, 255)
        return cv2.bitwise_and(edges, mask)

    def _average_lines(self, lines, w):
        """Separate left/right lines and return their averaged x-intercepts at frame bottom."""
        left_xs, right_xs = [], []
        if lines is None:
            return None, None
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 == x1:
                continue
            slope = (y2 - y1) / (x2 - x1)
            if abs(slope) < 0.3:   # Ignore near-horizontal lines
                continue
            cx = (x1 + x2) / 2
            if slope < 0:          # Negative slope → left lane in image coords
                left_xs.append(cx)
            else:                  # Positive slope → right lane
                right_xs.append(cx)
        left  = np.mean(left_xs)  if left_xs  else None
        right = np.mean(right_xs) if right_xs else None
        return left, right

    # ── Public API ────────────────────────────────────────────────
    def analyze(self, frame) -> dict:
        if frame is None:
            return {"action": "stop", "offset": 0.0, "confidence": 0.0, "debug_frame": None}

        h, w = frame.shape[:2]
        debug = frame.copy()

        # Pre-processing
        gray    = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges   = cv2.Canny(blurred, self.canny_low, self.canny_high)
        roi     = self._region_of_interest(edges, h, w)

        # Line detection
        lines = cv2.HoughLinesP(roi, 1, np.pi / 180,
                                threshold=self.hough_thresh,
                                minLineLength=30, maxLineGap=60)

        left_x, right_x = self._average_lines(lines, w)
        centre_x = w / 2

        # Determine lane centre
        if left_x is not None and right_x is not None:
            lane_centre = (left_x + right_x) / 2
            confidence  = 1.0
        elif left_x is not None:
            lane_centre = left_x + w * 0.25
            confidence  = 0.5
        elif right_x is not None:
            lane_centre = right_x - w * 0.25
            confidence  = 0.5
        else:
            # No lines found — go straight
            return {"action": "forward", "offset": 0.0, "confidence": 0.0, "debug_frame": debug}

        offset = (lane_centre - centre_x) / (w / 2)   # Normalised −1…+1

        # Steering decision
        if offset < -self.dead_zone:
            action = "left"
        elif offset > self.dead_zone:
            action = "right"
        else:
            action = "forward"

        # Annotate debug frame
        cv2.line(debug, (int(lane_centre), h), (int(lane_centre), int(h * self.roi_top)),
                 (0, 255, 0), 3)
        cv2.line(debug, (int(centre_x), h), (int(centre_x), int(h * self.roi_top)),
                 (255, 0, 0), 2)
        cv2.putText(debug, f"Lane: {action}  offset={offset:+.2f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

        logger.debug(f"LaneFollower → action={action}, offset={offset:.2f}, conf={confidence:.1f}")
        return {"action": action, "offset": round(offset, 3),
                "confidence": confidence, "debug_frame": debug}


# ══════════════════════════════════════════════════════════════════
# 2.  CAMERA-BASED OBSTACLE DETECTOR
# ══════════════════════════════════════════════════════════════════
class CameraObstacleDetector:
    """
    Detects obstacles in the camera frame using background subtraction /
    contour analysis in the lower portion of the frame (what the robot
    is about to drive into).

    analyze(frame) → dict:
        threat      : 'none' | 'low' | 'medium' | 'high'
        direction   : 'left' | 'center' | 'right' | 'none'
        fill_ratio  : float  (0-1, fraction of danger zone filled by obstacles)
        debug_frame : annotated BGR frame
    """

    def __init__(self,
                 danger_zone_top: float = 0.55,    # Top of the danger zone (fraction of frame)
                 low_thresh: float = 0.10,
                 medium_thresh: float = 0.25,
                 high_thresh: float = 0.45,
                 min_contour_area: int = 800):
        self.dz_top        = danger_zone_top
        self.low_thresh    = low_thresh
        self.med_thresh    = medium_thresh
        self.high_thresh   = high_thresh
        self.min_area      = min_contour_area

    def analyze(self, frame) -> dict:
        if frame is None:
            return {"threat": "none", "direction": "none",
                    "fill_ratio": 0.0, "debug_frame": None}

        h, w   = frame.shape[:2]
        debug  = frame.copy()
        dz_y   = int(h * self.dz_top)

        # Work only in the danger zone (lower portion of frame)
        roi = frame[dz_y:h, :]

        # Edge / threshold pipeline
        gray    = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 0, 255,
                                  cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

        contours, _ = cv2.findContours(cleaned, cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        dz_area   = roi.shape[0] * roi.shape[1]
        left_fill = center_fill = right_fill = 0

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            x, y, cw, ch = cv2.boundingRect(cnt)
            cx = x + cw / 2

            # Shift contour coords back to full-frame for drawing
            cnt_shifted = cnt.copy()
            cnt_shifted[:, :, 1] += dz_y
            cv2.drawContours(debug, [cnt_shifted], -1, (0, 0, 255), 2)

            # Bucket by horizontal position
            if cx < w / 3:
                left_fill   += area
            elif cx < 2 * w / 3:
                center_fill += area
            else:
                right_fill  += area

        total_fill = (left_fill + center_fill + right_fill) / dz_area
        fill_ratio = round(min(total_fill, 1.0), 3)

        # Threat level
        if fill_ratio >= self.high_thresh:
            threat = "high"
        elif fill_ratio >= self.med_thresh:
            threat = "medium"
        elif fill_ratio >= self.low_thresh:
            threat = "low"
        else:
            threat = "none"

        # Dominant direction
        buckets   = {"left": left_fill, "center": center_fill, "right": right_fill}
        direction = max(buckets, key=buckets.get) if fill_ratio >= self.low_thresh else "none"

        # Draw danger zone line
        cv2.line(debug, (0, dz_y), (w, dz_y), (0, 165, 255), 2)
        cv2.putText(debug,
                    f"Obstacle: {threat}  dir={direction}  fill={fill_ratio:.2f}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 165, 255), 2)

        logger.debug(f"CameraObstacle → threat={threat}, dir={direction}, fill={fill_ratio}")
        return {"threat": threat, "direction": direction,
                "fill_ratio": fill_ratio, "debug_frame": debug}


# ══════════════════════════════════════════════════════════════════
# 3.  YOLO OBJECT DETECTOR  (YOLOv8-nano via ultralytics)
# ══════════════════════════════════════════════════════════════════
class YOLODetector:
    """
    Runs YOLOv8-nano (ultralytics) on each frame for real-time
    multi-class object detection.

    First run: YOLOv8n weights (~6 MB) are auto-downloaded by ultralytics.

    analyze(frame, filter_classes=None) → dict:
        detections  : list of {label, confidence, bbox:[x1,y1,x2,y2], centre:(cx,cy)}
        count       : int
        debug_frame : annotated BGR frame

    filter_classes: optional list of class names to keep, e.g. ['person', 'dog']
    """

    # Standard COCO class names (80 classes)
    COCO_CLASSES = [
        "person","bicycle","car","motorbike","aeroplane","bus","train","truck","boat",
        "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
        "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
        "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball",
        "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
        "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
        "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
        "sofa","pottedplant","bed","diningtable","toilet","tvmonitor","laptop","mouse",
        "remote","keyboard","cell phone","microwave","oven","toaster","sink",
        "refrigerator","book","clock","vase","scissors","teddy bear","hair drier",
        "toothbrush"
    ]

    def __init__(self, model_size: str = "yolov8n.pt", confidence: float = 0.45):
        self.conf      = confidence
        self.model     = None
        self._model_id = model_size
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self._model_id)
            logger.info(f"YOLODetector: loaded {self._model_id}")
        except ImportError:
            logger.error(
                "ultralytics is not installed. "
                "Run: pip install ultralytics"
            )
        except Exception as e:
            logger.error(f"YOLODetector: failed to load model — {e}")

    def analyze(self, frame, filter_classes: list = None) -> dict:
        """
        Run YOLO inference on frame.

        Args:
            frame          : BGR numpy array
            filter_classes : list of class name strings to keep, or None for all
        Returns:
            dict with 'detections', 'count', 'debug_frame'
        """
        if frame is None or self.model is None:
            return {"detections": [], "count": 0, "debug_frame": frame}

        debug      = frame.copy()
        detections = []

        try:
            results = self.model(frame, conf=self.conf, verbose=False)[0]

            for box in results.boxes:
                cls_id  = int(box.cls[0])
                label   = (results.names.get(cls_id)
                           or (self.COCO_CLASSES[cls_id]
                               if cls_id < len(self.COCO_CLASSES) else str(cls_id)))
                conf_val = float(box.conf[0])

                if filter_classes and label not in filter_classes:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

                detections.append({
                    "label"     : label,
                    "confidence": round(conf_val, 2),
                    "bbox"      : [x1, y1, x2, y2],
                    "centre"    : (cx, cy),
                })

                # Annotate frame
                color = (0, 255, 0) if label == "person" else (255, 128, 0)
                cv2.rectangle(debug, (x1, y1), (x2, y2), color, 2)
                cv2.putText(debug, f"{label} {conf_val:.2f}",
                            (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX,
                            0.65, color, 2)

        except Exception as e:
            logger.error(f"YOLODetector inference error: {e}")

        cv2.putText(debug, f"YOLO detections: {len(detections)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        logger.debug(f"YOLODetector → {len(detections)} objects detected")
        return {"detections": detections, "count": len(detections), "debug_frame": debug}

    def detect_classes(self, frame, class_names: list) -> list:
        """Convenience wrapper — returns only detections matching class_names."""
        result = self.analyze(frame, filter_classes=class_names)
        return result["detections"]

    def is_present(self, frame, class_name: str) -> bool:
        """Returns True if at least one instance of class_name is visible."""
        return len(self.detect_classes(frame, [class_name])) > 0
