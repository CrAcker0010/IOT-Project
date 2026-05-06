"""
lcd_display.py
==============
Driver for a 16x2 or 20x4 I2C LCD display with PCF8574 backpack.

Hardware:
    LCD Pin → Raspberry Pi
    VCC     → 5V  (pin 2 or 4)
    GND     → GND (pin 6)
    SDA     → GPIO 2 / SDA (pin 3)
    SCL     → GPIO 3 / SCL (pin 5)
    I2C address: 0x27  (default for most PCF8574 backpacks)

Library: RPLCD  →  pip install RPLCD smbus2

Usage:
    from utils.lcd_display import LCDDisplay

    lcd = LCDDisplay()              # 16x2 default
    lcd.show_startup()
    lcd.show_mode("autonomous")
    lcd.show_message("Hello!", "World")
    lcd.show_sensor_data(front=45.2, left=30.1, right=28.5)
    lcd.show_ip("192.168.1.101")
    lcd.scroll_text("This is a long scrolling message")
    lcd.clear()
    lcd.backlight(False)            # Turn backlight off
"""

import time
import threading
from utils.logger import get_logger

logger = get_logger("LCDDisplay")

# ── Display size ───────────────────────────────────────────────────
LCD_COLS = 16    # Change to 20 if using a 20x4 display
LCD_ROWS = 2     # Change to 4 if using a 20x4 display
I2C_ADDR = 0x27  # Default PCF8574 address (try 0x3F if 0x27 doesn't work)
I2C_PORT = 1     # Raspberry Pi I2C bus 1 (GPIO2/3)


