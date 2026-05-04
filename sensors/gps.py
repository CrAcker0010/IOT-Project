import serial
import pynmea2
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("GPS")

class GPSModule:
    def __init__(self):
        try:
            self.ser = serial.Serial(SETTINGS["GPS_PORT"], baudrate=SETTINGS["GPS_BAUD"], timeout=1)
            logger.info("GPS module initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize GPS: {e}")
            self.ser = None

    def get_location(self):
        if not self.ser:
            return None
            
        try:
            line = self.ser.readline().decode('ascii', errors='replace')
            if line.startswith('$GPGGA'):
                msg = pynmea2.parse(line)
                return {
                    "latitude": msg.latitude,
                    "longitude": msg.longitude,
                    "altitude": msg.altitude,
                    "num_sats": msg.num_sats
                }
        except serial.SerialException as e:
            logger.error(f"Device error: {e}")
        except pynmea2.ParseError as e:
            # Ignore parsing errors from incomplete sentences
            pass
        return None
