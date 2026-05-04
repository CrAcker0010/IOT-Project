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
            rotated_frame = cv2.rotate(robot_instance.camera.frame, cv2.ROTATE_90_CLOCKWISE)
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
        
    # Set to manual if driving remotely
    if command in ['forward', 'backward', 'left', 'right', 'stop']:
        robot_instance.set_mode("idle")
    
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

@app.route('/api/pet/call', methods=['POST'])
def call_pet():
    if robot_instance:
        logger.info("Web interface called the pet!")
        robot_instance.set_mode("pet")
        if hasattr(robot_instance.pet_mode, 'called_by_owner'):
            robot_instance.pet_mode.called_by_owner()
        return jsonify({"status": "pet_called"})
    return jsonify({"status": "error"})

@app.route('/api/rescue', methods=['POST'])
def rescue():
    """Activate / deactivate rescue mode."""
    if not robot_instance:
        return jsonify({"status": "error", "message": "Robot not initialised"}), 500
    data   = request.json or {}
    action = data.get("action", "start")   # "start" or "stop"
    if action == "start":
        robot_instance.set_mode("rescue")
        logger.info("Rescue mode started via web API.")
        return jsonify({"status": "rescue_started"})
    else:
        robot_instance.set_mode("idle")
        logger.info("Rescue mode stopped via web API.")
        return jsonify({"status": "rescue_stopped"})

@app.route('/api/search', methods=['POST'])
def search():
    """Activate / deactivate search mode with an optional target description."""
    if not robot_instance:
        return jsonify({"status": "error", "message": "Robot not initialised"}), 500
    data   = request.json or {}
    action = data.get("action", "start")           # "start" or "stop"
    target = data.get("target", "any object or person of interest")
    if action == "start":
        robot_instance.set_mode("search", search_target=target)
        logger.info(f"Search mode started via web API. Target: '{target}'")
        return jsonify({"status": "search_started", "target": target})
    else:
        robot_instance.set_mode("idle")
        logger.info("Search mode stopped via web API.")
        return jsonify({"status": "search_stopped"})


@app.route('/api/chat', methods=['POST'])
def chat():
    """Send a text message to the AI chatbot / command parser."""
    if not robot_instance:
        return jsonify({"status": "error"}), 500
    data    = request.json or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"reply": "Please say something."})
    try:
        from audio.voice_brain import VoiceBrain
        if not hasattr(robot_instance, '_voice_brain'):
            robot_instance._voice_brain = VoiceBrain(robot=robot_instance)
        reply = robot_instance._voice_brain.chat_text(message)
        return jsonify({"reply": reply})
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"reply": "Sorry, the chatbot encountered an error."}), 500

@app.route('/api/vision_drive', methods=['POST'])
def vision_drive():
    """Start or stop camera-based autonomous driving mode."""
    if not robot_instance:
        return jsonify({"status": "error"}), 500
    data   = request.json or {}
    action = data.get("action", "start")
    if action == "start":
        robot_instance.set_mode("vision_drive")
        return jsonify({"status": "vision_drive_started"})
    else:
        robot_instance.set_mode("idle")
        return jsonify({"status": "vision_drive_stopped"})

@app.route('/api/vision/check', methods=['POST'])
def vision_check():
    """
    Run one or more vision functions on the current camera frame on demand.
    Body: { "checks": ["lane", "obstacle", "yolo"] }
    Returns the latest result dicts (debug frames excluded for JSON).
    """
    if not robot_instance or not hasattr(robot_instance, 'vision_drive_mode'):
        return jsonify({"status": "error"}), 500

    data   = request.json or {}
    checks = data.get("checks", ["lane", "obstacle", "yolo"])
    vdm    = robot_instance.vision_drive_mode
    frame  = robot_instance.camera.frame if robot_instance.camera else None
    out    = {}

    if "lane" in checks:
        r = vdm.run_lane_check(frame)
        out["lane"] = {k: v for k, v in r.items() if k != "debug_frame"}

    if "obstacle" in checks:
        r = vdm.run_obstacle_check(frame)
        out["obstacle"] = {k: v for k, v in r.items() if k != "debug_frame"}

    if "yolo" in checks:
        filter_cls = data.get("filter_classes", None)
        r = vdm.run_yolo_check(frame, filter_classes=filter_cls)
        out["yolo"] = {k: v for k, v in r.items() if k != "debug_frame"}

    return jsonify({"status": "ok", "results": out})


def run_server(host='0.0.0.0', port=5000):
    logger.info(f"Starting web interface on {host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)

def start_server_thread(host='0.0.0.0', port=5000):
    server_thread = threading.Thread(target=run_server, args=(host, port), daemon=True)
    server_thread.start()
    return server_thread
