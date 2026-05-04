import time
import sys
import RPi.GPIO as GPIO
from utils.logger import get_logger
from utils.config import PINS
from utils.lcd_display import LCDDisplay
from sensors.ultrasonic import UltrasonicSensor
from sensors.sweeper_sonar import SweeperSonar
from sensors.gyroscope import MPU6050
from actuators.motors import MotorController
from actuators.servo import ServoController
from audio.speaker_output import SpeakerOutput
from audio.voice_brain import VoiceBrain
from vision.camera_stream import CameraStream
from modes.autonomous_mode import AutonomousMode
from modes.pet_mode import PetMode
from modes.surveillance_mode import SurveillanceMode
from modes.rescue_mode import RescueMode
from modes.search_mode import SearchMode
from modes.vision_drive_mode import VisionDriveMode
from communication.web_server import init_web_server, start_server_thread

logger = get_logger("MainController")

class RobotSystem:
    def __init__(self):
        logger.info("Initializing Robot System...")
        
        # Actuators
        self.motors = MotorController()
        self.servos = ServoController()
        
        # Sensors
        self.us_sweeper = UltrasonicSensor(PINS["US_FRONT_TRIG"], PINS["US_FRONT_ECHO"], "Sweeper")
        self.us_back    = UltrasonicSensor(PINS["US_BACK_TRIG"],  PINS["US_BACK_ECHO"],  "Back")
        self.us_down    = UltrasonicSensor(PINS["US_DOWN_TRIG"],  PINS["US_DOWN_ECHO"],  "Down")
        self.gyroscope  = MPU6050()

        # SweeperSonar handles the physical rotation of the front sensor
        self.sonar = SweeperSonar(self.us_sweeper, self.servos)

        # Peripherals
        self.speaker = SpeakerOutput()
        self.camera  = CameraStream()

        # Modes
        self.autonomous_mode   = AutonomousMode(self.motors, self.sonar, self.us_back, self.us_down, self.speaker)
        self.pet_mode          = PetMode(self.motors, self.servos, self.speaker, self.camera)
        self.surveillance_mode = SurveillanceMode(self.camera, self.speaker)
        self.rescue_mode       = RescueMode(self.motors, self.sonar, self.servos, self.speaker, self.camera)
        self.search_mode       = SearchMode(self.motors, self.sonar, self.servos, self.speaker, self.camera)
        self.vision_drive_mode = VisionDriveMode(self.motors, self.camera, self.servos, self.speaker)
        
        # Voice Brain (chatbot + command dispatcher)
        self.voice_brain = VoiceBrain(robot=self)
        
        # LCD Display (I2C 0x27)
        self.lcd = LCDDisplay()
        
        # Current state
        self.current_mode = None
        logger.info("System fully initialized.")

    def start(self):
        try:
            self.speaker.greet()
            self.camera.start()
            self.voice_brain.start()   # ← start listening for voice commands

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
            
            logger.info("Initializing web interface...")
            init_web_server(self)
            start_server_thread()
            
            logger.info("Starting central control loop...")
            
            # Default to autonomous mode for testing
            self.set_mode("autonomous")
            
            while True:
                # Main loop: Here you could add logic to switch modes
                # e.g., listening to API requests, voice commands, or NodeMCU messages
                
                # Periodically check road quality
                if self.gyroscope.detect_rough_road():
                    logger.warning("Rough road detected! Logging data...")
                    # Logic to save to report...
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Interrupted by user. Shutting down...")
            self.cleanup()
        except Exception as e:
            logger.error(f"System error: {e}")
            self.cleanup()

    def set_mode(self, mode_name, search_target: str = None):
        # Stop current mode
        if self.current_mode == "autonomous":
            self.autonomous_mode.stop()
        elif self.current_mode == "pet":
            self.pet_mode.stop()
        elif self.current_mode == "surveillance":
            self.surveillance_mode.stop()
        elif self.current_mode == "rescue":
            self.rescue_mode.stop()
        elif self.current_mode == "search":
            self.search_mode.stop()
        elif self.current_mode == "vision_drive":
            self.vision_drive_mode.stop()
            
        self.current_mode = mode_name
        self.lcd.show_mode(mode_name)   # ← update LCD on every mode change
        
        # Start new mode
        if mode_name == "autonomous":
            self.autonomous_mode.start()
        elif mode_name == "pet":
            self.pet_mode.start()
        elif mode_name == "surveillance":
            self.surveillance_mode.start()
        elif mode_name == "rescue":
            self.rescue_mode.start()
        elif mode_name == "search":
            self.search_mode.start(target=search_target)
        elif mode_name == "vision_drive":
            self.vision_drive_mode.start()
        elif mode_name == "idle":
            self.motors.stop()
        else:
            logger.warning(f"Unknown mode: {mode_name}")

    def cleanup(self):
        try: self.set_mode("idle")
        except Exception: pass
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
