"""
gemini.py
=========
Gemini AI Controller for robot intelligence and chat.
"""

from google import genai
from utils.logger import get_logger

logger = get_logger("GeminiAI")

class GeminiAI:
    def __init__(self, api_key):
        if not api_key or api_key == "YOUR_API_KEY_HERE":
            logger.warning("Gemini API Key is not configured correctly in config.py.")
            self.client = None
            return
            
        try:
            self.client = genai.Client(api_key=api_key)
            self.model_id = "gemini-2.0-flash"
            logger.info("Gemini AI Client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self.client = None

    def chat(self, prompt):
        """Send a prompt to Gemini and return the text response."""
        if not self.client:
            return "Error: Gemini API key not configured. Please add your key to utils/config.py."
            
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API Error: {e}")
            return f"Error communicating with Gemini: {str(e)}"