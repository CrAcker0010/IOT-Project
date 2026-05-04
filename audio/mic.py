import speech_recognition as sr
from utils.logger import get_logger

logger = get_logger("MicInput")

class MicInput:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        
        # Adjust microphone sensitivity dynamically based on ambient noise
        try:
            with sr.Microphone() as source:
                logger.info("Calibrating microphone for ambient noise... Please wait.")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                logger.info("Microphone calibrated successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize microphone: {e}. Check hardware connections.")
            
    def listen(self, timeout=5, phrase_time_limit=10):
        """
        Listens to the microphone and returns the transcribed text.
        Returns None if no speech was detected or an error occurred.
        """
        logger.info("Listening for voice input...")
        try:
            with sr.Microphone() as source:
                # Capture the audio
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
                
            logger.info("Processing voice input...")
            # Use Google's free speech recognition to convert to text
            text = self.recognizer.recognize_google(audio)
            logger.info(f"User said: '{text}'")
            return text
            
        except sr.WaitTimeoutError:
            logger.info("Listening timed out. No speech detected.")
            return None
        except sr.UnknownValueError:
            logger.warning("Could not understand audio.")
            return None
        except sr.RequestError as e:
            logger.error(f"Could not request results from Speech Recognition service; {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during microphone recording: {e}")
            return None
