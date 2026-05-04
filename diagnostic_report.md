# 🔍 IOT Robot — Full Diagnostic Report

---

## 1. GPIO Pin Collision Audit

All pins are in **BCM numbering**. The Pi 4 has GPIO 0–27 usable.

| GPIO | Assigned To | Direction | Conflict? |
|------|------------|-----------|-----------|
| 2 | I2C SDA (MPU6050 + LCD) | I2C | ✅ None — shared I2C bus is correct |
| 3 | I2C SCL (MPU6050 + LCD) | I2C | ✅ None — shared I2C bus is correct |
| 4 | DHT11 | IN | ✅ None |
| 5 | MOTOR_IN1 | OUT | ✅ None |
| 6 | MOTOR_IN2 | OUT | ✅ None |
| 9 | US_RIGHT_TRIG | OUT | ✅ None |
| 10 | US_LEFT_ECHO | IN | ✅ None |
| 11 | US_RIGHT_ECHO | IN | ✅ None |
| 12 | MOTOR_ENA (PWM) | OUT/PWM | ✅ None |
| 13 | MOTOR_ENB (PWM) | OUT/PWM | ✅ None |
| 14 | SERVO_PAN (PWM) | OUT/PWM | ✅ None |
| 15 | SERVO_TILT (PWM) | OUT/PWM | ✅ None |
| 17 | US_FRONT_TRIG | OUT | ✅ None |
| 18 | BUZZER | OUT | ✅ None |
| 19 | MOTOR_IN4 | OUT | ✅ None |
| 22 | US_LEFT_TRIG | OUT | ✅ None |
| 23 | LED_RED | OUT | ✅ None |
| 24 | LED_GREEN | OUT | ✅ None |
| 25 | LED_BLUE | OUT | ✅ None |
| 26 | MOTOR_IN3 | OUT | ✅ None |
| 27 | US_FRONT_ECHO | IN | ✅ None |

> **GPIO 0 and 1 (US_DOWN_TRIG / US_DOWN_ECHO)** — ⚠️ These are reserved for EEPROM (HAT ID). Safe to use if no HAT is attached, but avoid if possible. Use GPIO 20/21 instead.

**Result: ✅ No pin collisions.**

---

## 2. I2C Address Audit

| Device | Address | Bus |
|--------|---------|-----|
| MPU6050 Gyroscope | 0x68 | I2C-1 |
| LCD (PCF8574) | 0x27 | I2C-1 |

**Result: ✅ No I2C address conflicts.**  
Both devices share the same SDA/SCL wires — this is correct and expected for I2C.

---

## 3. UART Bus Conflict ⚠️

| Device | Port | Baud |
|--------|------|------|
| GPS | `/dev/serial0` | 9600 |
| NodeMCU (old serial code) | `/dev/ttyUSB0` | 9600 |

**Result: ✅ No conflict** — GPS uses the Pi's hardware UART `/dev/serial0` and NodeMCU is now WiFi-based (HTTP). The old `nodemcu.py` serial file is no longer used.

---

## 4. Predictable Failure Points & Fixes

### FAILURE 1 — `smbus` vs `smbus2` in gyroscope.py
**Root cause:** `gyroscope.py` imports `smbus` (old library). Pi OS may only have `smbus2`.  
**Fix:**
```python
# gyroscope.py line 1 — change:
import smbus
# to:
try:
    import smbus2 as smbus
except ImportError:
    import smbus
```

---

### FAILURE 2 — GPIO `setmode` called multiple times
**Root cause:** Both `motors.py` and `servo.py` each call `GPIO.setmode(GPIO.BCM)`. If called twice with the same mode it is fine, but any inconsistency crashes the program.  
**Fix:** Call `GPIO.setmode(GPIO.BCM)` only once in `main.py` before any hardware is initialized, and remove it from the individual classes.

---

