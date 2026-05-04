# 🎓 Comprehensive Technical Project Report

**Project Title:** Vision-Driven Autonomous IoT Robotic Platform with Multimodal AI and Home Automation Integration  
**Core Technologies:** Raspberry Pi 4, ESP32 (NodeMCU), Python, OpenCV, YOLOv8, Google Gemini AI, Flask REST API.

---

## 1. Abstract & Introduction
This project presents a highly modular, multipurpose autonomous robotic platform. Unlike traditional remote-controlled vehicles, this system acts as an edge-computing device capable of processing environmental data in real-time. It integrates hardware sensors (ultrasonic, gyroscope), computer vision (lane detection, object recognition), artificial intelligence (LLM-based natural language processing and vision analysis), and IoT connectivity (controlling home appliances via a secondary ESP32 node).

---

## 2. Hardware Architecture & Components

The physical architecture is divided into the **Main Edge Node** (Robot) and the **IoT Peripheral Node** (Home Automation).

### Main Edge Node (Raspberry Pi 4)
*   **Compute:** Raspberry Pi 4 Model B (Broadcom BCM2711, Quad-core Cortex-A72). Acts as the central orchestrator.
*   **Locomotion:** L298N Dual H-Bridge Motor Driver controlling DC gear motors via high-frequency PWM signals.
*   **Spatial Awareness:** 4× HC-SR04 Ultrasonic Sensors. Configured for Front, Left, Right, and Downward (cliff detection). ECHO pins are stepped down to 3.3V using 1kΩ/2kΩ voltage dividers to protect the Pi's GPIO.
*   **Inertial Measurement:** MPU6050 6-DOF Gyroscope and Accelerometer, communicating via the I2C-1 bus (SDA/SCL) at address `0x68`. Used for rough terrain detection.
*   **Visual Input:** CSI Pi Camera / USB Webcam capturing frames continuously via a dedicated background thread to prevent IO blocking.
*   **Articulations:** Two SG90/MG996R Servos configured in a Pan-Tilt mechanism for the camera, controlled via PWM duty cycle mapping (2% to 12%). Powered by an isolated Buck Converter to prevent Pi brownouts.
*   **Audio I/O:** USB Microphone for voice command capture and a raw 2-wire coil speaker driven by a PAM8403 Class-D audio amplifier.
*   **Human-Machine Interface (HMI):** 16×2 Character LCD with a PCF8574 I2C backpack (Address `0x27`) sharing the bus with the MPU6050.

### IoT Peripheral Node (ESP32 / NodeMCU)
*   **Microcontroller:** ESP32 handling Wi-Fi connectivity.
*   **Actuators:** 4-Channel 5V Relay Module controlling mains-voltage appliances (3 Lights, 1 Door lock).
*   **Protocol:** Operates an asynchronous HTTP Web Server handling REST `GET` requests from the Raspberry Pi.

---

## 3. Software Architecture & Multi-threading

The software stack is written entirely in Python, emphasizing concurrency and non-blocking operations.

### Multi-threading Model
To ensure the robot can drive, stream video, and process AI commands simultaneously, the system uses the `threading` module heavily:
1.  **Main Thread:** Orchestrates the system and handles graceful shutdowns (`cleanup()`).
2.  **Camera Thread:** Continuously captures frames into a `self.frame` buffer, ensuring the latest frame is always available in $O(1)$ time without blocking other processes.
3.  **Flask API Thread:** Runs the Werkzeug WSGI web server on port 5000, serving the HTML dashboard and exposing REST endpoints (`/api/control`, `/api/chat`).
4.  **Voice Brain Thread:** Continuously polls the microphone via `speech_recognition`, processes audio, and routes logic.
5.  **Mode Threads:** When an autonomous mode (e.g., Rescue Mode) is activated, it spawns its own background loop thread.
6.  **Speaker Queue Thread:** `pyttsx3` TTS is not thread-safe. A dedicated worker thread consumes string messages from a thread-safe `queue.Queue()`, preventing race conditions.

---

## 4. Artificial Intelligence & NLP Subsystem

### The Voice Brain (`voice_brain.py`)
This module is the NLP entry point. Audio is transcribed to text using the Google Speech Recognition API.
*   **Deterministic Routing:** Transcriptions are checked against a predefined `COMMAND_MAP` using substring matching. If a match is found, specific hardware interrupts are triggered (e.g., `motors.forward()`, or sending an HTTP request to the ESP32).
*   **Generative AI Fallback:** If the utterance does not match a hardcoded command, it is passed to **Google Gemini 1.5 Flash**. The LLM is prompted with a system persona ("ARIA, the robot assistant") and maintains conversational context. Its text response is then piped to the TTS engine and spoken aloud.

