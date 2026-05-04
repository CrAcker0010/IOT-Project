# 🤖 IOT Robot — Voice Command & Feature Guide

> **How it works:**  
> Speak to the Raspberry Pi microphone. The robot parses your speech, executes the matching action, and speaks a reply back to you. If nothing matches, the built-in **Gemini AI chatbot** (ARIA) answers your question.

---

## 🗣️ Wake Word

Before every command, say:

```
"Hey robot"
```

> You can disable the wake word in `audio/voice_brain.py` by setting `WAKE_WORD = None` to make the robot always listen.

---

## 🚗 Robot Driving Modes

These commands switch the robot's operating personality.

| What you say | What happens |
|---|---|
| *"autonomous mode"* / *"start autonomous"* / *"self drive"* | Ultrasonic sensor-based obstacle avoidance (no camera) |
| *"vision drive"* / *"camera drive"* / *"drive with camera"* | Camera-based driving using lane detection + YOLO |
| *"pet mode"* / *"act like a pet dog"* | Robot wanders playfully, seeks owner's face |
| *"surveillance mode"* / *"guard mode"* / *"security mode"* | Camera monitors area, alerts on motion |
| *"rescue mode"* / *"find survivors"* / *"rescue bot"* | Navigates area searching for human faces (survivors) |
| *"search mode"* / *"find object"* / *"search bot"* | Uses Gemini Vision to hunt for a target you describe |
| *"stop"* / *"halt"* / *"idle"* / *"abort"* | Stops all motors and returns to standby |
| *"sleep"* / *"go to sleep"* / *"standby"* | Enters standby mode |

---

## 🎮 Manual Movement Controls

| What you say | What happens |
|---|---|
| *"move forward"* / *"go forward"* / *"go ahead"* | Drives forward at 50% speed |
| *"move backward"* / *"reverse"* / *"back up"* | Drives backward |
| *"turn left"* / *"go left"* | Left turn |
| *"turn right"* / *"go right"* | Right turn |
| *"stop moving"* / *"motors off"* | Stops motors immediately |

---

## 📷 Camera & Servo Controls

| What you say | What happens |
|---|---|
| *"look up"* / *"camera up"* / *"tilt up"* | Tilts camera servo upward by 15 degrees |
| *"look down"* / *"camera down"* / *"tilt down"* | Tilts camera servo downward |
| *"look left"* / *"camera left"* / *"pan left"* | Pans camera servo to the left |
| *"look right"* / *"camera right"* / *"pan right"* | Pans camera servo to the right |
| *"center camera"* / *"reset camera"* / *"look ahead"* | Returns both servos to 90 degrees |

---

## 💡 Home Automation (via NodeMCU WiFi)

> Raspberry Pi sends an HTTP request to the NodeMCU ESP32.
> Make sure `NODEMCU_IP` is set correctly in `utils/config.py`.

| What you say | What happens |
|---|---|
| *"turn on light 1"* / *"light one on"* | Turns on relay → Light 1 |
| *"turn off light 1"* / *"light 1 off"* | Turns off relay → Light 1 |
| *"turn on light 2"* / *"light two on"* | Turns on relay → Light 2 |
| *"turn off light 2"* / *"light 2 off"* | Turns off relay → Light 2 |
| *"turn on light 3"* / *"light three on"* | Turns on relay → Light 3 |
| *"turn off light 3"* / *"light 3 off"* | Turns off relay → Light 3 |
| *"turn off all"* / *"all lights off"* / *"everything off"* | Turns all 3 lights OFF |
| *"open door"* / *"unlock door"* / *"open gate"* | Opens Door relay (GPIO 18) |
| *"close door"* / *"lock door"* / *"shut door"* | Closes Door relay |

---

## ℹ️ System Information Commands

| What you say | What happens |
|---|---|
| *"what mode"* / *"current mode"* / *"what are you doing"* | Robot reports its current mode |
| *"status"* / *"system status"* / *"report status"* | Reports mode + camera state |
| *"what can you do"* / *"help"* / *"list commands"* | Robot lists all capabilities |
| *"who are you"* / *"introduce yourself"* | Robot introduces itself as ARIA |

---

## 🤖 AI Chatbot (ARIA)

Any phrase that **does not match** a command above is sent directly to the **Gemini AI chatbot**. ARIA will:

- Answer general questions
- Explain what voice commands to use
- Have a natural conversation

**Examples you can say:**
```
"Hey robot, what is the weather like?"
"Hey robot, how does YOLO work?"
"Hey robot, tell me a joke"
"Hey robot, what should I search for?"
"Hey robot, explain what rescue mode does"
```

### Web Chat UI (text-based)

```
POST http://<raspberry-pi-ip>:5000/api/chat
Content-Type: application/json
Body: { "message": "What mode are you in?" }

Response: { "reply": "I am currently in autonomous mode." }
```

---

## 🏗️ Project File Structure

