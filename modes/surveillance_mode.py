import time
import threading
import os
import google.generativeai as genai
from utils.logger import get_logger

logger = get_logger("SurveillanceMode")

class SurveillanceMode:
    def __init__(self, camera, speaker):
        self.camera = camera
        self.speaker = speaker
        self.running = False
        self.thread = None

        # Fresh Gemini Initialization specific to Surveillance Mode
        self.api_key = os.environ.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE")
        self.model = None
        self.chat = None
        
        if self.api_key and self.api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.chat = self.model.start_chat(history=[])
                
                # Surveillance Mode specific system prompt
                system_prompt = (
                    "You are a strict, highly vigilant, no-nonsense robot security guard. "
                    "You speak in brief, authoritarian military-style terminology. "
                    "Report status updates professionally and concisely (max 2 sentences). "
                    "Start your reports with 'SECURITY ALERT' or 'STATUS'."
                )
                self.chat.send_message(system_prompt)
                logger.info("Surveillance Mode Gemini intelligence initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini in Surveillance Mode: {e}")
        else:
            logger.warning("No GEMINI_API_KEY found. Surveillance Mode will run without cloud intelligence.")

    def get_security_report(self, observation):
        if not self.chat:
            return "Security perimeter is secure."
        try:
            prompt = f"I am observing the following: {observation}. Give me a security status update."
            response = self.chat.send_message(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "Camera feed active. Scanning for anomalies."

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("Surveillance Mode activated.")
        self.speaker.speak(self.get_security_report("Activating surveillance protocols and checking perimeter."))

    def _run_loop(self):
        scan_counter = 0
        while self.running:
            frame = self.camera.read()
            if frame is not None:
                # Placeholder for actual OpenCV motion/intruder detection
                motion_detected = False 
                
                if motion_detected:
                    alert = self.get_security_report("Unidentified movement detected in sector Alpha.")
                    self.speaker.speak(alert)
                    logger.warning("Motion detected in surveillance mode!")
            
            # Periodically give a status update
            scan_counter += 1
            if scan_counter > 50: # Roughly every 5 seconds (0.1s sleep * 50)
                update = self.get_security_report("No movement detected. Sector clear.")
                self.speaker.speak(update)
                scan_counter = 0
                
            time.sleep(0.1)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Surveillance Mode deactivated.")