### FAILURE 3 — `GPIO.cleanup()` called before PWM stops
**Root cause:** In `cleanup()` in `main.py`, `GPIO.cleanup()` is called, but PWM objects (`pwm_a`, `pwm_b` in motors) may still be running if `motors.cleanup()` raises an exception first.  
**Fix:** Wrap each cleanup step in `try/except`:
```python
def cleanup(self):
    try: self.set_mode("idle")
    except: pass
    try: self.voice_brain.stop()
    except: pass
    try: self.lcd.cleanup()
    except: pass
    try: self.camera.stop()
    except: pass
    try: self.motors.cleanup()
    except: pass
    try: self.servos.cleanup()
    except: pass
    try: GPIO.cleanup()
    except: pass
```

---

### FAILURE 4 — Servo PWM signal stays active (motor jitter)
**Root cause:** `servo.py` uses `ChangeDutyCycle()` but never calls `ChangeDutyCycle(0)` after moving. This keeps the PWM signal high and causes the servo to jitter and heat up.  
**Fix:** Add a stop pulse after each move:
```python
def set_pan(self, angle):
    self.pan_angle = max(0, min(180, angle))
    self.pan_pwm.ChangeDutyCycle(self.angle_to_duty_cycle(self.pan_angle))
    time.sleep(0.3)
    self.pan_pwm.ChangeDutyCycle(0)   # ← stop signal
```

---

### FAILURE 5 — `CameraStream.read()` vs `.frame`
**Root cause:** `CameraStream` exposes both a `.frame` attribute and a `.read()` method, but `surveillance_mode.py` calls `self.camera.read()` while other modes use `self.camera.frame`. They are equivalent here, but if `read()` is later changed to return a copy this breaks.  
**Fix:** Standardise all modes to use `self.camera.frame`.

---

### FAILURE 6 — `WAKE_WORD` expression is always `"hey robot"`
**Root cause:** In `voice_brain.py`:
```python
WAKE_WORD = "hey robot" or "robot" or "autobot"
```
Python `or` on strings returns the first truthy string. This always evaluates to `"hey robot"`. The alternatives are silently ignored.  
**Fix:**
```python
WAKE_WORDS = ["hey robot", "robot", "autobot"]
# Then in _loop check:
if any(w in t for w in WAKE_WORDS):
```

---

### FAILURE 7 — `search_mode.py` Gemini Vision sends raw bytes inline
**Root cause:** The `generate_content()` call passes image data as a plain dict `{"mime_type": ..., "data": bytes}`. The correct format for `google-generativeai >= 0.5` is to use `PIL.Image` or `genai.types.Part`.  
**Fix:**
```python
from google.generativeai.types import Part
image_part = Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
response = self.vision_model.generate_content([prompt, image_part])
```

---

### FAILURE 8 — `LCDDisplay` fails silently if `RPLCD` not installed
**Root cause:** The LCD init catches `ImportError` and logs it, but `self.lcd` stays `None`. All subsequent calls (`show_mode()`, etc.) silently do nothing. This is handled — but the robot will boot with no LCD output and no visible warning to the user.  
**Fix (already handled in code):** Already safe — add one startup check in `main.py`:
```python
if self.lcd.lcd is None:
    logger.warning("LCD not available — running without display.")
```

---

### FAILURE 9 — `socket.gethostbyname(socket.gethostname())` returns `127.0.0.1`
**Root cause:** On Raspberry Pi, `gethostbyname(gethostname())` often resolves to `127.0.0.1` (loopback), not the actual WiFi IP.  
**Fix:**
```python
import socket
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "Check router"
    finally:
        s.close()
```

---

### FAILURE 10 — `home_automation.py` not started anywhere
**Root cause:** `HomeAutomationController` is defined but never instantiated or started in `main.py`. The voice brain calls `send_command()` directly but the background listener is never running.  
**Fix:** Add to `main.py` in `__init__`:
```python
from communication.home_automation import HomeAutomationController
self.home_ctrl = HomeAutomationController()
# No need to call start() since VoiceBrain handles it via send_command() directly.
```
The `send_command()` import in voice_brain already works — this is a minor note only.

---

