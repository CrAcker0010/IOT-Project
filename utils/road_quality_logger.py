import time
import csv
import threading
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("RoadQuality")

class RoadQualityLogger:
    """
    Background logger that monitors the MPU6050 gyroscope to detect bumps
    and generates a CSV road quality report.
    """
    def __init__(self, gyroscope, interval=0.1, threshold=0.4):
        self.gyroscope = gyroscope
        # self.ultrasonic_down = ultrasonic.UltrasonicSensor("down")
        self.interval = interval
        self.threshold = threshold
        self.running = False
        self.thread = None
        self.report_data = []
        self.filename = None

    def start(self):
        if not self.gyroscope:
            logger.error("Cannot start Road Quality Logger: No gyroscope available.")
            return
        if self.running:
            return
            
        self.running = True
        self.report_data = []
        self.filename = f"road_quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        self.thread = threading.Thread(target=self._log_loop, daemon=True)
        self.thread.start()
        logger.info(f"Started road quality logging. Report will be saved to {self.filename}")

    def _log_loop(self):
        while self.running:
            try:
                ax, ay, az = self.gyroscope.get_accel_data()
                
                # Gravity is roughly 1.0g on the Z-axis when flat.
                # A deviation from 1.0g indicates vertical acceleration (a bump or pothole).
                z_deviation = abs(abs(az) - 1.0)
                
                # Check if it's considered a significant bump
                is_bump = z_deviation > self.threshold
                status = "BUMP / POTHOLE" if is_bump else "Normal"
                
                # We log if it's a bump, OR just for a baseline
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                self.report_data.append([
                    timestamp, 
                    round(ax, 3), 
                    round(ay, 3), 
                    round(az, 3), 
                    round(z_deviation, 3), 
                    status
                ])
                
            except Exception as e:
                logger.error(f"Error reading gyroscope for road quality: {e}")
            
            time.sleep(self.interval)

    def stop(self):
        if not self.running:
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
        
        self.save_report()

    def save_report(self):
        if not self.report_data:
            logger.warning("No road quality data to save.")
            return

        try:
            with open(self.filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                # Write header
                writer.writerow(["Timestamp", "Accel_X (g)", "Accel_Y (g)", "Accel_Z (g)", "Z_Deviation (g)", "Road Quality"])
                # Write data
                writer.writerows(self.report_data)
                
            logger.info(f"Road quality report successfully generated: {self.filename}")
            print(f"\n[+] Road Quality Report saved to: {self.filename}")
            
        except Exception as e:
            logger.error(f"Failed to save road quality report: {e}")

# If run as a standalone script for testing
if __name__ == "__main__":
    from sensors.gyroscope import MPU6050
    print("Testing Road Quality Logger standalone...")
    try:
        gyro = MPU6050()
        logger = RoadQualityLogger(gyro)
        logger.start()
        print("Logging... Shake the sensor to simulate bumps. Press Ctrl+C to stop and generate report.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.stop()
        print("Done.")
    except Exception as e:
        print(f"Failed to test: {e}")