---

## 5. Computer Vision & Machine Learning Methodology

All vision logic is encapsulated in independent, stateless classes within `camera_vision.py`.

### 1. Lane Following (Classical Computer Vision)
*   **Algorithm:** Canny Edge Detection + Contour Analysis.
*   **Methodology:** The frame is converted to grayscale, blurred, and cropped to the Region of Interest (ROI) — typically the bottom 40% of the frame. Thresholding isolates the road lines.
*   **Calculation:** The centroid (Moments) of the largest contour is calculated. The $X$-coordinate of this centroid is compared to the frame's center to compute an `offset` (-1.0 to +1.0), which dictates steering severity.

### 2. Obstacle Detection (Monocular Depth Heuristics)
*   **Methodology:** Because a single camera lacks depth perception, the system looks for large, sudden contours in the lowest part of the frame. If an object occupies a massive pixel area at the bottom of the frame, it is mathematically assumed to be physically close to the lens.

### 3. Object Detection (Deep Learning)
*   **Model:** YOLOv8-nano (You Only Look Once) via the `ultralytics` library.
*   **Methodology:** YOLO divides the image into an $S \times S$ grid and predicts bounding boxes and class probabilities simultaneously. We use the 'nano' model for maximum inference speed on the Raspberry Pi's ARM CPU. It is utilized in `VisionDriveMode` to detect 'stop signs', 'traffic lights', and 'persons' to trigger emergency braking.

### 4. Multimodal Search (Gemini Vision)
*   Used in `SearchMode`. The robot captures a frame, encodes it as a JPEG byte array, wraps it in a PIL Image object, and sends it to the Gemini Multimodal API with a prompt like: *"Look at this image. Is the target 'red bag' visible?"*. This allows for zero-shot object detection of items YOLO wasn't explicitly trained on.

---

## 6. The Autonomous Modes

The system architecture allows dynamic swapping of "Personalities" (Modes) at runtime without restarting the script.

1.  **Autonomous Mode:** Relies strictly on HC-SR04 ultrasonic sensors. Uses reactive obstacle avoidance logic (If front < 30cm, turn left/right based on side sensor clearance).
2.  **Vision Drive Mode:** A priority-based fusion engine. Priority 1: YOLO Stop Signs (Stop). Priority 2: Camera Obstacles (Reverse & Turn). Priority 3: Lane Offset (Steer).
3.  **Surveillance Mode:** Uses OpenCV Background Subtraction (`cv2.absdiff`) to detect motion in a static frame. If pixel delta > threshold, it triggers an alarm.
4.  **Rescue Mode:** Utilizes Haar Cascades (`haarcascade_frontalface_default.xml`) to detect human faces in disaster scenarios.
5.  **Search Mode:** Uses the Gemini Vision API methodology (described above) while executing a hardcoded expanding-square search algorithm via the motors.
6.  **Pet Mode:** Detects faces, calculates bounding box area to estimate distance, and dynamically adjusts motor PWM to maintain a set distance from the user (following behavior).

---

## 7. IoT & Home Automation Protocol

The integration between the Robot and the Home is decoupled via REST APIs over the local WLAN.
*   **ESP32 Firmware:** Runs an asynchronous web server.
*   **Endpoints:** `/light/<1/2/3>/<on/off>` and `/door/4/<on/off>`.
*   **Execution Flow:** User speaks *"Turn on light 1"* $\rightarrow$ Mic captures audio $\rightarrow$ Voice Brain parses command $\rightarrow$ `requests.get("http://<ESP32_IP>/light/1/on")` is executed $\rightarrow$ ESP32 pulls GPIO 5 HIGH $\rightarrow$ Transistor switches 5V Relay $\rightarrow$ 220V Mains circuit is completed $\rightarrow$ Bulb turns on.

---

## 8. Conclusion & Future Scope

**Conclusion:** The project successfully demonstrates the fusion of deterministic edge-computing (sensor-based navigation) with probabilistic cloud-computing (LLMs and Multimodal AI). By maintaining a modular architecture, the system prevents hardware blocking and ensures real-time responsiveness.

**Future Enhancements:**
1.  **SLAM (Simultaneous Localization and Mapping):** Upgrading from reactive ultrasonic navigation to 2D LiDAR-based mapping using ROS (Robot Operating System).
2.  **Edge TPU:** Adding a Google Coral USB Accelerator to offload YOLOv8 inferencing from the Pi CPU to dedicated tensor hardware, increasing FPS from ~3 to ~30.
3.  **Kinematics:** Implementing PID (Proportional-Integral-Derivative) controllers for smoother motor acceleration and deceleration.
