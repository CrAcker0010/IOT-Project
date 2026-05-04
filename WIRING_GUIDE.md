# 🔌 Complete Wiring Guide — IOT Robot

> Every single wire, pin-by-pin. Follow this and plug in.

---

## Raspberry Pi 4 — Pin Reference

```
                    3V3  (1) (2)  5V
          I2C SDA / GPIO2  (3) (4)  5V
          I2C SCL / GPIO3  (5) (6)  GND
                    GPIO4  (7) (8)  GPIO14 / UART TX
                      GND  (9) (10) GPIO15 / UART RX
                   GPIO17 (11) (12) GPIO18
                   GPIO27 (13) (14) GND
                   GPIO22 (15) (16) GPIO23
                    3V3   (17) (18) GPIO24
         SPI MOSI/GPIO10 (19) (20) GND
          SPI MISO/GPIO9 (21) (22) GPIO25
         SPI SCLK/GPIO11 (23) (24) GPIO8
                      GND (25) (26) GPIO7
                   GPIO0  (27) (28) GPIO1
                   GPIO5  (29) (30) GND
                   GPIO6  (31) (32) GPIO12
                  GPIO13  (33) (34) GND
                  GPIO19  (35) (36) GPIO16
                  GPIO26  (37) (38) GPIO20
                      GND (39) (40) GPIO21
```

---

## 1. L298N Motor Driver (2 DC Motors)

The L298N drives 2 motors (left pair + right pair).
Power the L298N with a **separate battery (7–12V)**, NOT from the Pi.

```
L298N            →  Raspberry Pi
─────────────────────────────────────
ENA              →  Pin 32 (GPIO 12)  ← PWM speed left motors
IN1              →  Pin 29 (GPIO 5)
IN2              →  Pin 31 (GPIO 6)
IN3              →  Pin 37 (GPIO 26)
IN4              →  Pin 35 (GPIO 19)
ENB              →  Pin 33 (GPIO 13)  ← PWM speed right motors
GND              →  Pin 6  (GND)     ← ALSO connect to battery GND

L298N Power:
12V              →  Battery + (7–12V)
GND              →  Battery –
5V (output)      →  Can power the Pi (optional, remove jumper first)
```

```
Motor wires:
  Left  motor  →  L298N  OUT1 (+)  and  OUT2 (–)
  Right motor  →  L298N  OUT3 (+)  and  OUT4 (–)
```

> ⚡ **Important:** L298N GND and Pi GND **must** share a common ground.

---

## 2. Ultrasonic Sensors (HC-SR04) × 4

Each sensor has 4 pins: VCC, TRIG, ECHO, GND.

> ⚠️ **ECHO is 5V but Pi GPIO is 3.3V!** Use a voltage divider on each ECHO line:
> `ECHO → 1kΩ resistor → Pi GPIO` and `between Pi GPIO and GND put a 2kΩ resistor`

```
FRONT (Sweeper) sensor:
  VCC   →  Pin 2  (5V)
  TRIG  →  Pin 11 (GPIO 17)
  ECHO  →  Pin 13 (GPIO 27)  ← through 1kΩ/2kΩ voltage divider
  GND   →  Pin 14 (GND)

BACK sensor (for reversing):
  VCC   →  Pin 2  (5V)
  TRIG  →  Pin 15 (GPIO 22)
  ECHO  →  Pin 19 (GPIO 10)  ← through voltage divider
  GND   →  Pin 20 (GND)

DOWN sensor (cliff / stair detection):
  VCC   →  Pin 4  (5V)
  TRIG  →  Pin 21 (GPIO 9)
  ECHO  →  Pin 23 (GPIO 11)  ← through voltage divider
  GND   →  Pin 25 (GND)
```

### Voltage Divider Wiring (for each ECHO pin)

```
HC-SR04 ECHO ──┬── 1kΩ ──── Pi GPIO pin
               │
               2kΩ
               │
              GND
```

