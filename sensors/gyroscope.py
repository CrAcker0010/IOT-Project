try:
    import smbus2 as smbus
except ImportError:
    import smbus
import math
import time
from utils.logger import get_logger

logger = get_logger("Gyroscope")

class MPU6050:
    def __init__(self, address=0x68):
        self.bus = smbus.SMBus(1)
        self.address = address
        try:
            # Wake up the MPU-6050 (write 0 to power management register)
            self.bus.write_byte_data(self.address, 0x6B, 0)
            logger.info("MPU6050 initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize MPU6050: {e}")
            
    def read_word_2c(self, reg):
        try:
            h = self.bus.read_byte_data(self.address, reg)
            l = self.bus.read_byte_data(self.address, reg+1)
            value = (h << 8) + l
            if value >= 0x8000:
                return -((65535 - value) + 1)
            else:
                return value
        except Exception as e:
            logger.error(f"Error reading register {reg}: {e}")
            return 0
            
    def get_accel_data(self):
        ax = self.read_word_2c(0x3B) / 16384.0
        ay = self.read_word_2c(0x3D) / 16384.0
        az = self.read_word_2c(0x3F) / 16384.0
        return ax, ay, az
        
    def get_gyro_data(self):
        gx = self.read_word_2c(0x43) / 131.0
        gy = self.read_word_2c(0x45) / 131.0
        gz = self.read_word_2c(0x47) / 131.0
        return gx, gy, gz

    def detect_rough_road(self, threshold=1.5):
        """Simple heuristic to detect rough road based on Z-axis acceleration variance"""
        ax, ay, az = self.get_accel_data()
        # Gravity is approx 1g on Z axis. Variations mean bumps.
        if abs(abs(az) - 1.0) > threshold:
            return True
        return False
