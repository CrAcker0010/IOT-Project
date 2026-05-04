import os
import queue
import threading
import pyttsx3
from utils.logger import get_logger

logger = get_logger("Speaker")

class SpeakerOutput:
    def __init__(self):
        self._queue  = queue.Queue()
        self._engine = None
        self._worker_thread = threading.Thread(
            target=self._worker, daemon=True
        )
        self._worker_thread.start()
        logger.info("Speaker output initialized (thread-safe queue mode).")

    def _init_engine(self):
        """Initialise pyttsx3 inside the worker thread (required for some backends)."""
        try:
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate',   150)
            self._engine.setProperty('volume', 0.9)
        except Exception as e:
            logger.error(f"pyttsx3 init failed: {e}. Will fall back to espeak.")
            self._engine = None

    def _worker(self):
        """Dedicated thread: pulls text from the queue and speaks it serially."""
        self._init_engine()
        while True:
            text = self._queue.get()
            if text is None:   # Shutdown sentinel
                break
            logger.info(f"Robot says: {text}")
            try:
                if self._engine:
                    self._engine.say(text)
                    self._engine.runAndWait()
                else:
                    os.system(f'espeak "{text}"')
            except Exception as e:
                logger.error(f"Speaker error: {e}")
                # Re-init engine on error
                self._init_engine()
            finally:
                self._queue.task_done()

    def speak(self, text: str):
        """Queue text for speaking. Thread-safe — callable from any thread."""
        if text:
            self._queue.put(str(text))

    def greet(self):
        self.speak("Hello Sir, I am your autonomous multipurpose robotic assistant.")

    def explain_features(self):
        self.speak(
            "I can navigate autonomously, stream live video, "
            "detect road conditions, and act as a pet or surveillance robot."
        )

    def stop(self):
        """Gracefully shut down the speaker worker."""
        self._queue.put(None)

