"""
web_server.py — Manual Control Web Dashboard
==============================================
Flask server providing:
  - Live camera feed
  - Motor control (forward/backward/left/right/stop)
  - Camera pan/tilt control
  - Speed adjustment
  - Home automation relay control
  - Sensor data API
"""

from flask import Flask, render_template, Response, request, jsonify
import cv2
import threading
from utils.logger import get_logger

logger = get_logger("WebServer")

app = Flask(__name__, template_folder='../templates', static_folder='../static')
robot_instance = None

def init_web_server(robot):
    global robot_instance
    robot_instance = robot

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    while True:
        if robot_instance and robot_instance.camera and robot_instance.camera.frame is not None:
            rotated_frame = cv2.rotate(robot_instance.camera.frame, cv2.ROTATE_180)
            ret, buffer = cv2.imencode('.jpg', rotated_frame)
            if ret:
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            # Yield empty/placeholder or just sleep
            import time
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/control', methods=['POST'])
def control():
    data = request.json
    command = data.get('command')
    speed = data.get('speed', 50)
    
    if not robot_instance:
        return jsonify({"status": "error"}), 500
    
    if command == 'forward':
        robot_instance.motors.forward(speed)
    elif command == 'backward':
        robot_instance.motors.backward(speed)
    elif command == 'left':
        robot_instance.motors.left(speed)
    elif command == 'right':
        robot_instance.motors.right(speed)
    elif command == 'stop':
        robot_instance.motors.stop()
        
    return jsonify({"status": "success"})

@app.route('/api/camera', methods=['POST'])
def camera_control():
    data = request.json
    command = data.get('command')
    
    if not robot_instance or not hasattr(robot_instance, 'servos'):
        return jsonify({"status": "error"}), 500
        
    step = 10
    if command == 'up':
        robot_instance.servos.set_tilt(robot_instance.servos.tilt_angle - step)
    elif command == 'down':
        robot_instance.servos.set_tilt(robot_instance.servos.tilt_angle + step)
    elif command == 'left':
        robot_instance.servos.set_pan(robot_instance.servos.pan_angle + step)
    elif command == 'right':
        robot_instance.servos.set_pan(robot_instance.servos.pan_angle - step)
    elif command == 'reset':
        robot_instance.servos.set_pan(90)
        robot_instance.servos.set_tilt(90)
        
    return jsonify({"status": "success"})

@app.route('/api/auto', methods=['POST'])
def auto_mode():
    data = request.json or {}
    action = data.get('action')
    
    if not robot_instance or not hasattr(robot_instance, 'auto_mode'):
        return jsonify({"status": "error", "message": "AutoMode not initialized"}), 500
        
    if action == 'start':
        robot_instance.auto_mode.start()
    elif action == 'stop':
        robot_instance.auto_mode.stop()
        
    return jsonify({"status": "success"})

@app.route('/api/sensors', methods=['GET'])
def sensors():
    """Return current sensor readings."""
    if not robot_instance:
        return jsonify({"status": "error"}), 500

    data = {
        "front": robot_instance.us_front.get_distance(),
        "back":  robot_instance.us_back.get_distance(),
        "down":  robot_instance.us_down.get_distance(),
    }

    if robot_instance.gyroscope:
        try:
            ax, ay, az = robot_instance.gyroscope.get_accel_data()
            data["accel"] = {"x": round(ax, 2), "y": round(ay, 2), "z": round(az, 2)}
        except Exception:
            pass

    return jsonify({"status": "ok", "sensors": data})

@app.route('/api/home', methods=['POST'])
def home_automation():
    """Forward a command to the NodeMCU home automation controller."""
    data = request.json or {}
    endpoint = data.get("endpoint", "")
    if not endpoint:
        return jsonify({"status": "error", "message": "No endpoint provided"}), 400

    from communication.home_automation import send_command
    result = send_command(endpoint)
    return jsonify({"status": "ok", "result": result})


def run_server(host='0.0.0.0', port=5000):
    logger.info(f"Starting web interface on {host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)

def start_server_thread(host='0.0.0.0', port=5000):
    server_thread = threading.Thread(target=run_server, args=(host, port), daemon=True)
    server_thread.start()
    return server_thread
