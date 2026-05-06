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
        self.thread.start()
        logger.info("Autonomous mode started.")
        if hasattr(self.robot, 'lcd') and self.robot.lcd:
            self.robot.lcd.show_mode("AUTO")

    def stop(self):
        if not self.running:
            return
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        self.robot.motors.stop()
        self.robot.servos.set_pan(90)
        self.robot.servos.set_tilt(90)
        logger.info("Autonomous mode stopped.")
        if hasattr(self.robot, 'lcd') and self.robot.lcd:
            self.robot.lcd.show_mode("MANUAL")

    def _auto_loop(self):
        """Main autonomous driving logic running in a background thread."""
        try:
            # Ensure camera/sensors are facing directly forward
            self.robot.servos.set_pan(90)
            self.robot.servos.set_tilt(90)
            
            while self.running:
                # 1. Cliff detection (down sensor)
                # If distance > danger_dist, it means the ground dropped away (we are over an edge!)
                down_dist = self.robot.us_down.get_distance()
                if down_dist > self.danger_dist or down_dist < 0:
                    logger.warning("CLIFF DETECTED! Reversing...")
                    self.robot.motors.backward(60)
                    time.sleep(1)
                    self.robot.motors.left(60)
                    time.sleep(0.5)
                    self.robot.motors.stop()
                    continue

                # 2. Obstacle detection (front sensor)
                front_dist = self.robot.us_front.get_distance()
                if 0 < front_dist < self.obstacle_dist:
                    logger.info(f"Obstacle detected at {front_dist:.1f}cm. Evading...")
                    self.robot.motors.stop()
                    
                    # Look left
                    self.robot.servos.set_pan(160)
                    time.sleep(0.5)
                    left_dist = self.robot.us_front.get_distance()
                    
                    # Look right
                    self.robot.servos.set_pan(20)
                    time.sleep(0.5)
                    right_dist = self.robot.us_front.get_distance()
                    
                    # Look center again
                    self.robot.servos.set_pan(90)
                    time.sleep(0.3)
                    
                    # Decide where to go based on sensor sweeps
                    if left_dist > right_dist and left_dist > self.obstacle_dist:
                        logger.info("Path clear on Left. Turning Left.")
                        self.robot.motors.left(60)
                        time.sleep(0.5)
                    elif right_dist > left_dist and right_dist > self.obstacle_dist:
                        logger.info("Path clear on Right. Turning Right.")
                        self.robot.motors.right(60)
                        time.sleep(0.5)
                    else:
                        logger.info("Trapped! Reversing.")
                        self.robot.motors.backward(60)
                        time.sleep(1.0)
                        self.robot.motors.right(60)
                        time.sleep(0.8)
                        
                    self.robot.motors.stop()
                else:
                    # Clear path, move forward
                    self.robot.motors.forward(50)
                    
                # Small delay to prevent hogging the CPU
                time.sleep(0.05) 
                
        except Exception as e:
            logger.error(f"Error in Auto Mode loop: {e}")
            self.robot.motors.stop()
