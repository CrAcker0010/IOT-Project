# System Configuration File
import os

# GPIO Pins Configuration (BCM Mode)
PINS = {
    # Motor Driver (L298N)
    "MOTOR_ENA": 12, # PWM
    "MOTOR_ENB": 13, # PWM
    "MOTOR_IN1": 5,
    "MOTOR_IN2": 6,
    "MOTOR_IN3": 26,
    "MOTOR_IN4": 19,
    
    # Ultrasonic Sensors (Trig, Echo)
    "US_FRONT_TRIG": 17,
    "US_FRONT_ECHO": 27,
    "US_LEFT_TRIG": 22,
    "US_LEFT_ECHO": 10,
    "US_RIGHT_TRIG": 9,
    "US_RIGHT_ECHO": 11,
    "US_DOWN_TRIG": 20,
    "US_DOWN_ECHO": 21,
    
    # DHT11 Sensor
    "DHT11_PIN": 4,
    
    # Servos
    "SERVO_PAN": 14,
    "SERVO_TILT": 15,
    
    # Relays & Indicators
    "BUZZER": 18,
    "LED_RED": 23,
    "LED_GREEN": 24,
    "LED_BLUE": 25,
    
    # I2C (Gyroscope MPU6050 uses standard I2C pins GPIO2/SDA, GPIO3/SCL)
    # UART (GPS & NodeMCU uses standard UART TX/RX pins)
}

# Settings
SETTINGS = {
    "MOTOR_SPEED_DEFAULT": 50, # PWM Duty Cycle 0-100
    "OBSTACLE_THRESHOLD_CM": 30,
    "DANGER_THRESHOLD_CM": 15,
    "CAMERA_RESOLUTION": (640, 480),
    "CAMERA_FRAMERATE": 30,
    "STREAM_PORT": 5000,
    "NODEMCU_IP": "192.168.1.100",   # ← update after flashing (check Serial Monitor)
    "NODEMCU_BAUD": 9600,
    "GPS_BAUD": 9600,
    "GPS_PORT": "/dev/serial0",
    "NODEMCU_PORT": "/dev/ttyUSB0",
    "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
}

import json

def load_safety_limits():
    """Load the JSON limits for safe Gemini prototyping."""
    try:
        with open("safety_limits.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Could not load safety_limits.json: {e}")
        return None

SAFETY_LIMITS = load_safety_limits()
