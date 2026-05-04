import cv2
import threading
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("CameraStream")

class CameraStream:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, SETTINGS["CAMERA_RESOLUTION"][0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SETTINGS["CAMERA_RESOLUTION"][1])
        self.cap.set(cv2.CAP_PROP_FPS, SETTINGS["CAMERA_FRAMERATE"])
        
        self.frame = None
        self.running = False
        self.thread = None
        
        if not self.cap.isOpened():
            logger.error("Failed to open camera.")

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()
        logger.info("Camera stream started.")

    def _update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                # Optionally add object detection logic here
                self.frame = frame

    def read(self):
        return self.frame

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.cap.release()
        logger.info("Camera stream stopped.")
