"""
=============================================================
  Smart Autonomous AI Car - Camera Input Module
  Project: Smart Autonomous AI Car
  Hardware: Raspberry Pi 4 (4GB)
  Camera: Raspberry Pi Camera Module v2 / USB Webcam
=============================================================

Yeh file camera se live input leti hai aur frames process karti hai.
Dono Pi Camera aur USB Webcam ko support karta hai.

Dependencies install karne ke liye:
    pip install opencv-python picamera2 numpy

Raspberry Pi Camera ko enable karne ke liye:
    sudo raspi-config  -> Interface Options -> Camera -> Enable
"""

import cv2
import numpy as np
import time
import sys
import os

# =============================================================
#  CONFIGURATION - Yahan apni settings badlein
# =============================================================

CAMERA_TYPE = "picamera"     # "picamera" ya "usb" choose karein
USB_CAMERA_INDEX = 0          # USB webcam ke liye (0 = pehla camera)

FRAME_WIDTH = 640             # Frame width (pixels)
FRAME_HEIGHT = 480            # Frame height (pixels)
FPS = 30                      # Frames per second

SHOW_PREVIEW = True           # Live preview window dikhaye?
SAVE_FRAMES = False           # Frames save karein disk pe?
SAVE_PATH = "./captured_frames"  # Save folder path

# =============================================================
#  PI CAMERA INPUT CLASS
# =============================================================

# # class PiCameraInput:
#  """    Raspberry Pi Camera Module ke liye class.
#     picamera2 library use karta hai (Bullseye+ OS pe default).
#     """

#     def __init__(self, width=FRAME_WIDTH, height=FRAME_HEIGHT, fps=FPS):
#         self.width = width
#         self.height = height
#         self.fps = fps
#         self.camera = None
#         self._setup()

#     def _setup(self):
#         """Camera initialize karein."""
#         try:
#             from picamera2 import Picamera2
#             self.camera = Picamera2()
#             config = self.camera.create_preview_configuration(
#                 main={"size": (self.width, self.height), "format": "RGB888"}
#             )
#             self.camera.configure(config)
#             self.camera.start()
#             time.sleep(1)  # Camera warm-up ke liye wait karein
#             print("[OK] Raspberry Pi Camera successfully start hui!")
#         except ImportError:
#             print("[ERROR] picamera2 library nahi mili.")
#             print("       Install karein: sudo apt install python3-picamera2")
#             sys.exit(1)
#         except Exception as e:
#             print(f"[ERROR] Pi Camera start nahi hui: {e}")
#             print("       Check karein: sudo raspi-config -> Camera -> Enable")
#             sys.exit(1)

#     def read(self):
#         """
#         Camera se ek frame lein.
#         Returns: (success: bool, frame: numpy array BGR format)
#         """
#         try:
#             frame_rgb = self.camera.capture_array()
#             # RGB se BGR convert karein (OpenCV BGR use karta hai)
#             frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
#             return True, frame_bgr
#         except Exception as e:
#             print(f"[ERROR] Frame capture fail: {e}")
#             return False, None

#     def release(self):
#         """Camera band karein."""
#         if self.camera:
#             self.camera.stop()
#             print("[OK] Pi Camera band ho gayi.")


# =============================================================
#  USB WEBCAM INPUT CLASS
# =============================================================

class USBCameraInput:
    """
    USB Webcam ke liye class.
    OpenCV use karta hai - kisi bhi USB camera ke saath kaam karta hai.
    """

    def __init__(self, index=USB_CAMERA_INDEX, width=FRAME_WIDTH, height=FRAME_HEIGHT, fps=FPS):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.cap = None
        self._setup()

    def _setup(self):
        """Camera initialize karein."""
        self.cap = cv2.VideoCapture(self.index)

        if not self.cap.isOpened():
            print(f"[ERROR] USB Camera index {self.index} open nahi hui.")
            print(f"       Dusra index try karein: USB_CAMERA_INDEX = 1 ya 2")
            sys.exit(1)

        # Camera properties set karein
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)

        print(f"[OK] USB Camera (index={self.index}) successfully start hui!")
        print(f"     Resolution: {int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x"
              f"{int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")

    def read(self):
        """
        Camera se ek frame lein.
        Returns: (success: bool, frame: numpy array BGR format)
        """
        if not self.cap.isOpened():
            return False, None
        ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        """Camera band karein."""
        if self.cap:
            self.cap.release()
            print("[OK] USB Camera band ho gayi.")


# =============================================================
#  FRAME PROCESSOR - AI Car ke liye frame processing
# =============================================================

