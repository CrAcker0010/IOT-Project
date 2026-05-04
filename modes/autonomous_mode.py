import time
import threading
import os
import google.generativeai as genai
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("AutonomousMode")

class AutonomousMode:
    def __init__(self, motors, sensors, speaker=None):
        self.motors = motors
        self.sensors = sensors # dict containing "front", "left", "right"
        self.speaker = speaker
        self.running = False
        self.thread = None

        # Fresh Gemini Initialization specific to Autonomous Mode
        self.api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
        self.model = None
        self.chat = None
        
        if self.api_key and self.api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.chat = self.model.start_chat(history=[])
                
                # Autonomous Mode specific system prompt
                system_prompt = (
                    "You are the intelligent navigation computer of an autonomous car. "
                    "You process sensor data to make quick, logical driving decisions. "
                    "Keep your responses extremely short, technical, and precise, as if "
                    "reporting to a dashboard console. Maximum 1 sentence."
                )
                self.chat.send_message(system_prompt)
                logger.info("Autonomous Mode Gemini intelligence initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini in Autonomous Mode: {e}")
        else:
            logger.warning("No GEMINI_API_KEY found. Autonomous Mode will run without cloud intelligence.")

    def get_navigation_decision(self, sensor_data):
        if not self.chat:
            return "Navigating."
        try:
            prompt = f"Sensor readings - {sensor_data}. What is your navigation decision?"
            response = self.chat.send_message(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "Navigating."

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Autonomous mode started.")
        
        if self.speaker:
            self.speaker.speak(self.get_navigation_decision("Starting engine and beginning autonomous route computation."))

    def _run_loop(self):
        decision_timer = 0
        while self.running:
            front_dist = self.sensors["front"].get_distance()
            left_dist = self.sensors["left"].get_distance()
            right_dist = self.sensors["right"].get_distance()
            
            # Basic collision avoidance logic
            if front_dist > 0 and front_dist < SETTINGS["DANGER_THRESHOLD_CM"]:
                logger.warning("Obstacle too close! Stopping and reversing.")
                self.motors.backward(speed=50)
                time.sleep(0.5)
                self.motors.stop()
                
                # Check sides
                if left_dist > right_dist:
                    self.motors.left(speed=60)
                else:
                    self.motors.right(speed=60)
                time.sleep(0.5)
                self.motors.stop()
                
                # AI comment on danger
                if self.speaker:
                    sensor_str = f"Critical obstacle front at {front_dist}cm. Evasive maneuver executed."
                    self.speaker.speak(self.get_navigation_decision(sensor_str))
                
            elif front_dist > 0 and front_dist < SETTINGS["OBSTACLE_THRESHOLD_CM"]:
                logger.info("Obstacle detected ahead. Turning.")
                if left_dist > right_dist:
                    self.motors.left(speed=50)
                else:
                    self.motors.right(speed=50)
                time.sleep(0.3)
                
            else:
                self.motors.forward(speed=SETTINGS["MOTOR_SPEED_DEFAULT"])
                
            # Periodically let the AI comment on the route
            decision_timer += 1
            if decision_timer > 100: # Every ~10 seconds
                if self.speaker:
                    sensor_str = f"Front: {front_dist}cm, Left: {left_dist}cm, Right: {right_dist}cm. Path clear."
                    self.speaker.speak(self.get_navigation_decision(sensor_str))
                decision_timer = 0
                
            time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.motors.stop()
        logger.info("Autonomous mode stopped.")