### FAILURE 11 — `US_DOWN_TRIG` on GPIO 0 / `US_DOWN_ECHO` on GPIO 1
**Root cause:** GPIO 0 and 1 are I2C ID EEPROM pins, reserved on Pi HATs. They work for normal I/O only if no HAT is attached, but are unreliable.  
**Fix:** Reassign in `config.py`:
```python
"US_DOWN_TRIG": 20,   # GPIO 20
"US_DOWN_ECHO": 21,   # GPIO 21
```

---

### FAILURE 12 — `VisionDriveMode` `use_yolo=True` blocks Pi at startup
**Root cause:** YOLOv8 model download (~6 MB) happens on first run. On a Pi with no internet or slow internet this hangs the constructor for 30+ seconds.  
**Fix:** Lazy-load YOLO in a background thread:
```python
def _lazy_load_yolo(self):
    threading.Thread(target=self.yolo._load_model, daemon=True).start()
```

---

### FAILURE 13 — `pet_mode.py` and `rescue_mode.py` both call `speaker.speak()` from background thread
**Root cause:** `pyttsx3` is not thread-safe. Calling `engine.say()` from a non-main thread can cause `RuntimeError: run loop already started`.  
**Fix:** Use a thread-safe speak queue:
```python
# In speaker_output.py, add a queue-based speak method
import queue, threading
_q = queue.Queue()
def _worker():
    while True:
        text = _q.get()
        engine.say(text); engine.runAndWait()
threading.Thread(target=_worker, daemon=True).start()

def speak(self, text):
    _q.put(text)
```

---

### FAILURE 14 — `index.html` mic button only triggers `callPet()`
**Root cause:** The web speech recognition only routes to `callPet()`. It has no connection to the new APIs: rescue, search, chatbot, vision drive, home automation lights, or modes.  
**Status: ❌ index.html is NOT ready for the full feature set.**

---

## 5. index.html Readiness Assessment

| Feature | index.html support | Status |
|---|---|---|
| Motor D-pad | ✅ `/api/control` | ✅ Ready |
| Camera servo D-pad | ✅ `/api/camera` | ✅ Ready |
| Pet mode call | ✅ `/api/pet/call` | ✅ Ready |
| Mode switching | ❌ Not present | ❌ Missing |
| Rescue bot | ❌ Not present | ❌ Missing |
| Search bot | ❌ Not present | ❌ Missing |
| Vision drive | ❌ Not present | ❌ Missing |
| Home automation (lights/door) | ❌ Not present | ❌ Missing |
| AI chatbot (text) | ❌ Not present | ❌ Missing |
| System status display | ❌ Not present | ❌ Missing |

**The current `index.html` covers about 30% of the system. The remaining 70% needs to be added.**

> See the updated `index.html` — a complete replacement has been prepared with all features wired in.

---

## 6. Summary: Things to Fix Now

| Priority | Issue | File | Fix |
|---|---|---|---|
| 🔴 Critical | `smbus` import | `sensors/gyroscope.py` | Use `smbus2` |
| 🔴 Critical | pyttsx3 not thread-safe | `audio/speaker_output.py` | Queue-based speaker |
| 🔴 Critical | Gemini Vision image format | `modes/search_mode.py` | Use `Part.from_bytes()` |
| 🟡 High | WAKE_WORD `or` bug | `audio/voice_brain.py` | Use list + `any()` |
| 🟡 High | IP shows 127.0.0.1 | `main.py` | Use UDP socket method |
| 🟡 High | GPIO 0/1 reserved | `utils/config.py` | Change to GPIO 20/21 |
| 🟡 High | Servo jitter | `actuators/servo.py` | Add `ChangeDutyCycle(0)` |
| 🟠 Medium | YOLO blocks boot | `modes/vision_drive_mode.py` | Lazy load in thread |
| 🟠 Medium | GPIO.setmode dupe | `actuators/motors.py`, `servo.py` | Move to `main.py` only |
| 🟢 Low | GPIO 0/1 down sensor | `utils/config.py` | Move to GPIO 20/21 |
| 🟢 Low | LCD None warning | `main.py` | Add startup check log |
