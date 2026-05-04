import google.generativeai as genai
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("GeminiAgent")

class GeminiAgent:
    def __init__(self):
        api_key = SETTINGS.get("GEMINI_API_KEY")
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            logger.error("Gemini API key not configured. Please set GEMINI_API_KEY environment variable.")
            self.model = None
            return
            
        try:
            genai.configure(api_key=api_key)
            # Use gemini-1.5-flash for faster responses suitable for a robot
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            self.chat = self.model.start_chat(history=[])
            
            # System prompt to give the car its persona
            system_prompt = (
                "You are the brain of an autonomous robotic car built on a Raspberry Pi. "
                "You have features like obstacle avoidance, road quality detection, and surveillance. "
                "Keep your answers extremely concise, friendly, and practical, as they will be spoken aloud by a text-to-speech engine."
            )
            self.chat.send_message(system_prompt)
            
            logger.info("Gemini Agent initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.model = None

    def ask(self, query):
        if not self.model:
            return "I am sorry, my cloud intelligence is currently disconnected."
            
        try:
            logger.info(f"Asking Gemini: {query}")
            response = self.chat.send_message(query)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error querying Gemini: {e}")
            return "I am having trouble connecting to my cloud brain right now."
            
    def analyze_situation(self, sensor_data):
        """Pass sensor data to Gemini to get an intelligent decision or observation."""
        prompt = f"I am currently receiving this sensor data: {sensor_data}. What should I do or say?"
        return self.ask(prompt)
