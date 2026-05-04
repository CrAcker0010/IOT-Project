import time
import RPi.GPIO as GPIO
from utils.logger import get_logger

logger = get_logger("Ultrasonic")

class UltrasonicSensor:
    def __init__(self, trig_pin, echo_pin, name="Sensor"):
        self.trig = trig_pin
        self.echo = echo_pin
        self.name = name
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig, GPIO.OUT)
        GPIO.setup(self.echo, GPIO.IN)
        GPIO.output(self.trig, False)
        
    def get_distance(self):
        try:
            # Send 10us pulse
            GPIO.output(self.trig, True)
            time.sleep(0.00001)
            GPIO.output(self.trig, False)
            
            pulse_start = time.time()
            pulse_end = time.time()
            
            timeout_start = time.time()
            
            while GPIO.input(self.echo) == 0:
                pulse_start = time.time()
                if pulse_start - timeout_start > 0.1: # timeout
                    return -1
                    
            while GPIO.input(self.echo) == 1:
                pulse_end = time.time()
                if pulse_end - timeout_start > 0.1: # timeout
                    return -1
                    
            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150
            return round(distance, 2)
            
        except Exception as e:
            logger.error(f"Error reading {self.name} sensor: {e}")
            return -1

    def cleanup(self):
        pass # Handle in main cleanup
