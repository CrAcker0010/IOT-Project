import time
import RPi.GPIO as GPIO
from utils.config import PINS
from utils.logger import get_logger

logger = get_logger("Servo")

class ServoController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS["SERVO_PAN"], GPIO.OUT)
        GPIO.setup(PINS["SERVO_TILT"], GPIO.OUT)

        self.pan_pwm  = GPIO.PWM(PINS["SERVO_PAN"],  50)   # 50 Hz
        self.tilt_pwm = GPIO.PWM(PINS["SERVO_TILT"], 50)

        self.pan_pwm.start(0)
        self.tilt_pwm.start(0)

        # Center positions
        self.pan_angle  = 90
        self.tilt_angle = 90
        self.set_pan(self.pan_angle)
        self.set_tilt(self.tilt_angle)
        logger.info("Servos initialized.")

    def angle_to_duty_cycle(self, angle):
        """Maps 0-180° to ~2-12% duty cycle (standard servo range)."""
        return 2 + (angle / 18)

    def set_pan(self, angle):
        self.pan_angle = max(0, min(180, angle))
        self.pan_pwm.ChangeDutyCycle(self.angle_to_duty_cycle(self.pan_angle))
        time.sleep(0.25)
        self.pan_pwm.ChangeDutyCycle(0)   # Release signal — prevents jitter & heat

    def set_tilt(self, angle):
        self.tilt_angle = max(0, min(180, angle))
        self.tilt_pwm.ChangeDutyCycle(self.angle_to_duty_cycle(self.tilt_angle))
        time.sleep(0.25)
        self.tilt_pwm.ChangeDutyCycle(0)  # Release signal — prevents jitter & heat

    def cleanup(self):
        self.pan_pwm.stop()
        self.tilt_pwm.stop()

