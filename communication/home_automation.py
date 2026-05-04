"""
home_automation.py
==================
Raspberry Pi side of the Home Automation system.

Listens for voice commands via the microphone and sends HTTP
requests to the NodeMCU (ESP32/ESP8266) to control:
  - Light 1
  - Light 2
  - Light 3
  - Door 4

Voice command examples:
  "turn on light 1"    → GET http://<NODEMCU_IP>/light/1/on
  "turn off light 2"   → GET http://<NODEMCU_IP>/light/2/off
  "open door"          → GET http://<NODEMCU_IP>/door/4/on
  "close door"         → GET http://<NODEMCU_IP>/door/4/off
  "turn off all"       → GET http://<NODEMCU_IP>/all/off
  "status"             → GET http://<NODEMCU_IP>/status  (prints JSON)

Usage:
  python -m communication.home_automation
  (or run it as a standalone script)
"""

import requests
import threading
import time
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("HomeAutomation")

# ── NodeMCU base URL ───────────────────────────────────────────────
# Update NODEMCU_IP in utils/config.py after flashing the Arduino sketch.
NODEMCU_BASE = f"http://{SETTINGS.get('NODEMCU_IP', '192.168.1.100')}"
REQUEST_TIMEOUT = 5   # seconds

# ── HTTP helper ────────────────────────────────────────────────────
def send_command(endpoint: str) -> dict | None:
    """Send a GET request to the NodeMCU and return the JSON response."""
    url = f"{NODEMCU_BASE}{endpoint}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        logger.info(f"NodeMCU response for '{endpoint}': {resp.text}")
        return resp.json()
    except requests.exceptions.ConnectionError:
        logger.error(f"Cannot reach NodeMCU at {NODEMCU_BASE}. Is it powered on and connected to WiFi?")
    except requests.exceptions.Timeout:
        logger.error(f"Request to NodeMCU timed out ({endpoint})")
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP error: {e}")
    return None

# ── Voice command parser ───────────────────────────────────────────
def parse_voice_command(text: str) -> str | None:
    """
    Parse a voice command string and return the corresponding
    NodeMCU API endpoint, or None if the command is not recognised.
    """
    if text is None:
        return None

    t = text.lower().strip()
    logger.info(f"Parsing voice command: '{t}'")

    # ── Turn OFF all ──────────────────────────────────────────────
    if any(k in t for k in ["all off", "everything off", "turn off all", "all lights off"]):
        return "/all/off"

    # ── Status check ─────────────────────────────────────────────
    if "status" in t:
        return "/status"

    # ── Door 4 ────────────────────────────────────────────────────
    if "door" in t or "door 4" in t or "gate" in t:
        if any(k in t for k in ["open", "unlock", "on"]):
            return "/door/4/on"
        if any(k in t for k in ["close", "lock", "off"]):
            return "/door/4/off"

    # ── Light number extraction ───────────────────────────────────
    number_map = {"one": "1", "two": "2", "three": "3", "1": "1", "2": "2", "3": "3"}
    action = None
    light_num = None

    if any(k in t for k in ["turn on", "switch on", "on"]):
        action = "on"
    elif any(k in t for k in ["turn off", "switch off", "off"]):
        action = "off"

    for word, num in number_map.items():
        if f"light {word}" in t or f"lamp {word}" in t or f"bulb {word}" in t:
            light_num = num
            break

    if action and light_num:
        return f"/light/{light_num}/{action}"

    logger.warning(f"Voice command not recognised: '{t}'")
    return None

# ── Speaker feedback ──────────────────────────────────────────────
def speak_feedback(endpoint: str, state: dict | None):
    """Log a friendly confirmation message (extend with TTS if needed)."""
    if state is None:
        logger.warning("No response from NodeMCU — check connection.")
        return

    feedback = {
        "/light/1/on":  "Light 1 is now ON.",
        "/light/1/off": "Light 1 is now OFF.",
        "/light/2/on":  "Light 2 is now ON.",
        "/light/2/off": "Light 2 is now OFF.",
        "/light/3/on":  "Light 3 is now ON.",
        "/light/3/off": "Light 3 is now OFF.",
        "/door/4/on":   "Door is now OPEN.",
        "/door/4/off":  "Door is now CLOSED.",
        "/all/off":     "All lights and the door are OFF.",
        "/status":      f"Current state: {state}",
    }
    logger.info(feedback.get(endpoint, f"Done: {endpoint}"))

# ── Main controller class ─────────────────────────────────────────
class HomeAutomationController:
    """Send commands to the NodeMCU. Voice input is handled by VoiceBrain."""

    def send_direct(self, endpoint: str) -> dict | None:
        """Send a command directly (used by voice_brain or web_server)."""
        state = send_command(endpoint)
        speak_feedback(endpoint, state)
        return state

# ── Standalone entry point (keyboard tester) ──────────────────────
if __name__ == "__main__":
    print("Home Automation Tester")
    print("Commands: light/1/on, light/2/off, door/4/on, all/off, status, quit")
    while True:
        cmd = input(">> ").strip()
        if cmd in ("quit", "exit"):
            break
        if not cmd.startswith("/"):
            cmd = "/" + cmd
        endpoint = parse_voice_command(cmd) if " " in cmd else cmd
        if endpoint:
            send_command(endpoint)
        else:
            print(f"Sending: {cmd}")
            send_command(cmd)

