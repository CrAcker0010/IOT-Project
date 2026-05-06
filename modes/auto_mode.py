import time
import threading
from utils.logger import get_logger
from utils.config import SETTINGS

logger = get_logger("AutoMode")

class AutoMode:
    """
    Autonomous driving mode. 
    Uses the Ultrasonic sensors to avoid obstacles and prevent falling off edges.
    """
    def __init__(self, robot):
        self.robot = robot
        self.running = False
        self.thread = None
        
        # Pull thresholds from config
        self.obstacle_dist = SETTINGS.get("OBSTACLE_THRESHOLD_CM", 30)
        self.danger_dist = SETTINGS.get("DANGER_THRESHOLD_CM", 15)

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._auto_loop, daemon=True)
        self.lcd_thread = threading.Thread(target=self._lcd_update_loop, daemon=True)
        
        self.thread.start()
        self.lcd_thread.start()
        logger.info("Autonomous mode started.")

    def _lcd_update_loop(self):
        """Displays 'AUTO' for 5 seconds, then shows live sensor scores."""
        if not hasattr(self.robot, 'lcd') or not self.robot.lcd:
            return

        # Phase 1: Show AUTO MODE for 5 seconds
        self.robot.lcd.show_mode("AUTO")
        start_time = time.time()
        
        while self.running and (time.time() - start_time) < 5:
            time.sleep(0.5)

        # Phase 2: Show live sensor/score data
        dots = 0
        while self.running:
            dot_str = "." * (dots % 4)
            dist = self.robot.us_front.get_distance()
            # If distance is err, show '??'
            dist_str = f"{dist:.0f}cm" if dist >= 0 else "Err"
            
            # Show Front distance as the 'score' metric for Auto Mode
            self.robot.lcd.show_text(f"Auto Running{dot_str}", f"Front: {dist_str}")
            
            dots += 1
            time.sleep(1.0)

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if hasattr(self, 'lcd_thread') and self.lcd_thread:
            self.lcd_thread.join(timeout=1.0)
        self.robot.motors.stop()
        self.robot.servos.set_pan(90)
        self.robot.servos.set_tilt(90)
        logger.info("Autonomous mode stopped.")
        if hasattr(self.robot, 'lcd') and self.robot.lcd:
            self.robot.lcd.show_mode("MANUAL")

    def _turn_with_gyro(self, target_angle_deg):
        """Turns the robot using gyroscope Z-axis integration."""
        if not self.robot.gyroscope:
            # Fallback to timing
            if target_angle_deg > 0:
                self.robot.motors.left(60)
            else:
                self.robot.motors.right(60)
            time.sleep(abs(target_angle_deg) / 90.0 * 0.5)
            self.robot.motors.stop()
            return

        current_angle = 0.0
        last_time = time.time()
        
        if target_angle_deg > 0:
            self.robot.motors.left(50)
        else:
            self.robot.motors.right(50)
            
        while self.running and abs(current_angle) < abs(target_angle_deg):
            _, _, gz = self.robot.gyroscope.get_gyro_data()
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            current_angle += gz * dt
            time.sleep(0.01)
            
        self.robot.motors.stop()

    def _auto_loop(self):
        """Main autonomous driving logic running in a background thread."""
        try:
            self.robot.servos.set_pan(90)
            self.robot.servos.set_tilt(90)
            
            while self.running:
                # 1. Cliff detection
                down_dist = self.robot.us_down.get_distance()
                if 15 < down_dist < 200: # Genuine cliff/hole
                    logger.warning(f"CLIFF DETECTED ({down_dist}cm)! Reversing...")
                    self.robot.motors.backward(60)
                    time.sleep(0.8)
                    self._turn_with_gyro(90)
                    continue

                # 2. Obstacle detection
                front_dist = self.robot.us_front.get_distance()
                if 0 < front_dist < 20: # User requested 20cm threshold
                    logger.info(f"Obstacle at {front_dist:.1f}cm. Scanning...")
                    self.robot.motors.stop()
                    
                    # Scan Left
                    self.robot.servos.set_pan(160)
                    time.sleep(0.5)
                    left_dist = self.robot.us_front.get_distance()
                    
                    # Scan Right
                    self.robot.servos.set_pan(20)
                    time.sleep(0.5)
                    right_dist = self.robot.us_front.get_distance()
                    
                    self.robot.servos.set_pan(90)
                    time.sleep(0.3)
                    
                    # Turn toward max distance
                    if left_dist > right_dist and left_dist > 20:
                        self._turn_with_gyro(90)
                    elif right_dist > left_dist and right_dist > 20:
                        self._turn_with_gyro(-90)
                    else:
                        self.robot.motors.backward(50)
                        time.sleep(0.8)
                        self._turn_with_gyro(180)
                else:
                    self.robot.motors.forward(50)
                    
                time.sleep(0.05) 
                
        except Exception as e:
            logger.error(f"Error in Auto Mode loop: {e}")
            self.robot.motors.stop()
