# 🤖 IOT Autonomous Multipurpose Robot

A Raspberry Pi 4 powered autonomous robot with AI brain (Google Gemini), camera vision, voice control, home automation, and 6 operating modes.

## 🛠 Hardware Required

| Component | Purpose |
|---|---|
| Raspberry Pi 4 | Main controller |
| L298N Motor Driver + DC Motors | Movement |
| 3× HC-SR04 Ultrasonic Sensors | Front (sweeper), Back, Down (cliff) |
| SG90 Pan-Tilt Servo Kit | Camera + front sensor rotation |
| Pi Camera / USB Webcam | Live video + vision AI |
| MPU6050 Gyroscope (I2C) | Road quality detection |
| KY-037 Sound Sensor | Clap detection |
| 16×2 I2C LCD (PCF8574) | Status display |
| Speaker (3.5mm / USB) | Voice output (pyttsx3/espeak) |
| ESP32/NodeMCU (optional) | Home automation relay control |

> See **WIRING_GUIDE.md** for full pin-by-pin wiring diagrams.

## 🚀 Quick Start (on Raspberry Pi)

```bash
# 1. Clone the project
git clone <your-repo-url>
cd IOT-Project

# 2. Run setup (installs everything)
chmod +x setup.sh run.sh
./setup.sh

# 3. Set your Gemini API key (optional, AI features need this)
export GEMINI_API_KEY="your-google-ai-key"

# 4. Start the robot
./run.sh
```

Dashboard opens at: **http://\<Pi-IP\>:5000**

## 📱 Web Dashboard

Open the dashboard from any phone/laptop on the same WiFi:
- **Live camera** feed with rotation
- **D-pad controls** for movement + camera pan/tilt
- **Mode switcher** for all 6 modes
- **AI Chatbot** (ARIA) — type or speak commands
- **Home automation** — control lights + door via NodeMCU
- **Voice commands** via browser Speech API (🎤 button)
- **Keyboard shortcuts** — Arrow keys to drive, Space to stop

## 🧠 Operating Modes

| Mode | Description |
|---|---|
| 🧭 **Autonomous** | Ultrasonic sweeper navigation + cliff detection |
| 📷 **Vision Drive** | Camera-based driving: lane follow + obstacle detect + YOLO |
| 🐕 **Pet Mode** | Robot dog: random wiggles, face following, AI personality |
| 👁 **Surveillance** | Security guard: monitors camera, periodic reports |
| 🆘 **Rescue Bot** | Navigates + searches for human faces (survivors) |
| 🔍 **Search Bot** | Gemini Vision AI finds any target object you name |

## 👏 Clap Commands (Physical)

| Claps | Action |
|---|---|
| 1 | Emergency stop |
| 2 | Toggle autonomous mode |
| 3 | Toggle rescue mode |
| 4 | Toggle search mode |

## 💡 Home Automation (NodeMCU)

1. Flash `communication/nodemcu.ino` to your ESP32/ESP8266
2. Set WiFi credentials in the `.ino` file
3. Update `NODEMCU_IP` in `utils/config.py` with the ESP's IP
4. Control 3 lights + 1 door from the dashboard or voice commands

## 📁 Project Structure

```
IOT-Project/
├── main.py                    # Entry point
├── setup.sh / run.sh          # Install & launch scripts
├── requirements.txt           # Python dependencies
├── safety_limits.json         # Motor/servo safety caps
│
├── actuators/
│   ├── motors.py              # L298N motor driver
│   └── servo.py               # Pan-tilt servo control
│
├── sensors/
│   ├── ultrasonic.py          # HC-SR04 distance sensor
│   ├── sweeper_sonar.py       # Servo-mounted sweeping sonar
│   ├── gyroscope.py           # MPU6050 accelerometer
│   └── gps.py                 # GPS module (UART)
│
├── audio/
│   ├── speaker_output.py      # Thread-safe TTS engine
│   ├── voice_brain.py         # Command dispatcher + Gemini chatbot
│   └── clap_detector.py       # Physical clap pattern detection
│
├── vision/
│   ├── camera_stream.py       # Threaded camera capture
│   └── camera_vision.py       # Lane follower, obstacle detector, YOLO
│
├── modes/
│   ├── autonomous_mode.py     # Ultrasonic navigation
│   ├── vision_drive_mode.py   # Camera-based autonomous driving
│   ├── pet_mode.py            # Robot pet personality
│   ├── surveillance_mode.py   # Security monitoring
│   ├── rescue_mode.py         # Survivor search
│   └── search_mode.py         # AI-powered object search
│
├── communication/
│   ├── web_server.py          # Flask dashboard + REST API
│   ├── home_automation.py     # NodeMCU HTTP controller
│   └── nodemcu.ino            # ESP32/ESP8266 firmware
│
├── intelligence/
│   └── gemini_agent.py        # Standalone Gemini wrapper
│
├── utils/
│   ├── config.py              # Pins, settings, API keys
│   ├── logger.py              # Logging to file + console
│   └── lcd_display.py         # I2C LCD driver
│
└── templates/
    └── index.html             # Web dashboard UI
```

## ⚙️ Configuration

Edit `utils/config.py` to change:
- **GPIO pin assignments** — match your wiring
- **Motor speed defaults** — tune for your chassis
- **Obstacle thresholds** — cm distances for danger/warning
- **Camera resolution** — 640×480 default
- **NodeMCU IP** — after flashing the ESP
- **Gemini API key** — or set `GEMINI_API_KEY` env var

## 📝 License

Educational / personal project.