This converts the 5V ECHO signal to ~3.3V safe for the Pi.

---

## 3. Servo Motors × 2 (Pan + Tilt for Camera)

Standard hobby servos (SG90 / MG996R) — 3 wires each.

> ⚡ Power servos from 5V **directly from battery or BEC**, NOT from Pi 5V pin (servos draw too much current and will brown-out the Pi).

```
PAN servo (horizontal):
  Signal (Orange/White)  →  Pin 38 (GPIO 20)
  VCC    (Red)           →  5V from BEC / battery regulator
  GND    (Brown/Black)   →  Pin 39 (GND)

TILT servo (vertical):
  Signal (Orange/White)  →  Pin 40 (GPIO 21)
  VCC    (Red)           →  5V from BEC / battery regulator
  GND    (Brown/Black)   →  Pin 39 (GND)
```

---

## 4. MPU6050 Gyroscope / Accelerometer (I2C)

4 wires. Shares the I2C bus with the LCD (different address).

```
MPU6050          →  Raspberry Pi
─────────────────────────────────────
VCC              →  Pin 1  (3.3V)    ← NOT 5V!
GND              →  Pin 6  (GND)
SDA              →  Pin 3  (GPIO 2 / SDA)
SCL              →  Pin 5  (GPIO 3 / SCL)
```

I2C address: **0x68** (default).

---

## 5. I2C LCD Display 16×2 (PCF8574 Backpack)

4 wires. Same I2C bus as MPU6050 — just daisy-chain.

```
LCD              →  Raspberry Pi
─────────────────────────────────────
VCC              →  Pin 2  (5V)      ← LCD needs 5V, not 3.3V
GND              →  Pin 6  (GND)
SDA              →  Pin 3  (GPIO 2 / SDA)  ← same wire as MPU6050
SCL              →  Pin 5  (GPIO 3 / SCL)  ← same wire as MPU6050
```

I2C address: **0x27** (default). If it doesn't work, try **0x3F**.

> 💡 Both MPU6050 and LCD share the same 2 wires (SDA + SCL). This is how I2C works — each device has a unique address.

---

## 6. DHT11 Temperature & Humidity Sensor

3 used pins (some modules have 4 pins, leave the unused one disconnected).

```
DHT11            →  Raspberry Pi
─────────────────────────────────────
VCC  (pin 1)     →  Pin 1  (3.3V)
DATA (pin 2)     →  Pin 7  (GPIO 4)
GND  (pin 4)     →  Pin 9  (GND)

Add a 10kΩ pull-up resistor between DATA and VCC.
```

---

## 7. GPS Module (UART)

4 wires. Uses the Pi's hardware UART.

> ⚠️ You must disable the Pi's serial console first:
> `sudo raspi-config` → Interface Options → Serial Port → Login shell: **No**, Hardware: **Yes**

```
GPS              →  Raspberry Pi
─────────────────────────────────────
VCC              →  Pin 1  (3.3V)    ← check your module! Some need 5V
TX               →  Pin 10 (GPIO 15 / RXD)  ← GPS TX goes to Pi RX
RX               →  Pin 8  (GPIO 14 / TXD)  ← GPS RX goes to Pi TX
GND              →  Pin 14 (GND)
```

> ✅ **NO CONFLICT:** Servos have been moved to GPIO 20/21. GPIO 14 and 15 are now fully available for your GPS module.

---

## 8. 🔊 Speaker (Raw 2-Wire Coil)

Your speaker has **only 2 bare wires going to the voice coil** (no built-in amplifier). Here's the deal:

> ❌ **You CANNOT connect a raw speaker coil directly to the Pi's 3.5mm audio jack.**  
> The Pi's audio output is too weak (~1mW) to drive a bare coil. You'll hear nothing or just a faint whisper.

### What you need: A tiny amplifier module

The cheapest option is a **PAM8403** module (~₹30 / $0.50):

