# Wiring Guide

| Component | Component Pin | Raspberry Pi Pin / Connection |
| :--- | :--- | :--- |
| **L298N Motor Driver** | ENA | Pin 32 (GPIO 12) |
| | IN1 | Pin 29 (GPIO 5) |
| | IN2 | Pin 31 (GPIO 6) |
| | IN3 | Pin 37 (GPIO 26) |
| | IN4 | Pin 35 (GPIO 19) |
| | ENB | Pin 33 (GPIO 13) |
| | GND | Pin 6 (GND) & Battery GND |
| | 12V | Battery + |
| **Ultrasonic Front** | VCC | Pin 2 (5V) |
| | TRIG | Pin 11 (GPIO 17) |
| | ECHO | Pin 13 (GPIO 27) (via divider) |
| | GND | Pin 14 (GND) |
| **Ultrasonic Back** | VCC | Pin 2 (5V) |
| | TRIG | Pin 15 (GPIO 22) |
| | ECHO | Pin 19 (GPIO 10) (via divider) |
| | GND | Pin 20 (GND) |
| **Ultrasonic Down** | VCC | Pin 4 (5V) |
| | TRIG | Pin 21 (GPIO 9) |
| | ECHO | Pin 23 (GPIO 11) (via divider) |
| | GND | Pin 25 (GND) |
| **Servo PAN** | Signal | Pin 38 (GPIO 20) |
| | VCC | 5V BEC |
| | GND | Pin 39 (GND) |
| **Servo TILT** | Signal | Pin 40 (GPIO 21) |
| | VCC | 5V BEC |
| | GND | Pin 39 (GND) |
| **MPU6050** | VCC | Pin 1 (3.3V) |
| | GND | Pin 6 (GND) |
| | SDA | Pin 3 (GPIO 2) |
| | SCL | Pin 5 (GPIO 3) |
| **I2C LCD** | VCC | Pin 2 (5V) |
| | GND | Pin 6 (GND) |
| | SDA | Pin 3 (GPIO 2) |
| | SCL | Pin 5 (GPIO 3) |
| **DHT11** | VCC | Pin 1 (3.3V) |
| | DATA | Pin 7 (GPIO 4) |
| | GND | Pin 9 (GND) |
| **GPS** | VCC | Pin 1 (3.3V) |
| | TX | USB UART Adapter RX |
| | RX | USB UART Adapter TX |
| | GND | Pin 14 (GND) |
| **Buzzer** | + | Pin 12 (GPIO 18) |
| | - | Pin 14 (GND) |
| **LED Red** | Anode | Pin 16 (GPIO 23) |
| | Cathode | Pin 20 (GND) |
| **LED Green** | Anode | Pin 18 (GPIO 24) |
| | Cathode | Pin 20 (GND) |
| **LED Blue** | Anode | Pin 22 (GPIO 25) |
| | Cathode | Pin 25 (GND) |
| **Sound Sensor** | VCC | Pin 4 (5V) |
| | GND | Pin 9 (GND) |
| | D0 | Pin 24 (GPIO 8) |
| **Camera** | Data | USB / CSI Connector |
| **Speaker** | Audio | USB Sound Card / 3.5mm Jack (via PAM8403) |
| **ESP32 (External)** | Relay IN1 | GPIO 5 |
| | Relay IN2 | GPIO 2 |
| | Relay IN3 | GPIO 3 |
| | Relay IN4 | GPIO 18 |
