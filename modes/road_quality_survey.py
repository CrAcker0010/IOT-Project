import time
import threading
from utils.logger import get_logger

logger = get_logger("RoadQualitySurvey")

class RoadQualitySurvey:
    """
    Automatic Road Quality Detection Mode
    Moves in an area, reads MPU (gyroscope) and down ultrasonic sensor,
    evaluates road quality, and navigates obstacles.
    """
    def __init__(self, robot):
        self.robot = robot
        self.running = False
        self.thread = None
        self.lcd_thread = None
        
        # Scoring metrics
        self.bump_score = 0.0
        self.total_readings = 0

    def start(self):
        if self.running:
            return
        self.running = True
        self.bump_score = 0.0
        self.total_readings = 0
        
        self.thread = threading.Thread(target=self._survey_loop, daemon=True)
        self.lcd_thread = threading.Thread(target=self._lcd_animation_loop, daemon=True)
        
        self.thread.start()
        self.lcd_thread.start()
        logger.info("Road Quality Survey started.")

    def stop(self):
        if not self.running:
            return
        self.running = False
        
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.lcd_thread:
            self.lcd_thread.join(timeout=1.0)
        
        self.robot.motors.stop()
        self.robot.servos.set_pan(90)
        self.robot.servos.set_tilt(90)
        
        final_score = self._calculate_score()
        logger.info(f"Road Quality Survey stopped. Final Score: {final_score}/100")
        
        if hasattr(self.robot, 'lcd') and self.robot.lcd:
            self.robot.lcd.show_text(f"Quality: {final_score}/100", "Survey Done")

    def _calculate_score(self):
        """Calculates a 0-100 score based on Z-axis gravity deviations."""
        if self.total_readings == 0:
            return 100
            
        avg_bump = self.bump_score / self.total_readings
        
        # A perfectly smooth road has 0 variance (approx 1g constantly).
        # We heavily penalize high average variance.
        score = 100 - (avg_bump * 200) 
        return max(0, min(100, int(score)))

    def _lcd_animation_loop(self):
        """Displays 'Reading' with animating dots on the LCD."""
        dots = 0
        while self.running:
            if hasattr(self.robot, 'lcd') and self.robot.lcd:
                dot_str = "." * (dots % 4)
                display_str = f"Reading{dot_str}".ljust(16)
                current_score = self._calculate_score()
                self.robot.lcd.show_text(display_str, f"Score: {current_score}/100")
            dots += 1
            time.sleep(0.5)

    def _turn_with_gyro(self, target_angle_deg):
        """Turns the robot using gyroscope Z-axis integration."""
        if not self.robot.gyroscope:
            # Fallback to timing if no gyro is available
            if target_angle_deg > 0:
                self.robot.motors.left(60)
            else:
                self.robot.motors.right(60)
            time.sleep(abs(target_angle_deg) / 90.0 * 0.5)
            self.robot.motors.stop()
            return

        # Simple gyro integration to achieve desired rotation
        current_angle = 0.0
        last_time = time.time()
        
        if target_angle_deg > 0:
            self.robot.motors.left(50)  # Turn Left for positive angles
        else:
            self.robot.motors.right(50) # Turn Right for negative angles
            
        while self.running and abs(current_angle) < abs(target_angle_deg):
            # gz is degrees per second
            _, _, gz = self.robot.gyroscope.get_gyro_data()
            
            current_time = time.time()
            dt = current_time - last_time
            last_time = current_time
            
            current_angle += gz * dt
            time.sleep(0.01)
            
        self.robot.motors.stop()

    def _survey_loop(self):
        """Main robot movement and scanning loop."""
        try:
            # Ensure sensors are facing directly forward
            self.robot.servos.set_pan(90)
            self.robot.servos.set_tilt(90)
            
            start_time = time.time()
            
            # Run the survey for 60 seconds (roughly exploring the 1x1m cubicle)
            while self.running and (time.time() - start_time) < 60:
                
                # 1. Read Road Quality Data (Gyroscope Z-axis)
                if self.robot.gyroscope:
                    ax, ay, az = self.robot.gyroscope.get_accel_data()
                    # Calculate deviation from standard 1.0g gravity
                    z_deviation = abs(abs(az) - 1.0)
                    self.bump_score += z_deviation
                    self.total_readings += 1
                    
                # Read downward sensor (could be used to detect severe potholes)
                down_dist = self.robot.us_down.get_distance()
                if down_dist > 15: # Severe pothole / edge
                    self.bump_score += 2.0 # Huge penalty
                    self.total_readings += 1
                
                # 2. Forward Movement and Obstacle Detection
                front_dist = self.robot.us_front.get_distance()
                
                if 0 < front_dist < 20:
                    self.robot.motors.stop()
                    logger.info("Obstacle < 20cm. Scanning sides...")
                    
                    # Scan sides using Servo (Pan used for left/right)
                    self.robot.servos.set_pan(160) # Look Left
                    time.sleep(0.5)
                    dist_left = self.robot.us_front.get_distance()
                    
                    self.robot.servos.set_pan(20) # Look Right
                    time.sleep(0.5)
                    dist_right = self.robot.us_front.get_distance()
                    
                    self.robot.servos.set_pan(90) # Look Center
                    time.sleep(0.3)
                    
                    # Store max distance and move in that direction using gyro
                    if dist_left > dist_right and dist_left > 20:
                        logger.info(f"Max distance Left ({dist_left}cm). Turning Left.")
                        self._turn_with_gyro(90) # Turn 90 deg left
                    elif dist_right > dist_left and dist_right > 20:
                        logger.info(f"Max distance Right ({dist_right}cm). Turning Right.")
                        self._turn_with_gyro(-90) # Turn 90 deg right
                    else:
                        logger.info("Trapped. Turning around.")
                        self._turn_with_gyro(180) # Turn 180 deg
                        
                else:
                    self.robot.motors.forward(50)
                    
                time.sleep(0.05)
                
            # Auto-stop when time is up
            if self.running:
                self.stop()
                
        except Exception as e:
            logger.error(f"Error in Road Quality Survey loop: {e}")
            self.robot.motors.stop()
