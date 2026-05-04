# Common Ground (GND) with Buck Converter

When you power servos using an external buck converter (which is a GREAT idea), you **MUST** connect the buck converter's ground to the Raspberry Pi's ground. 

Here is why and how to do it.

## The "Why"

Electricity needs a complete circuit (a loop) to flow. 
- The buck converter provides the raw power (the 5V "muscle") to make the servo move.
- The Raspberry Pi provides the PWM control signal (the 3.3V "brain" signal) to tell the servo *where* to move.

If the Pi and the buck converter don't share a common ground, the Pi's 3.3V PWM signal has no reference point. The servo won't know what "0 volts" is, so it can't understand the "3.3 volts" signal. It will either jitter wildly or do nothing at all.

## How to Wire It

```text
[ Battery (e.g., 12V) ]
   |                |
   + (Red)          - (Black)
   |                |
   v                v
[ IN+   BUCK CONV  IN- ]
[ OUT+             OUT-]
   |                |
   v                v
  5V               GND  <------ IMPORTANT POINT
   |                |
   +-------+--------+-------------+
           |        |             |
           v        v             v
       [ Servo 1 ] [ Servo 2 ]  [ Raspberry Pi GND (Pin 6, 9, 14, etc.) ]
         (Red)     (Brown)
           |          |
           v          v
   [ Pi GPIO 14 ] [ Pi GPIO 15 ]
   (PWM Signal)   (PWM Signal)
```

### The Connections

1. **Power:** Battery (+) and (-) go to Buck Converter IN+ and IN-.
2. **Servo Power:** Buck Converter OUT+ (adjusted to exactly 5V) goes to the **Red** wire of BOTH servos.
3. **Servo Ground:** Buck Converter OUT- goes to the **Brown/Black** wire of BOTH servos.
4. **THE COMMON GROUND:** Run a wire from Buck Converter OUT- (or the servo's brown/black wire) to **ANY GND pin on the Raspberry Pi**.
5. **Signals:** Pi GPIO 14 and 15 go to the **Orange/White** signal wires of the servos.

This ensures the Pi's 3.3V signal has a solid 0V reference to push against!
