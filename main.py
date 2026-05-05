"""
main.py — IOT Robot Main Controller
=====================================
Entry point for the manually-controlled robotic car.
Run: python3 main.py
"""

import time
import sys
import RPi.GPIO as GPIO
from utils.logger import get_logger
from utils.config import PINS, SETTINGS
from utils.lcd_display import LCDDisplay
from sensors.ultrasonic import UltrasonicSensor
from sensors.gyroscope import MPU6050
from actuators.motors import MotorController
from actuators.servo import ServoController
from audio.voice_brain import VoiceBrain
from vision.camera_stream import CameraStream
from communication.web_server import init_web_server, start_server_thread

logger = get_logger("MainController")


class RobotSystem:
    def __init__(self):
        logger.info("Initializing Robot System...")

        # ── Actuators ─────────────────────────────────────────────
        self.motors = MotorController()
        self.servos = ServoController()

        # ── Sensors ───────────────────────────────────────────────
        self.us_front = UltrasonicSensor(PINS["US_FRONT_TRIG"], PINS["US_FRONT_ECHO"], "Front")
        self.us_back  = UltrasonicSensor(PINS["US_BACK_TRIG"],  PINS["US_BACK_ECHO"],  "Back")
        self.us_down  = UltrasonicSensor(PINS["US_DOWN_TRIG"],  PINS["US_DOWN_ECHO"],  "Down")

        # Gyroscope (I2C — may fail if not wired)
        self.gyroscope = None
        try:
            self.gyroscope = MPU6050()
        except Exception as e:
            logger.warning(f"Gyroscope not available: {e}")

        # ── Peripherals ───────────────────────────────────────────
        self.camera  = CameraStream()

        # ── Clap detector (emergency stop) ────────────────────────
        self.voice_brain = VoiceBrain(robot=self)

        # ── LCD Display (I2C 0x27) ────────────────────────────────
        self.lcd = LCDDisplay()

        # ── Current state ─────────────────────────────────────────
        self.current_mode = "manual"
        logger.info("System fully initialized.")

    def start(self):
        try:
            self.camera.start()
            self.voice_brain.start()

            # Show boot info on LCD
            self.lcd.show_startup()
            time.sleep(2)
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                s.close()
            except Exception:
                ip = "Check router"
            self.lcd.show_ip(ip)
            logger.info(f"Dashboard: http://{ip}:{SETTINGS['STREAM_PORT']}")

            # Start web server
            logger.info("Initializing web interface...")
            init_web_server(self)
            start_server_thread(port=SETTINGS["STREAM_PORT"])

            logger.info("Robot ready. Manual control via web dashboard.")
            self.lcd.show_mode("manual")

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Interrupted by user. Shutting down...")
            self.cleanup()
        except Exception as e:
            logger.error(f"System error: {e}")
            self.cleanup()

    def cleanup(self):
        try: self.voice_brain.stop()
        except Exception: pass
        try: self.lcd.cleanup()
        except Exception: pass
        try: self.camera.stop()
        except Exception: pass
        try: self.motors.cleanup()
        except Exception: pass
        try: self.servos.cleanup()
        except Exception: pass
        try: GPIO.cleanup()
        except Exception: pass
        logger.info("Cleanup complete.")
        sys.exit(0)


if __name__ == "__main__":
    robot = RobotSystem()
    robot.start()
