# System Configuration File

# GPIO Pins Configuration (BCM Mode)
PINS = {
    # Motor Driver (L298N)
    "MOTOR_ENA": 12, # PWM
    "MOTOR_ENB": 13, # PWM
    "MOTOR_IN1": 5,
    "MOTOR_IN2": 6,
    "MOTOR_IN3": 26,
    "MOTOR_IN4": 19,
    
    # Ultrasonic Sensors
    "US_FRONT_TRIG": 9,  # On Pan-Tilt servo
    "US_FRONT_ECHO": 11,
    "US_BACK_TRIG":  22,
    "US_BACK_ECHO":  10,
    "US_DOWN_TRIG":  17,
    "US_DOWN_ECHO":  27,
    
    # DHT11 Sensor
    "DHT11_PIN": 4,
    
    # Servos (Moved to avoid UART conflict with GPS)
    "SERVO_PAN": 20,
    "SERVO_TILT": 21,
    
    # Relays & Indicators
    "BUZZER": 18,
    "MIC_PIN": 8,   # D0 pin of the Sound Sensor Module
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
    "CAMERA_RESOLUTION": (320, 240),    # Low-res for 1 GB RAM (saves ~40 MB)
    "CAMERA_FRAMERATE": 15,              # 15 fps is sufficient for robot nav
    "STREAM_PORT": 5000,
    "NODEMCU_IP": "192.168.1.100",   # ← update after flashing (check Serial Monitor)
    "NODEMCU_BAUD": 9600,
    "GPS_BAUD": 9600,
    "GPS_PORT": "/dev/serial0",
    "NODEMCU_PORT": "/dev/ttyUSB0",
    "GEMINI_API_KEY": "AIzaSyC2Gl6ggN2_uMdr7upMgp8alyoa5cQMNC0", # Update this with your actual key
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
