import RPi.GPIO as GPIO
from utils.config import PINS
from utils.logger import get_logger

logger = get_logger("Motors")

class MotorController:
    def __init__(self):
        GPIO.setmode(GPIO.BCM)
        
        # Setup pins
        self.pins = [
            PINS["MOTOR_IN1"], PINS["MOTOR_IN2"], 
            PINS["MOTOR_IN3"], PINS["MOTOR_IN4"],
            PINS["MOTOR_ENA"], PINS["MOTOR_ENB"]
        ]
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
            
        # Setup PWM
        self.pwm_a = GPIO.PWM(PINS["MOTOR_ENA"], 1000) # 1kHz frequency
        self.pwm_b = GPIO.PWM(PINS["MOTOR_ENB"], 1000)
        self.pwm_a.start(0)
        self.pwm_b.start(0)
        
        logger.info("Motors initialized.")

    def set_speed(self, speed):
        # speed is 0 to 100
        speed = max(0, min(100, speed))
        self.pwm_a.ChangeDutyCycle(speed)
        self.pwm_b.ChangeDutyCycle(speed)

    def forward(self, speed=50):
        self.set_speed(speed)
        GPIO.output(PINS["MOTOR_IN1"], GPIO.HIGH)
        GPIO.output(PINS["MOTOR_IN2"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN3"], GPIO.HIGH)
        GPIO.output(PINS["MOTOR_IN4"], GPIO.LOW)

    def backward(self, speed=50):
        self.set_speed(speed)
        GPIO.output(PINS["MOTOR_IN1"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN2"], GPIO.HIGH)
        GPIO.output(PINS["MOTOR_IN3"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN4"], GPIO.HIGH)

    def left(self, speed=50):
        self.set_speed(speed)
        # Left wheels backward, right wheels forward
        GPIO.output(PINS["MOTOR_IN1"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN2"], GPIO.HIGH)
        GPIO.output(PINS["MOTOR_IN3"], GPIO.HIGH)
        GPIO.output(PINS["MOTOR_IN4"], GPIO.LOW)

    def right(self, speed=50):
        self.set_speed(speed)
        # Left wheels forward, right wheels backward
        GPIO.output(PINS["MOTOR_IN1"], GPIO.HIGH)
        GPIO.output(PINS["MOTOR_IN2"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN3"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN4"], GPIO.HIGH)

    def stop(self):
        self.set_speed(0)
        GPIO.output(PINS["MOTOR_IN1"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN2"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN3"], GPIO.LOW)
        GPIO.output(PINS["MOTOR_IN4"], GPIO.LOW)

    def cleanup(self):
        self.stop()
        self.pwm_a.stop()
        self.pwm_b.stop()