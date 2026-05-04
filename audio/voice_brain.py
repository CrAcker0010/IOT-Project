"""
voice_brain.py
==============
Central command dispatcher + AI chatbot for the IOT Robot.

Input sources:
  1. CLAP DETECTOR (physical) — counts clap patterns (1-4) on the sound sensor.
  2. WEB DASHBOARD (remote)   — text/voice commands via browser Speech API.

Both routes share the same command engine and Gemini chatbot.
"""

import os
import time
import threading
import google.generativeai as genai

from audio.clap_detector import ClapDetector
from audio.speaker_output import SpeakerOutput
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("VoiceBrain")

# ─────────────────────────────────────────────────────────────────────────────
# CLAP ACTION MAP — maps clap counts to robot actions
# ─────────────────────────────────────────────────────────────────────────────
CLAP_ACTIONS = {
    1: {"action": "stop_motors",      "reply": "Emergency stop."},
    2: {"action": "mode_autonomous",  "reply": "Toggling autonomous mode."},
    3: {"action": "mode_rescue",      "reply": "Toggling rescue mode."},
    4: {"action": "mode_search",      "reply": "Toggling search mode."},
}


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
        self.speaker = robot.speaker if robot else SpeakerOutput()
        self.running = False

        # Clap detector — physical input
        self.clap_detector = ClapDetector(callback=self._on_clap)

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

    # ── Clap handler (physical input) ──────────────────────────────
    def _on_clap(self, clap_count: int):
        """Called by ClapDetector when a clap pattern is detected."""
        logger.info(f"Clap pattern received: {clap_count} clap(s)")

        mapping = CLAP_ACTIONS.get(clap_count)
        if not mapping:
            logger.info(f"No action for {clap_count} claps.")
            return

        action = mapping["action"]
        reply  = mapping["reply"]

        # Toggle logic: if already in that mode, go idle instead
        r = self.robot
        if r and action.startswith("mode_"):
            mode_name = action.replace("mode_", "")
            if r.current_mode == mode_name:
                r.set_mode("idle")
                reply = f"Stopped {mode_name} mode."
            else:
                self._execute_action(action)
        else:
            self._execute_action(action)

        # Show on LCD
        if r and hasattr(r, 'lcd'):
            r.lcd.show_voice_command(f"{clap_count} claps: {action}")

        logger.info(f"Clap reply: {reply}")
        self.speaker.speak(reply)

    # ── Process a single utterance (from web UI) ──────────────────
    def process_utterance(self, text: str):
        """Parse text, execute command or chatbot reply, speak response."""
        if not text:
            return

        t = text.lower().strip()
        logger.info(f"Utterance (web): '{t}'")

        reply = None

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

    # ── Public API ────────────────────────────────────────────────
    def start(self):
        if self.running:
            return
        self.running = True
        self.clap_detector.start()   # ← physical clap listener
        logger.info("VoiceBrain started (clap input + web UI).")
        self.speaker.speak(
            "Robot assistant ready. Clap once to stop, twice for autonomous, "
            "three times for rescue, four for search. Or use the web dashboard."
        )

    def stop(self):
        self.running = False
        self.clap_detector.stop()
        logger.info("VoiceBrain stopped.")

    def chat_text(self, text: str) -> str:
        """
        Send a text message directly (used by web UI / REST API).
        Executes command if matched, else chatbot. Returns the reply string.
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
    print("VoiceBrain running (clap detection). Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        brain.stop()
        print("Exited.")
