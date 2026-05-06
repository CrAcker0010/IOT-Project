# Wiring Guide

## Power Distribution (Breadboard Rails)
To keep wiring clean and manageable, use the power lanes on your breadboard:
* **5V Rail**: Connect Raspberry Pi Pin 2 or 4 (5V) to the breadboard's red (+) lane.
* **3.3V Rail**: Connect Raspberry Pi Pin 1 or 17 (3.3V) to a separate breadboard red (+) lane.
* **GND Rail**: Connect Raspberry Pi Pin 6, 9, or 14 (GND) to the breadboard's blue/black (-) lane. Connect the Battery GND and 5V BEC GND here as well for a common ground.

| Component | Component Pin | Raspberry Pi Pin / Connection |
| :--- | :--- | :--- |
| **L298N Motor Driver** | ENA | Pin 32 (GPIO 12) |
| | IN1 | Pin 29 (GPIO 5) |
| | IN2 | Pin 31 (GPIO 6) |
| | IN3 | Pin 37 (GPIO 26) |
| | IN4 | Pin 35 (GPIO 19) |
| | ENB | Pin 33 (GPIO 13) |
| | GND | GND Breadboard Rail |
| | 12V | Battery + |
| **Ultrasonic Front** | VCC | 3.3V Breadboard Rail (Workaround) |
| | TRIG | Pin 21 (GPIO 9) |
| | ECHO | Pin 23 (GPIO 11) |
| | GND | GND Breadboard Rail |
| **Ultrasonic Back** 
| VCC | 3.3V Breadboard Rail (Workaround) |
| | TRIG | Pin 15 (GPIO 22) |
| | ECHO | Pin 19 (GPIO 10) |
| | GND | GND Breadboard Rail |
| **Ultrasonic Down** | VCC | 3.3V Breadboard Rail (Workaround) |
| | TRIG | Pin 11 (GPIO 17) |
| | ECHO | Pin 13 (GPIO 27) |
| | GND | GND Breadboard Rail |
| **Servo PAN** | Signal | Pin 38 (GPIO 20) |
| | VCC | 5V BEC |
| | GND | GND Breadboard Rail |
| **Servo TILT** | Signal | Pin 40 (GPIO 21) |
| | VCC | 5V BEC |
| | GND | GND Breadboard Rail |
| **MPU6050** | VCC | 3.3V Breadboard Rail |
| | GND | GND Breadboard Rail |
| | SDA | Pin 3 (GPIO 2) |
| | SCL | Pin 5 (GPIO 3) |
| **I2C LCD** | VCC | 5V Breadboard Rail |
| | GND | GND Breadboard Rail |
| | SDA | Pin 3 (GPIO 2) |
| | SCL | Pin 5 (GPIO 3) |
| **DHT11** | VCC | 3.3V Breadboard Rail |
| | DATA | Pin 7 (GPIO 4) |
| | GND | GND Breadboard Rail |
| **GPS** | VCC | 3.3V Breadboard Rail |
| | TX | USB UART Adapter RX |
| | RX | USB UART Adapter TX |
| | GND | GND Breadboard Rail |
| **Buzzer** | + | Pin 12 (GPIO 18) |
| | - | GND Breadboard Rail |
| **LED Red** | Anode | Pin 16 (GPIO 23) |
| | Cathode | GND Breadboard Rail |
| **LED Green** | Anode | Pin 18 (GPIO 24) |
| | Cathode | GND Breadboard Rail |
| **LED Blue** | Anode | Pin 22 (GPIO 25) |
| | Cathode | GND Breadboard Rail |
| **Sound Sensor** | VCC | 5V Breadboard Rail |
| | GND | GND Breadboard Rail |
| | D0 | Pin 24 (GPIO 8) |
| **Camera** | Data | USB / CSI Connector |
| **Speaker** | Audio | USB Sound Card / 3.5mm Jack (via PAM8403) |
| **ESP32 (External)** | Relay IN1 | GPIO 5 |
| | Relay IN2 | GPIO 2 |
| | Relay IN3 | GPIO 3 |
| | Relay IN4 | GPIO 18 |
