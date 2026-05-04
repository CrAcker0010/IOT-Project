import time
import threading
import random
import os
import cv2
import google.generativeai as genai
from utils.logger import get_logger

logger = get_logger("PetMode")

class PetMode:
    def __init__(self, motors, servos, speaker, camera=None):
        self.motors = motors
        self.servos = servos
        self.speaker = speaker
        self.camera = camera
        self.running = False
        self.thread = None
        self.seeking_owner = False
        try:
            self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        except Exception as e:
            logger.error(f"Failed to load face cascade: {e}")
            self.face_cascade = None
        
        # Fresh Gemini Initialization specific to Pet Mode
        self.api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
        self.model = None
        self.chat = None
        
        if self.api_key and self.api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.chat = self.model.start_chat(history=[])
                
                # Pet Mode specific system prompt
                system_prompt = (
                    "You are a highly energetic, playful, and affectionate robot pet dog. "
                    "You express yourself with short, enthusiastic phrases, barking noises, and "
                    "funny canine-like thoughts. Keep it under 2 sentences."
                )
                self.chat.send_message(system_prompt)
                logger.info("Pet Mode Gemini intelligence initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini in Pet Mode: {e}")
        else:
            logger.warning("No GEMINI_API_KEY found. Pet Mode will run without cloud intelligence.")

    def get_pet_thought(self):
        if not self.chat:
            return "Woof woof! I am a happy robot."
        try:
            response = self.chat.send_message("What are you thinking about or feeling right now?")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "*happy robot noises*"

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Pet Mode activated.")
        self.speaker.speak(self.get_pet_thought())

    def called_by_owner(self):
        self.seeking_owner = True
        logger.info("Pet has been called! Now seeking owner...")
        if self.speaker:
            self.speaker.speak("I'm coming!")

    def _run_loop(self):
        while self.running:
            if self.seeking_owner and self.camera and self.camera.frame is not None:
                # Seek the owner using the camera
                frame = self.camera.frame
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = []
                if self.face_cascade:
                    faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                if len(faces) > 0:
                    # Face found!
                    logger.info("Found owner!")
                    if self.speaker:
                        self.speaker.speak("There you are!")
                    # Drive forward for a short bit
                    self.motors.forward(speed=50)
                    time.sleep(1.0)
                    self.motors.stop()
                    self.seeking_owner = False # Found the owner, resume normal
                else:
                    # Scan for owner by turning
                    self.motors.left(speed=40)
                    time.sleep(0.3)
                    self.motors.stop()
                    time.sleep(0.5)
                continue # Skip the normal random behavior while seeking

            # 1. Randomly look around
            pan_angle = random.randint(45, 135)
            tilt_angle = random.randint(70, 110)
            self.servos.set_pan(pan_angle)
            self.servos.set_tilt(tilt_angle)
            
            # 2. Occasional "happy wiggles" and thoughts
            if random.random() > 0.8:
                self.motors.left(speed=40)
                time.sleep(0.2)
                self.motors.right(speed=40)
                time.sleep(0.2)
                self.motors.stop()
                
                # Speak a generated pet thought
                thought = self.get_pet_thought()
                self.speaker.speak(thought)

            # 3. Rest for a bit before next action
            time.sleep(random.uniform(2.0, 5.0))

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        self.motors.stop()
        logger.info("Pet Mode deactivated.")