```
PAM8403 Amplifier Module (tiny, 3cm × 3cm board)

Raspberry Pi 3.5mm Audio Jack
    ├── Tip   (Left audio)  → PAM8403 "L IN"
    ├── Ring  (Right audio) → PAM8403 "R IN"
    └── Sleeve (GND)        → PAM8403 "GND"

PAM8403 Power:
    VCC  →  5V (from Pi Pin 4 or battery)
    GND  →  Pi GND (Pin 6)

PAM8403 Speaker Output:
    L OUT +  →  Speaker wire 1
    L OUT –  →  Speaker wire 2
```

### Wiring diagram:

```
Pi 3.5mm jack                    PAM8403                  Speaker
─────────────                 ┌───────────┐             ┌─────────┐
  Tip  ──────────────────────→│ L IN      │             │         │
  Sleeve ────────────────────→│ GND       │   L OUT + ──→│ Wire 1  │
                              │ VCC ←── 5V│   L OUT – ──→│ Wire 2  │
                              └───────────┘             └─────────┘
```

### Alternative (no amplifier needed):

If you don't have a PAM8403, use a **USB sound card** (~₹100):
```
Pi USB port → USB sound card → 3.5mm jack → any powered speaker/earphone
```

The software (`pyttsx3` / `espeak`) outputs audio to the Pi's default audio device automatically. No code changes needed either way.

### Set audio output to 3.5mm jack:

```bash
sudo raspi-config
# → System Options → Audio → 3.5mm Jack (Headphone)
```

---

## 9. Buzzer

Active buzzer (2 pins) — makes a tone when given HIGH signal.

```
Buzzer           →  Raspberry Pi
─────────────────────────────────────
+ (longer leg)   →  Pin 12 (GPIO 18)
– (shorter leg)  →  Pin 14 (GND)
```

---

## 10. Indicator LEDs × 3

Each LED needs a **220Ω–330Ω resistor** in series to limit current.

```
RED LED:
  Anode (+)  → 220Ω resistor → Pin 16 (GPIO 23)
  Cathode (–) → Pin 20 (GND)

GREEN LED:
  Anode (+)  → 220Ω resistor → Pin 18 (GPIO 24)
  Cathode (–) → Pin 20 (GND)

BLUE LED:
  Anode (+)  → 220Ω resistor → Pin 22 (GPIO 25)
  Cathode (–) → Pin 25 (GND)
```

---

## 11. Camera

### Option A — Pi Camera Module (CSI ribbon cable):
```
Ribbon cable → Pi CSI connector (the long slot between HDMI and audio jack)
Lift the black clip → slide ribbon in (blue side facing the USB ports) → press clip down
```

### Option B — USB Webcam:
```
USB webcam → any Pi USB port
```

No code change needed — both show up as `/dev/video0`.

---

## 12. Sound Sensor Module (KY-037/038)

This module has a microphone and a potentiometer to adjust sensitivity. It detects sound presence (like a clap) but **cannot** process spoken words for the AI.

```
Module Pin       →  Raspberry Pi
─────────────────────────────────────
VCC              →  Pin 2 or 4 (5V)
GND              →  Pin 6 or 9 (GND)
D0 (Digital Out) →  Pin 24 (GPIO 8)
A0 (Analog Out)  →  (Leave Disconnected — Pi has no ADC)
```

> 💡 **Usage:** You can use this to make the robot stop if you clap loudly or to wake it up, but you will still need a USB microphone if you want to speak commands like "Go to the kitchen."

---

## 13. NodeMCU ESP32 (WiFi — Home Automation)

The ESP32 is **NOT wired to the Pi**. It communicates via WiFi (HTTP).

### ESP32 → 4-Channel Relay Module

