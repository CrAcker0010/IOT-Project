"""
voice_brain.py
==============
Central voice command dispatcher + AI chatbot for the IOT Robot.

This is the single entry-point for ALL voice interaction. It:
  1. Continuously listens to the microphone.
  2. Checks if the spoken text is an ACTION command → executes it.
  3. If no command matches → routes to the Gemini chatbot for a reply.
  4. Speaks every response back via the speaker.

Run standalone:
    python -m audio.voice_brain

Or integrate into RobotSystem (main.py):
    from audio.voice_brain import VoiceBrain
    self.voice_brain = VoiceBrain(robot=self)
    self.voice_brain.start()
"""

import os
import time
import threading
import google.generativeai as genai

from audio.mic import MicInput
from audio.speaker_output import SpeakerOutput
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("VoiceBrain")

# ─────────────────────────────────────────────────────────────────────────────
# WAKE WORD  (optional — set to None to process every utterance)
# ─────────────────────────────────────────────────────────────────────────────
WAKE_WORDS = ["hey robot", "robot", "autobot"]   # any of these activates listening


# ─────────────────────────────────────────────────────────────────────────────
# COMMAND MAP
# Each entry:  trigger_phrases  →  (action_key, spoken_confirmation)
#
# action_key is handled in VoiceBrain._execute_action()
# ─────────────────────────────────────────────────────────────────────────────
COMMAND_MAP = [
 
    # ── Robot Modes ───────────────────────────────────────────────────────────
    {
        "phrases": ["autonomous mode", "start autonomous", "self drive", "drive yourself",
                    "auto mode", "start auto"],
        "action": "mode_autonomous",
        "reply": "Switching to autonomous mode. Ultrasonic navigation active."
    },
    {
        "phrases": ["vision drive", "camera drive", "drive with camera",
                    "start vision drive", "camera autonomous"],
        "action": "mode_vision_drive",
        "reply": "Vision drive mode activated. Using camera for navigation."
    },
    {
        "phrases": ["pet mode", "start pet mode", "act like a pet", "be a pet dog"],
        "action": "mode_pet",
        "reply": "Woof! Pet mode activated. I'm your robot dog now!"
    },
    {
        "phrases": ["surveillance mode", "start surveillance", "guard mode",
                    "watch mode", "security mode"],
        "action": "mode_surveillance",
        "reply": "Surveillance mode engaged. Monitoring the perimeter."
    },
    {
        "phrases": ["rescue mode", "start rescue", "find survivors",
                    "search for people", "rescue bot"],
        "action": "mode_rescue",
        "reply": "Rescue bot activated. Beginning survivor search."
    },
    {
        "phrases": ["search mode", "searching mode", "find object",
                    "look for something", "search bot"],
        "action": "mode_search",
        "reply": "Search mode activated. What should I look for? Please specify."
    },
    {
        "phrases": ["stop", "halt", "idle", "stop everything",
                    "stop moving", "cancel", "abort"],
        "action": "mode_idle",
        "reply": "Stopping all operations. Standing by."
    },

    # ── Movement Controls ─────────────────────────────────────────────────────
    {
        "phrases": ["move forward", "go forward", "drive forward", "go ahead"],
        "action": "move_forward",
        "reply": "Moving forward."
    },
    {
        "phrases": ["move backward", "go backward", "reverse", "back up", "go back"],
        "action": "move_backward",
        "reply": "Reversing."
    },
    {
        "phrases": ["turn left", "go left", "move left", "steer left"],
        "action": "move_left",
        "reply": "Turning left."
    },
    {
        "phrases": ["turn right", "go right", "move right", "steer right"],
        "action": "move_right",
        "reply": "Turning right."
    },
    {
        "phrases": ["stop moving", "stop motors", "motors off"],
        "action": "stop_motors",
        "reply": "Motors stopped."
    },

    # ── Camera / Servo Controls ───────────────────────────────────────────────
    {
        "phrases": ["look up", "camera up", "tilt up"],
        "action": "servo_up",
        "reply": "Tilting camera up."
    },
    {
        "phrases": ["look down", "camera down", "tilt down"],
        "action": "servo_down",
        "reply": "Tilting camera down."
    },
    {
        "phrases": ["look left", "camera left", "pan left"],
        "action": "servo_left",
        "reply": "Panning camera left."
    },
    {
        "phrases": ["look right", "camera right", "pan right"],
        "action": "servo_right",
        "reply": "Panning camera right."
    },
    {
        "phrases": ["center camera", "reset camera", "camera center", "look ahead"],
        "action": "servo_center",
        "reply": "Camera centered."
    },

    # ── Home Automation (NodeMCU via WiFi) ────────────────────────────────────
    {
        "phrases": ["turn on light 1", "switch on light 1", "light one on",
                    "light 1 on", "turn on light one"],
        "action": "light_1_on",
        "reply": "Light 1 is now ON."
    },
    {
        "phrases": ["turn off light 1", "switch off light 1", "light one off",
                    "light 1 off", "turn off light one"],
        "action": "light_1_off",
        "reply": "Light 1 is now OFF."
    },
    {
        "phrases": ["turn on light 2", "switch on light 2", "light two on",
                    "light 2 on", "turn on light two"],
        "action": "light_2_on",
        "reply": "Light 2 is now ON."
    },
    {
        "phrases": ["turn off light 2", "switch off light 2", "light two off",
                    "light 2 off", "turn off light two"],
        "action": "light_2_off",
        "reply": "Light 2 is now OFF."
    },
    {
        "phrases": ["turn on light 3", "switch on light 3", "light three on",
                    "light 3 on", "turn on light three"],
        "action": "light_3_on",
        "reply": "Light 3 is now ON."
    },
    {
        "phrases": ["turn off light 3", "switch off light 3", "light three off",
                    "light 3 off", "turn off light three"],
        "action": "light_3_off",
        "reply": "Light 3 is now OFF."
    },
    {
        "phrases": ["turn off all lights", "all lights off", "everything off",
                    "all off", "turn off all"],
        "action": "lights_all_off",
        "reply": "All lights are now OFF."
    },
    {
        "phrases": ["open door", "unlock door", "open gate", "door open"],
        "action": "door_open",
        "reply": "Door is now OPEN."
    },
    {
        "phrases": ["close door", "lock door", "shut door", "door close", "door closed"],
        "action": "door_close",
        "reply": "Door is now CLOSED."
    },

    # ── System / Info ─────────────────────────────────────────────────────────
    {
        "phrases": ["what mode", "current mode", "what are you doing",
                    "what is your mode"],
        "action": "report_mode",
        "reply": None   # dynamically generated
    },
    {
        "phrases": ["status", "system status", "report status", "give status"],
        "action": "report_status",
        "reply": None   # dynamically generated
    },
    {
        "phrases": ["what can you do", "list commands", "help", "show commands",
                    "what commands"],
        "action": "list_commands",
        "reply": (
            "I can switch between autonomous, vision drive, pet, surveillance, "
            "rescue, and search modes. I can move forward, backward, left, right. "
            "Control the camera, turn lights on or off, open and close the door. "
            "And I can chat with you using AI."
        )
    },
    {
        "phrases": ["introduce yourself", "who are you", "what are you"],
        "action": "introduce",
        "reply": (
            "I am your autonomous multipurpose robotic assistant, powered by "
            "Raspberry Pi and Gemini AI. I can navigate, detect objects, "
            "stream video, control your home, and have a conversation with you."
        )
    },
    {
        "phrases": ["sleep", "go to sleep", "power down", "standby"],
        "action": "mode_idle",
        "reply": "Going to standby mode. Say 'hey robot' to wake me up."
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# VOICE BRAIN CLASS
# ─────────────────────────────────────────────────────────────────────────────
class VoiceBrain:

    def __init__(self, robot=None):
        """
        Args:
            robot : RobotSystem instance from main.py (or None for standalone).
        """
        self.robot   = robot
        self.mic     = MicInput()
        self.speaker = robot.speaker if robot else SpeakerOutput()
        self.running = False
        self.thread  = None
        self._awake  = (not WAKE_WORDS)   # Always awake if WAKE_WORDS is empty

        # ── Gemini Chatbot ────────────────────────────────────────
        self.chat = None
        api_key = os.environ.get("GEMINI_API_KEY",
                                  SETTINGS.get("GEMINI_API_KEY", "YOUR_API_KEY_HERE"))
        if api_key and api_key != "YOUR_API_KEY_HERE":
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                self.chat = model.start_chat(history=[])
                self.chat.send_message(
                    "You are the AI brain of an autonomous multipurpose robot. "
                    "Your name is ARIA (Autonomous Robotic Intelligent Assistant). "
                    "You are friendly, concise, and helpful. "
                    "When the user speaks to you, reply in 1-2 short sentences max. "
                    "If asked to perform a robot action you cannot execute, "
                    "explain what voice command to say instead."
                )
                logger.info("VoiceBrain chatbot (Gemini) initialized.")
            except Exception as e:
                logger.error(f"Gemini chatbot init failed: {e}")

    # ── Command matching ──────────────────────────────────────────
    def _match_command(self, text: str):
        """Return the matched entry from COMMAND_MAP or None."""
        t = text.lower().strip()
        for entry in COMMAND_MAP:
            for phrase in entry["phrases"]:
                if phrase in t:
                    return entry
        return None

    # ── Action executor ───────────────────────────────────────────
    def _execute_action(self, action: str) -> str | None:
        """
        Execute the robot action. Returns an override reply string,
        or None to use the default reply from COMMAND_MAP.
        """
        r = self.robot

        # ── Modes ─────────────────────────────────────────────────
        if action == "mode_autonomous"   and r: r.set_mode("autonomous")
        elif action == "mode_vision_drive" and r: r.set_mode("vision_drive")
        elif action == "mode_pet"          and r: r.set_mode("pet")
        elif action == "mode_surveillance" and r: r.set_mode("surveillance")
        elif action == "mode_rescue"       and r: r.set_mode("rescue")
        elif action == "mode_search"       and r: r.set_mode("search")
        elif action == "mode_idle"         and r: r.set_mode("idle")

        # ── Movement ──────────────────────────────────────────────
        elif action == "move_forward"  and r: r.motors.forward(speed=50)
        elif action == "move_backward" and r: r.motors.backward(speed=50)
        elif action == "move_left"     and r: r.motors.left(speed=50)
        elif action == "move_right"    and r: r.motors.right(speed=50)
        elif action == "stop_motors"   and r: r.motors.stop()

        # ── Servos ────────────────────────────────────────────────
        elif action == "servo_up"     and r:
            r.servos.set_tilt(max(0,  r.servos.tilt_angle - 15))
        elif action == "servo_down"   and r:
            r.servos.set_tilt(min(180, r.servos.tilt_angle + 15))
        elif action == "servo_left"   and r:
            r.servos.set_pan(min(180,  r.servos.pan_angle + 15))
        elif action == "servo_right"  and r:
            r.servos.set_pan(max(0,    r.servos.pan_angle - 15))
        elif action == "servo_center" and r:
            r.servos.set_pan(90); r.servos.set_tilt(90)

        # ── Home Automation (NodeMCU) ─────────────────────────────
        elif action in ("light_1_on","light_1_off","light_2_on","light_2_off",
                        "light_3_on","light_3_off","lights_all_off",
                        "door_open","door_close"):
            from communication.home_automation import send_command
            mapping = {
                "light_1_on":    "/light/1/on",
                "light_1_off":   "/light/1/off",
                "light_2_on":    "/light/2/on",
                "light_2_off":   "/light/2/off",
                "light_3_on":    "/light/3/on",
                "light_3_off":   "/light/3/off",
                "lights_all_off":"/all/off",
                "door_open":     "/door/4/on",
                "door_close":    "/door/4/off",
            }
            send_command(mapping[action])

        # ── Dynamic replies ───────────────────────────────────────
        elif action == "report_mode":
            mode = r.current_mode if r else "unknown"
            return f"I am currently in {mode} mode."

        elif action == "report_status":
            if r:
                return (
                    f"Mode: {r.current_mode}. "
                    f"Camera: {'active' if r.camera.running else 'off'}."
                )
            return "Robot not connected."

        elif action == "introduce":
            pass   # Reply already set in COMMAND_MAP

        elif action == "list_commands":
            pass   # Reply already set in COMMAND_MAP

        return None   # Use default COMMAND_MAP reply

    # ── Chatbot fallback ──────────────────────────────────────────
    def _chatbot_reply(self, text: str) -> str:
        """Send text to Gemini and return the response."""
        if self.chat is None:
            return "I'm not sure how to respond to that. Try asking for help."
        try:
            resp = self.chat.send_message(text)
            return resp.text.strip()
        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return "Sorry, I had trouble thinking of a response."

    # ── Process a single utterance ────────────────────────────────
    def process_utterance(self, text: str):
        """Parse text, execute command or chatbot reply, speak response."""
        if not text:
            return

        t = text.lower().strip()
        logger.info(f"Utterance: '{t}'")

        # Wake word check
        if WAKE_WORDS and not self._awake:
            if any(w in t for w in WAKE_WORDS):
                self._awake = True
                self.speaker.speak("Yes? I'm listening.")
            return

        # Reset awake after each handled command (require wake word again)
        # Comment out the next line to stay always-on without wake word
        # self._awake = False

        # Try to match a command
        entry = self._match_command(t)
        if entry:
            override = self._execute_action(entry["action"])
            reply    = override if override else entry["reply"]
            # Show command on LCD
            if self.robot and hasattr(self.robot, 'lcd'):
                self.robot.lcd.show_voice_command(entry["action"].replace("_", " "))
        else:
            # No command matched → chatbot
            logger.info("No command matched — routing to chatbot.")
            reply = self._chatbot_reply(text)
            # Scroll chatbot reply on LCD
            if reply and self.robot and hasattr(self.robot, 'lcd'):
                self.robot.lcd.show_chatbot_reply(reply)

        if reply:
            logger.info(f"Robot replies: {reply}")
            self.speaker.speak(reply)

    # ── Background listen loop ────────────────────────────────────
    def _loop(self):
        logger.info("VoiceBrain listening loop started.")
        while self.running:
            try:
                text = self.mic.listen(timeout=8, phrase_time_limit=8)
                if text:
                    self.process_utterance(text)
            except Exception as e:
                logger.error(f"VoiceBrain loop error: {e}")
                time.sleep(1)

    # ── Public API ────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread  = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        logger.info("VoiceBrain started.")
        self.speaker.speak(
            f"Voice assistant ready. {'Say ' + WAKE_WORD + ' to activate.' if WAKE_WORD else 'Listening for commands.'}"
        )

    def stop(self):
        self.running = False
        logger.info("VoiceBrain stopped.")

    def chat_text(self, text: str) -> str:
        """
        Send a text message directly to the chatbot (used by web UI).
        Returns the reply string without speaking it.
        """
        entry = self._match_command(text)
        if entry:
            override = self._execute_action(entry["action"])
            return override if override else entry["reply"]
        return self._chatbot_reply(text)


# ── Standalone entry point ────────────────────────────────────────
if __name__ == "__main__":
    brain = VoiceBrain(robot=None)
    brain.start()
    print(f"Voice Brain running. Wake word: '{WAKE_WORD}'. Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        brain.stop()
        print("Exited.")