class LCDDisplay:
    """
    I2C LCD display controller.

    All public methods are safe to call even if the display hardware
    is not connected — errors are logged and silently swallowed.
    """

    def __init__(self, cols: int = LCD_COLS, rows: int = LCD_ROWS,
                 address: int = I2C_ADDR, port: int = I2C_PORT):
        self.cols    = cols
        self.rows    = rows
        self.address = address
        self.lcd     = None
        self._lock   = threading.Lock()
        self._scroll_thread  = None
        self._scroll_running = False
        self._init_display(port)

    # ── Initialisation ────────────────────────────────────────────
    def _init_display(self, port: int):
        try:
            from RPLCD.i2c import CharLCD
            self.lcd = CharLCD(
                i2c_expander="PCF8574",
                address=self.address,
                port=port,
                cols=self.cols,
                rows=self.rows,
                dotsize=8,
                charmap="A02",
                auto_linebreaks=True,
                backlight_enabled=True,
            )
            self.lcd.clear()
            logger.info(f"LCD initialised at I2C 0x{self.address:02X} "
                        f"({self.cols}x{self.rows})")
        except ImportError:
            logger.error("RPLCD not installed. Run: pip install RPLCD smbus2")
        except Exception as e:
            logger.error(f"LCD init failed (check wiring/address): {e}")

    # ── Low-level write helpers ───────────────────────────────────
    def _pad(self, text: str) -> str:
        """Pad / truncate text to exactly self.cols characters."""
        return text[:self.cols].ljust(self.cols)

    def _write_lines(self, *lines):
        """Write up to self.rows lines to the display (thread-safe)."""
        if self.lcd is None:
            return
        with self._lock:
            try:
                self.lcd.clear()
                for i, line in enumerate(lines[:self.rows]):
                    self.lcd.cursor_pos = (i, 0)
                    self.lcd.write_string(self._pad(str(line)))
            except Exception as e:
                logger.error(f"LCD write error: {e}")

    # ── Public display methods ────────────────────────────────────

    def clear(self):
        """Clear all text from the display."""
        if self.lcd is None:
            return
        with self._lock:
            try:
                self.lcd.clear()
            except Exception as e:
                logger.error(f"LCD clear error: {e}")

    def backlight(self, state: bool):
        """Turn the LCD backlight on (True) or off (False)."""
        if self.lcd is None:
            return
        with self._lock:
            try:
                self.lcd.backlight_enabled = state
            except Exception as e:
                logger.error(f"LCD backlight error: {e}")

    def show_message(self, line1: str = "", line2: str = "",
                     line3: str = "", line4: str = ""):
        """
        Display a custom message.
        Pass up to 4 strings (unused lines on 16x2 are ignored).

        Example:
            lcd.show_message("Hello!", "Robot ready.")
        """
        self._stop_scroll()
        lines = [line1, line2, line3, line4]
        self._write_lines(*lines[:self.rows])

    def show_startup(self):
        """Splash screen shown when the robot boots."""
        self._stop_scroll()
        if self.rows >= 4:
            self._write_lines("  IOT ROBOT v1.0", "  Initialising..",
                              "  Powered by Pi4", "  + Gemini AI")
        else:
            self._write_lines("  IOT ROBOT v1.0", "  Initialising..")
        logger.info("LCD: startup screen shown.")

    # def show_mode(self, mode: str):
    #     """
    #     Show the current operating mode.

    #     Example:
    #         lcd.show_mode("autonomous")
    #     """
    #     self._stop_scroll()
    #     mode_labels = {
    #         "autonomous"  : "AUTO  (Ultrasonic)",
    #         "vision_drive": "VISION DRIVE",
    #         "pet"         : "PET MODE  (follow)",
    #         "surveillance": "SURVEILLANCE",
    #         "rescue"      : "RESCUE BOT",
    #         "search"      : "SEARCH BOT",
    #         "idle"        : "STANDBY  (idle)",
    #         "manual"      : "MANUAL  (remote)",
    #     }
    #     label = mode_labels.get(mode.lower(), mode.upper())
    #     self._write_lines(">> MODE:", label)
    #     logger.info(f"LCD: mode = {mode}")

    def show_sensor_data(self, front: float = -1,
                         left: float = -1, right: float = -1,
                         speed: int = 0):
        """
        Show ultrasonic sensor distances and motor speed.

        Example:
            lcd.show_sensor_data(front=45.2, left=30.1, right=28.5, speed=50)
        """
        self._stop_scroll()

        def fmt(v): return f"{v:.0f}cm" if v >= 0 else " --  "

        if self.rows >= 4:
            self._write_lines(
                "SENSORS",
                f"F:{fmt(front)} Spd:{speed}%",
                f"L:{fmt(left)}",
                f"R:{fmt(right)}"
            )
        else:
            # Compact 2-line format
            self._write_lines(
                f"F:{fmt(front)} Spd:{speed}%",
                f"L:{fmt(left)} R:{fmt(right)}"
            )

    def show_ip(self, ip: str):
        """
        Display the Pi's IP address (useful at boot so you know where to connect).

        Example:
            lcd.show_ip("192.168.1.101")
        """
        self._stop_scroll()
        self._write_lines("Web Dashboard:", ip)
        logger.info(f"LCD: IP = {ip}")

    def show_voice_command(self, command: str):
        """
        Show the last recognised voice command.

        Example:
            lcd.show_voice_command("rescue mode")
        """
        self._stop_scroll()
        self._write_lines("Voice CMD:", command[:self.cols])

    def show_yolo_detection(self, label: str, confidence: float):
        """
        Show a YOLO object detection result.

        Example:
            lcd.show_yolo_detection("person", 0.91)
        """
        self._stop_scroll()
        self._write_lines(
            f"Detected: {label[:self.cols - 10]}",
            f"Conf: {confidence * 100:.0f}%"
        )

    def show_rescue_status(self, survivors: int, searching: bool):
        """
        Show rescue mode status — number of survivors found.

        Example:
            lcd.show_rescue_status(survivors=2, searching=True)
        """
        self._stop_scroll()
        status = "Searching..." if searching else "Mission done"
        self._write_lines(
            f"RESCUE: {status}",
            f"Survivors: {survivors}"
        )

    def show_home_automation(self, light1: bool, light2: bool,
                             light3: bool, door: bool):
        """
        Show NodeMCU home automation state.

        Example:
            lcd.show_home_automation(True, False, True, False)
        """
        self._stop_scroll()
        l1 = "ON " if light1 else "OFF"
        l2 = "ON " if light2 else "OFF"
        l3 = "ON " if light3 else "OFF"
        dr = "OPEN" if door else "SHUT"
        if self.rows >= 4:
            self._write_lines("HOME AUTOMATION",
                              f"L1:{l1} L2:{l2} L3:{l3}",
                              f"Door: {dr}", "")
        else:
            self._write_lines(
                f"L1:{l1} L2:{l2} L3:{l3}",
                f"Door:{dr}"
            )

    def show_gps(self, lat: float, lon: float):
        """
        Show GPS coordinates.

        Example:
            lcd.show_gps(12.9716, 77.5946)
        """
        self._stop_scroll()
        self._write_lines(
            f"Lat:{lat:.4f}",
            f"Lon:{lon:.4f}"
        )

    def show_chatbot_reply(self, reply: str):
        """
        Scroll a long chatbot reply across the display.

        Example:
            lcd.show_chatbot_reply("I am ARIA, your robot assistant.")
        """
        self.scroll_text(reply, line=1, delay=0.35)

    # ── Scrolling text ────────────────────────────────────────────
    def scroll_text(self, text: str, line: int = 1,
                    delay: float = 0.3, repeat: int = 1):
        """
        Scroll a long text string across a single row.

        Args:
            text   : The string to scroll.
            line   : Row index (0-based) to scroll on.
            delay  : Seconds between each scroll step.
            repeat : How many times to repeat the scroll.

        Example:
            lcd.scroll_text("Autonomous driving active!", line=1)
        """
        self._stop_scroll()
        self._scroll_running = True
        self._scroll_thread = threading.Thread(
            target=self._scroll_worker,
            args=(text, line, delay, repeat),
            daemon=True
        )
        self._scroll_thread.start()

    def _scroll_worker(self, text: str, line: int,
                       delay: float, repeat: int):
        padded = " " * self.cols + text + " " * self.cols
        if self.lcd is None:
            return
        for _ in range(repeat):
            for i in range(len(padded) - self.cols + 1):
                if not self._scroll_running:
                    return
                chunk = padded[i: i + self.cols]
                with self._lock:
                    try:
                        self.lcd.cursor_pos = (line, 0)
                        self.lcd.write_string(chunk)
                    except Exception:
                        return
                time.sleep(delay)

    def _stop_scroll(self):
        """Stop any in-progress scrolling before writing new content."""
        self._scroll_running = False
        if self._scroll_thread and self._scroll_thread.is_alive():
            self._scroll_thread.join(timeout=1)

    # ── Cleanup ───────────────────────────────────────────────────
    def cleanup(self):
        """Clear display and turn off backlight on shutdown."""
        self._stop_scroll()
        self.clear()
        self.backlight(False)
        logger.info("LCD: cleaned up.")