```
IOT-Project/
│
├── main.py                       ← Main entry point, boots the entire system
│
├── audio/
│   ├── voice_brain.py            ← Central voice + chatbot brain (KEY FILE)
│   ├── mic.py                    ← Microphone input (Google Speech Recognition)
│   └── speaker_output.py         ← Text-to-speech output (pyttsx3 / espeak)
│
├── modes/
│   ├── autonomous_mode.py        ← Ultrasonic obstacle avoidance navigation
│   ├── pet_mode.py               ← Face-following pet robot
│   ├── surveillance_mode.py      ← Camera monitoring + motion detection
│   ├── rescue_mode.py            ← Face detection survivor search
│   ├── search_mode.py            ← Gemini Vision target search
│   └── vision_drive_mode.py      ← Camera-based autonomous driving (lane + YOLO)
│
├── vision/
│   ├── camera_stream.py          ← Live camera capture thread
│   └── camera_vision.py          ← 3 callable vision functions:
│                                     LaneFollower.analyze(frame)
│                                     CameraObstacleDetector.analyze(frame)
│                                     YOLODetector.analyze(frame)
│
├── communication/
│   ├── nodemcu.ino               ← Flash this to ESP32/NodeMCU
│   ├── home_automation.py        ← HTTP command sender to NodeMCU
│   └── web_server.py             ← Flask web dashboard + REST API
│
├── actuators/
│   ├── motors.py                 ← L298N motor driver
│   └── servo.py                  ← Pan/tilt servo control
│
├── sensors/
│   ├── ultrasonic.py             ← HC-SR04 distance sensor
│   ├── gyroscope.py              ← MPU6050 IMU
│   └── gps.py                    ← GPS UART reader
│
└── utils/
    ├── config.py                 ← All pins, IPs, settings (edit this first)
    └── logger.py                 ← Logging utility
```

---

## ⚙️ Configuration Quick Reference (`utils/config.py`)

| Setting | Default | What to change |
|---|---|---|
| `NODEMCU_IP` | `192.168.1.100` | IP shown on NodeMCU Serial Monitor after flashing |
| `NODEMCU_BAUD` | `9600` | Leave as-is (matches `nodemcu.ino`) |
| `MOTOR_SPEED_DEFAULT` | `50` | 0 to 100 PWM duty cycle |
| `OBSTACLE_THRESHOLD_CM` | `30` | Distance to start turning |
| `DANGER_THRESHOLD_CM` | `15` | Distance for emergency stop |
| `CAMERA_RESOLUTION` | `(640, 480)` | Reduce for faster YOLO on Pi |
| `STREAM_PORT` | `5000` | Web dashboard port |
| `GEMINI_API_KEY` | env var | Run: `export GEMINI_API_KEY=your_key` |

---

## 🌐 Web API Endpoints

All endpoints accept `POST` with a JSON body.

| Endpoint | Body Example | Description |
|---|---|---|
| `/api/control` | `{"command":"forward","speed":50}` | Manual motor control |
| `/api/camera` | `{"command":"left"}` | Servo pan/tilt |
| `/api/rescue` | `{"action":"start"}` | Rescue bot on/off |
| `/api/search` | `{"action":"start","target":"red bag"}` | Search bot on/off |
| `/api/vision_drive` | `{"action":"start"}` | Camera-drive on/off |
| `/api/vision/check` | `{"checks":["lane","obstacle","yolo"]}` | One-shot vision check |
| `/api/chat` | `{"message":"hello"}` | Text chatbot, returns `reply` |
| `/api/pet/call` | *(empty body)* | Activate pet mode |
| `/video_feed` | GET only | MJPEG live camera stream |

---

## 🔌 Hardware Setup Summary

```
Raspberry Pi 4
├── L298N Motor Driver    ← GPIO 5, 6, 12, 13, 19, 26
├── Ultrasonic (Front)    ← TRIG GPIO 17 / ECHO GPIO 27
├── Ultrasonic (Left)     ← TRIG GPIO 22 / ECHO GPIO 10
├── Ultrasonic (Right)    ← TRIG GPIO 9  / ECHO GPIO 11
├── MPU6050 Gyroscope     ← I2C SDA GPIO 2 / SCL GPIO 3
├── Pan Servo             ← GPIO 14
├── Tilt Servo            ← GPIO 15
├── DHT11 Sensor          ← GPIO 4
├── Camera Module or USB  ← /dev/video0
├── USB Microphone        ← speech_recognition default device
├── Speaker               ← 3.5mm jack or USB
└── GPS Module            ← /dev/serial0 (UART)

NodeMCU ESP32 (WiFi — same network as Pi)
├── Relay 1 (Light 1)     ← GPIO 5
├── Relay 2 (Light 2)     ← GPIO 2
├── Relay 3 (Light 3)     ← GPIO 3
└── Relay 4 (Door)        ← GPIO 18
```

---

## 🚀 Starting the System

```bash
# 1. Install all Python dependencies on the Pi
pip install -r requirements.txt

# 2. Set your Gemini API key
export GEMINI_API_KEY="your_api_key_here"

# 3. Flash nodemcu.ino to your ESP32 via Arduino IDE
#    (Set WiFi SSID and password inside the file first)

# 4. Update NODEMCU_IP in utils/config.py

# 5. Start the robot
python main.py
```

The system will:
1. Initialize all hardware
2. Greet you out loud
3. Start the web dashboard at `http://<pi-ip>:5000`
4. Begin listening for voice commands

---

## 🔊 Voice Command Flow

```
You speak
    │
    ▼
MicInput.listen()  ──── Google Speech API ────► Text string
    │
    ▼
VoiceBrain.process_utterance(text)
    │
    ├── Wake word check ("hey robot")
    │       Not heard? → Ignore
    │
    ├── Match against COMMAND_MAP?
    │       YES → _execute_action()
    │              ├── Change mode (autonomous / rescue / search ...)
    │              ├── Drive motors (forward / left / right ...)
    │              ├── Move servos (pan / tilt)
    │              └── Send HTTP to NodeMCU (lights / door)
    │              └──► speaker.speak(confirmation reply)
    │
    └── NO match → Gemini Chatbot (ARIA)
                       └──► speaker.speak(AI reply)
```

---

*IOT-Project | Raspberry Pi 4 + NodeMCU ESP32 | May 2026*