```
ESP32            →  Relay Module
─────────────────────────────────────
GPIO 5           →  IN1 (Light 1)
GPIO 2           →  IN2 (Light 2)
GPIO 3           →  IN3 (Light 3)
GPIO 18          →  IN4 (Door lock)
3.3V or VIN      →  VCC
GND              →  GND

Relay Module → Appliances
─────────────────────────────────────
Relay 1 COM+NO   →  Light 1 (mains wire through relay)
Relay 2 COM+NO   →  Light 2
Relay 3 COM+NO   →  Light 3
Relay 4 COM+NO   →  Door lock solenoid / electronic lock
```

### ESP32 Power:
```
USB cable from any 5V source (power bank, wall adapter, Pi USB)
```

> ⚠️ **Mains electricity (220V) passes through the relay module to the lights. Be EXTREMELY careful. Insulate all connections. If unsure, use 12V LED strips instead of mains bulbs.**

---

## Complete Wiring Summary Table

| Device | Pi Pin # | GPIO # | Wire Color (suggested) |
|---|---|---|---|
| **Motor ENA** | 32 | 12 | Orange |
| **Motor ENB** | 33 | 13 | Orange |
| **Motor IN1** | 29 | 5 | Yellow |
| **Motor IN2** | 31 | 6 | Yellow |
| **Motor IN3** | 37 | 26 | Yellow |
| **Motor IN4** | 35 | 19 | Yellow |
| **US Sweeper TRIG** | 11 | 17 | Blue |
| **US Sweeper ECHO** | 13 | 27 | Green (with divider) |
| **US Back TRIG** | 15 | 22 | Blue |
| **US Back ECHO** | 19 | 10 | Green (with divider) |
| **US Down TRIG** | 21 | 9 | Blue |
| **US Down ECHO** | 23 | 11 | Green (with divider) |
| **DHT11 DATA** | 7 | 4 | White |
| **Servo PAN** | 38 | 20 | Orange |
| **Servo TILT** | 40 | 21 | Orange |
| **Buzzer +** | 12 | 18 | Red |
| **LED Red** | 16 | 23 | Red |
| **LED Green** | 18 | 24 | Green |
| **LED Blue** | 22 | 25 | Blue |
| **MPU6050 SDA** | 3 | 2 | White |
| **MPU6050 SCL** | 5 | 3 | Yellow |
| **LCD SDA** | 3 | 2 | White (same wire) |
| **LCD SCL** | 5 | 3 | Yellow (same wire) |
| **GPS TX→Pi RX** | USB adapter | — | Green |
| **Speaker** | 3.5mm jack | — | via PAM8403 amp |
| **Camera** | CSI or USB | — | Ribbon / USB |
| **Sound Sensor D0** | 24 | 8 | White |
| **Camera** | CSI or USB | — | Ribbon / USB |

---

## Power Supply Plan

```
┌─────────────────┐
│  Battery Pack    │
│  (7–12V LiPo    │
│   or 8×AA)      │
│                  │
│  + ──→ L298N 12V│──→ Motors
│  – ──→ L298N GND│
│                  │
│  + ──→ 5V BEC   │──→ Servos VCC
│  – ──→ BEC GND  │──→ Servos GND + Pi GND
│                  │
│  (optional)      │
│  L298N 5V out ──→│──→ Pi 5V (Pin 4) ← powers the Pi
└─────────────────┘

ESP32: separate USB power bank or tap from 5V BEC
PAM8403 amp: 5V from Pi Pin 4 or BEC
```

> 🔑 **Golden rule:** ALL GNDs must be connected together (battery GND = L298N GND = Pi GND = servo GND = amp GND).

---

## GPS UART Conflict Fix

GPIO 14 and 15 are used by both servos AND UART. Since servos are more important for the robot, **use a USB UART adapter for GPS**:

```bash
# Buy a CP2102 or CH340 USB-to-UART adapter (~₹60)
# Connect: GPS TX → adapter RX, GPS RX → adapter TX, GND → GND
# Plug adapter into Pi USB
# Change config.py:
GPS_PORT = "/dev/ttyUSB1"
```

---

*Print this out, follow it top to bottom, and your robot is ready. 🤖*