class FrameProcessor:
    """
    Camera frames ko process karne ke liye utility functions.
    AI Car ke liye useful operations.
    """

    @staticmethod
    def get_frame_info(frame):
        """Frame ki basic info return karein."""
        if frame is None:
            return {}
        h, w, c = frame.shape
        return {"height": h, "width": w, "channels": c}

    @staticmethod
    def resize(frame, width=320, height=240):
        """Frame resize karein (AI models ke liye chhota size faster hota hai)."""
        return cv2.resize(frame, (width, height))

    @staticmethod
    def to_grayscale(frame):
        """Frame ko grayscale mein convert karein."""
        return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    @staticmethod
    def flip_horizontal(frame):
        """Frame ko horizontally flip karein (mirror)."""
        return cv2.flip(frame, 1)

    @staticmethod
    def add_overlay(frame, fps, frame_count):
        """Frame pe FPS aur frame count dikhayein (debug ke liye)."""
        text1 = f"FPS: {fps:.1f}"
        text2 = f"Frame: {frame_count}"
        text3 = "Smart AI Car | Camera Input"

        cv2.putText(frame, text1, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, text2, (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(frame, text3, (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 1)
        return frame

    @staticmethod
    def detect_edges(frame):
        """Edge detection - line following ke liye useful."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)
        return edges

    @staticmethod
    def save_frame(frame, path, frame_count):
        """Frame disk pe save karein."""
        os.makedirs(path, exist_ok=True)
        filename = os.path.join(path, f"frame_{frame_count:06d}.jpg")
        cv2.imwrite(filename, frame)
        return filename


# =============================================================
#  MAIN CAMERA LOOP
# =============================================================

def main():
    """
    Main camera loop - frames continuously capture karta hai
    aur process karta hai.
    """
    print("=" * 55)
    print("  Smart Autonomous AI Car - Camera Input Module")
    print("=" * 55)
    print(f"  Camera Type : {CAMERA_TYPE}")
    print(f"  Resolution  : {FRAME_WIDTH}x{FRAME_HEIGHT}")
    print(f"  Target FPS  : {FPS}")
    print(f"  Preview     : {'ON' if SHOW_PREVIEW else 'OFF'}")
    print(f"  Save Frames : {'ON' if SAVE_FRAMES else 'OFF'}")
    print("=" * 55)
    print("  Controls: 'q' = Quit | 's' = Screenshot save")
    print("=" * 55)

    # Camera initialize karein
    if CAMERA_TYPE.lower() == "picamera":
        camera = PiCameraInput(width=FRAME_WIDTH, height=FRAME_HEIGHT, fps=FPS)
    elif CAMERA_TYPE.lower() == "usb":
        camera = USBCameraInput(index=USB_CAMERA_INDEX,
                                width=FRAME_WIDTH, height=FRAME_HEIGHT, fps=FPS)
    else:
        print(f"[ERROR] Unknown CAMERA_TYPE: '{CAMERA_TYPE}'. 'picamera' ya 'usb' use karein.")
        sys.exit(1)

    processor = FrameProcessor()

    # FPS calculate karne ke liye variables
    frame_count = 0
    fps_display = 0.0
    fps_timer = time.time()
    fps_frame_counter = 0

    print("\n[START] Camera loop shuru ho rahi hai...\n")

    try:
        while True:
            # --- Frame Capture ---
            success, frame = camera.read()

            if not success or frame is None:
                print("[WARNING] Frame capture fail hua, retry...")
                time.sleep(0.1)
                continue

            frame_count += 1
            fps_frame_counter += 1

            # --- FPS Calculate karein (har second update) ---
            elapsed = time.time() - fps_timer
            if elapsed >= 1.0:
                fps_display = fps_frame_counter / elapsed
                fps_frame_counter = 0
                fps_timer = time.time()

            # =================================================
            #  YAHAN APNA AI/PROCESSING CODE LIKHEIN
            # =================================================
            # Example 1: Edge detection (line following ke liye)
            # edges = processor.detect_edges(frame)

            # Example 2: Frame resize karein AI model ke liye
            # small_frame = processor.resize(frame, 320, 240)

            # Example 3: Apna object detection function call karein
            # detections = my_object_detector(frame)
            # =================================================

            # Overlay add karein (FPS + frame count)
            display_frame = processor.add_overlay(frame.copy(), fps_display, frame_count)

            # --- Preview Window ---
            if SHOW_PREVIEW:
                cv2.imshow("Smart AI Car - Camera Input", display_frame)

            # --- Auto Frame Save ---
            if SAVE_FRAMES:
                processor.save_frame(frame, SAVE_PATH, frame_count)

            # --- Keyboard Controls ---
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\n[QUIT] 'q' dabaya gaya, camera band ho rahi hai...")
                break

            elif key == ord('s'):
                # Manual screenshot
                fname = processor.save_frame(frame, "./screenshots", frame_count)
                print(f"[SAVE] Screenshot save hua: {fname}")

            # Terminal pe basic stats print karein (har 30 frames pe)
            if frame_count % 30 == 0:
                info = processor.get_frame_info(frame)
                print(f"[INFO] Frame #{frame_count} | FPS: {fps_display:.1f} | "
                      f"Size: {info['width']}x{info['height']}")

    except KeyboardInterrupt:
        print("\n[STOP] Ctrl+C dabaya gaya, band ho raha hai...")

    finally:
        # Cleanup
        camera.release()
        cv2.destroyAllWindows()
        print(f"\n[DONE] Total frames capture kiye: {frame_count}")
        print("[DONE] Camera module safely band ho gaya.")


# =============================================================
#  DIRECT USE EXAMPLE (import ke liye)
# =============================================================

def get_single_frame(camera_type=CAMERA_TYPE):
    """
    Sirf ek frame chahiye? Is function ko import karke use karein.

    Usage:
        from camera_input import get_single_frame
        frame = get_single_frame()
        # frame ab numpy array hai, OpenCV se process karein
    """
    if camera_type.lower() == "picamera":
        cam = PiCameraInput()
    else:
        cam = USBCameraInput()

    success, frame = cam.read()
    cam.release()

    if success:
        return frame
    else:
        raise RuntimeError("Frame capture fail hua.")


# =============================================================
#  ENTRY POINT
# =============================================================

if __name__ == "__main__":
    main()
