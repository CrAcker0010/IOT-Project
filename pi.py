"""
rpi_camera_server.py — All-in-One IOT Robot Controller
=======================================================
Combines motor control, servo control, camera streaming,
and the full web dashboard into a single file.
Run on Raspberry Pi:  python3 rpi_camera_server.py
"""

import cv2
import time
import threading
from flask import Flask, Response, render_template_string, request, jsonify

# ═══════════════════════════════════════════════════════════════════
# GPIO SETUP (only on Raspberry Pi)
# ═══════════════════════════════════════════════════════════════════
try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    ON_PI = False
    print("[WARN] RPi.GPIO not found — running in SIMULATION mode.")

# ── Pin Configuration (BCM) ──────────────────────────────────────
PINS = {
    "MOTOR_ENA": 12, "MOTOR_ENB": 13,
    "MOTOR_IN1": 5,  "MOTOR_IN2": 6,
    "MOTOR_IN3": 26, "MOTOR_IN4": 19,
    "SERVO_PAN": 20, "SERVO_TILT": 21,
}

# ═══════════════════════════════════════════════════════════════════
# MOTOR CONTROLLER
# ═══════════════════════════════════════════════════════════════════
class MotorController:
    def __init__(self):
        if not ON_PI:
            return
        GPIO.setmode(GPIO.BCM)
        self._pins = [
            PINS["MOTOR_IN1"], PINS["MOTOR_IN2"],
            PINS["MOTOR_IN3"], PINS["MOTOR_IN4"],
            PINS["MOTOR_ENA"], PINS["MOTOR_ENB"],
        ]
        for p in self._pins:
            GPIO.setup(p, GPIO.OUT)
            GPIO.output(p, GPIO.LOW)
        self.pwm_a = GPIO.PWM(PINS["MOTOR_ENA"], 1000)
        self.pwm_b = GPIO.PWM(PINS["MOTOR_ENB"], 1000)
        self.pwm_a.start(0)
        self.pwm_b.start(0)

    def _speed(self, s):
        if not ON_PI: return
        s = max(0, min(100, s))
        self.pwm_a.ChangeDutyCycle(s)
        self.pwm_b.ChangeDutyCycle(s)

    def _set(self, a, b, c, d):
        if not ON_PI: return
        GPIO.output(PINS["MOTOR_IN1"], a)
        GPIO.output(PINS["MOTOR_IN2"], b)
        GPIO.output(PINS["MOTOR_IN3"], c)
        GPIO.output(PINS["MOTOR_IN4"], d)

    def forward(self, speed=50):
        self._speed(speed); self._set(1, 0, 1, 0)
    def backward(self, speed=50):
        self._speed(speed); self._set(0, 1, 0, 1)
    def left(self, speed=50):
        self._speed(speed); self._set(0, 1, 1, 0)
    def right(self, speed=50):
        self._speed(speed); self._set(1, 0, 0, 1)
    def stop(self):
        self._speed(0); self._set(0, 0, 0, 0)
    def cleanup(self):
        self.stop()
        if ON_PI:
            self.pwm_a.stop(); self.pwm_b.stop()

# ═══════════════════════════════════════════════════════════════════
# SERVO CONTROLLER (Pan-Tilt)
# ═══════════════════════════════════════════════════════════════════
class ServoController:
    def __init__(self):
        self.pan_angle = 90
        self.tilt_angle = 90
        if not ON_PI:
            return
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PINS["SERVO_PAN"], GPIO.OUT)
        GPIO.setup(PINS["SERVO_TILT"], GPIO.OUT)
        self.pan_pwm = GPIO.PWM(PINS["SERVO_PAN"], 50)
        self.tilt_pwm = GPIO.PWM(PINS["SERVO_TILT"], 50)
        self.pan_pwm.start(0)
        self.tilt_pwm.start(0)
        self.set_pan(90)
        self.set_tilt(90)

    @staticmethod
    def _duty(angle):
        return 2 + (angle / 18)

    def set_pan(self, angle):
        self.pan_angle = max(0, min(180, angle))
        if not ON_PI: return
        self.pan_pwm.ChangeDutyCycle(self._duty(self.pan_angle))
        time.sleep(0.25)
        self.pan_pwm.ChangeDutyCycle(0)

    def set_tilt(self, angle):
        self.tilt_angle = max(0, min(180, angle))
        if not ON_PI: return
        self.tilt_pwm.ChangeDutyCycle(self._duty(self.tilt_angle))
        time.sleep(0.25)
        self.tilt_pwm.ChangeDutyCycle(0)

    def cleanup(self):
        if ON_PI:
            self.pan_pwm.stop(); self.tilt_pwm.stop()

# ═══════════════════════════════════════════════════════════════════
# CAMERA STREAM (threaded capture)
# ═══════════════════════════════════════════════════════════════════
class CameraStream:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.frame = None
        self.running = False

    def start(self):
        if self.running: return
        self.running = True
        threading.Thread(target=self._update, daemon=True).start()

    def _update(self):
        while self.running:
            ret, f = self.cap.read()
            if ret:
                self.frame = f

    def stop(self):
        self.running = False
        self.cap.release()

# ═══════════════════════════════════════════════════════════════════
# INSTANTIATE HARDWARE
# ═══════════════════════════════════════════════════════════════════
motors = MotorController()
servos = ServoController()
camera = CameraStream()
current_mode = "idle"

# ═══════════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════════
app = Flask(__name__)

def gen_frames():
    while True:
        if camera.frame is not None:
            frame = cv2.rotate(camera.frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
            ret, buf = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buf.tobytes() + b'\r\n')
        else:
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# ── Motor API ─────────────────────────────────────────────────────
@app.route('/api/control', methods=['POST'])
def control():
    data = request.json or {}
    cmd = data.get('command', '')
    speed = data.get('speed', 50)
    actions = {
        'forward': lambda: motors.forward(speed),
        'backward': lambda: motors.backward(speed),
        'left': lambda: motors.left(speed),
        'right': lambda: motors.right(speed),
        'stop': motors.stop,
    }
    fn = actions.get(cmd)
    if fn:
        fn()
    print(f"[MOTOR] {cmd} speed={speed}")
    return jsonify({"status": "ok"})

# ── Camera Pan/Tilt API ──────────────────────────────────────────
@app.route('/api/camera', methods=['POST'])
def camera_control():
    data = request.json or {}
    cmd = data.get('command', '')
    step = 10
    if cmd == 'up':    servos.set_tilt(servos.tilt_angle - step)
    elif cmd == 'down':  servos.set_tilt(servos.tilt_angle + step)
    elif cmd == 'left':  servos.set_pan(servos.pan_angle + step)
    elif cmd == 'right': servos.set_pan(servos.pan_angle - step)
    elif cmd == 'reset': servos.set_pan(90); servos.set_tilt(90)
    print(f"[CAM] {cmd} → pan={servos.pan_angle} tilt={servos.tilt_angle}")
    return jsonify({"status": "ok"})

# ── Mode API ─────────────────────────────────────────────────────
@app.route('/api/mode', methods=['POST'])
def set_mode():
    global current_mode
    data = request.json or {}
    current_mode = data.get('mode', 'idle')
    if current_mode == 'idle':
        motors.stop()
    print(f"[MODE] → {current_mode}")
    return jsonify({"status": "ok", "mode": current_mode})

# ── Dashboard ─────────────────────────────────────────────────────
@app.route('/')
def index():
    return render_template_string(HTML_PAGE)

# ═══════════════════════════════════════════════════════════════════
# HTML TEMPLATE (from IOT-Project templates/index.html)
# ═══════════════════════════════════════════════════════════════════
HTML_PAGE = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>IOT Robot Dashboard</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<style>
:root{--bg:#080c14;--panel:#0f1623;--border:#1e2d45;--accent:#3b82f6;--green:#10b981;--red:#ef4444;--yellow:#f59e0b;--text:#e2e8f0;--muted:#64748b;--radius:14px}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Inter',sans-serif;min-height:100vh;display:flex;flex-direction:column}
.topbar{display:flex;align-items:center;justify-content:space-between;padding:.75rem 1.5rem;background:var(--panel);border-bottom:1px solid var(--border)}
.topbar-brand{font-weight:800;font-size:1.1rem;letter-spacing:1px;color:var(--accent)}
.topbar-status{display:flex;align-items:center;gap:.5rem;font-size:.8rem;color:var(--muted)}
.dot{width:8px;height:8px;border-radius:50%;background:var(--green);animation:blink 2s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}
#current-mode-badge{padding:.25rem .75rem;border-radius:99px;font-size:.75rem;font-weight:600;background:var(--accent);color:#fff}
.main{flex:1;display:grid;grid-template-columns:240px 1fr 280px;grid-template-rows:1fr auto;gap:1rem;padding:1rem}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:1rem}
.panel-title{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:2px;color:var(--muted);margin-bottom:.75rem}
.camera-wrap{grid-row:1;grid-column:2;display:flex;flex-direction:column;gap:.75rem}
#video-feed{width:100%;border-radius:var(--radius);background:#000;aspect-ratio:4/3;object-fit:cover;border:1px solid var(--border)}
.dpad{display:grid;grid-template-columns:repeat(3,56px);grid-template-rows:repeat(3,56px);gap:6px;margin:0 auto}
.dpad-btn{width:56px;height:56px;border-radius:50%;border:2px solid var(--border);background:linear-gradient(145deg,#1a2540,#0f1623);color:var(--text);font-size:1.3rem;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:all .1s;box-shadow:0 4px 0 #060a10;user-select:none;-webkit-user-select:none}
.dpad-btn:active,.dpad-btn.pressed{transform:translateY(4px);box-shadow:none;background:var(--accent)}
.dpad-stop{background:linear-gradient(145deg,#7f1d1d,#450a0a);border-color:var(--red)}
.dpad-stop:active{background:var(--red)}
.dn1{grid-column:2;grid-row:1}.dl2{grid-column:1;grid-row:2}.dc2{grid-column:2;grid-row:2}.dr2{grid-column:3;grid-row:2}.dn3{grid-column:2;grid-row:3}
.mode-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.mode-btn{padding:.6rem .4rem;border-radius:10px;border:1px solid var(--border);background:#111827;color:var(--text);font-size:.72rem;font-weight:600;cursor:pointer;text-align:center;transition:all .2s}
.mode-btn:hover{border-color:var(--accent);color:var(--accent)}
.mode-btn.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.mode-btn.mode-stop{border-color:var(--red);color:var(--red)}
.mode-btn.mode-stop:hover{background:var(--red);color:#fff}
.relay-grid{display:grid;grid-template-columns:1fr 1fr;gap:.5rem}
.relay-card{border-radius:10px;border:1px solid var(--border);background:#111827;padding:.6rem;text-align:center}
.relay-label{font-size:.7rem;color:var(--muted);margin-bottom:.4rem}
.relay-toggle{width:100%;padding:.35rem;border-radius:6px;border:none;font-size:.75rem;font-weight:700;cursor:pointer;transition:all .2s}
.relay-toggle.off{background:#1e293b;color:var(--muted)}.relay-toggle.on{background:var(--yellow);color:#000}
.chat-col{display:flex;flex-direction:column;gap:.75rem}
.chat-messages{flex:1;overflow-y:auto;max-height:280px;display:flex;flex-direction:column;gap:.5rem;padding:.25rem}
.chat-msg{padding:.5rem .75rem;border-radius:10px;font-size:.8rem;max-width:90%;line-height:1.4}
.chat-msg.user{background:var(--accent);color:#fff;align-self:flex-end}
.chat-msg.bot{background:#1e293b;color:var(--text);align-self:flex-start}
.chat-input-row{display:flex;gap:.5rem}
#chat-input{flex:1;padding:.5rem .75rem;border-radius:8px;border:1px solid var(--border);background:#111827;color:var(--text);font-size:.85rem;font-family:inherit}
#chat-input:focus{outline:none;border-color:var(--accent)}
.icon-btn{padding:.5rem .75rem;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:1rem;transition:background .2s}
.icon-btn:hover{background:#2563eb}
#search-target{width:100%;padding:.4rem .6rem;border-radius:8px;border:1px solid var(--border);background:#111827;color:var(--text);font-size:.8rem;margin-top:.25rem}
.bottom-bar{grid-column:1/-1;display:flex;align-items:center;gap:1rem;padding:.5rem 1rem;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);font-size:.75rem;color:var(--muted)}
.bottom-bar span{color:var(--text);font-family:'JetBrains Mono',monospace}
.portrait-warning{display:none;position:fixed;inset:0;z-index:9999;background:var(--bg);flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:2rem}
.portrait-warning h2{margin-top:1rem}
@media(max-width:896px) and (orientation:portrait){.portrait-warning{display:flex}body{overflow:hidden}}
@media(max-width:900px){.main{grid-template-columns:1fr}.camera-wrap{grid-column:1;grid-row:auto}}
</style>
</head>
<body>
<div class="portrait-warning"><h2>Rotate to Landscape</h2><p>Please rotate your device to use the dashboard.</p></div>
<div class="topbar">
  <div class="topbar-brand">🤖 IOT ROBOT</div>
  <div class="topbar-status"><div class="dot"></div> Live &nbsp;|&nbsp; Mode: <span id="current-mode-badge">idle</span></div>
</div>
<div class="main">
  <div style="display:flex;flex-direction:column;gap:.75rem;">
    <div class="panel">
      <div class="panel-title">🚗 Robot Modes</div>
      <div class="mode-grid">
        <button class="mode-btn" onclick="setMode('autonomous')">🧭 Autonomous</button>
        <button class="mode-btn" onclick="setMode('vision_drive')">📷 Vision Drive</button>
        <button class="mode-btn" onclick="setMode('pet')">🐕 Pet Mode</button>
        <button class="mode-btn" onclick="setMode('surveillance')">👁 Surveillance</button>
        <button class="mode-btn" onclick="setMode('rescue')">🆘 Rescue Bot</button>
        <button class="mode-btn" onclick="setMode('search')">🔍 Search Bot</button>
        <button class="mode-btn mode-stop" style="grid-column:1/-1" onclick="setMode('idle')">⏹ STOP ALL</button>
      </div>
      <input id="search-target" type="text" placeholder="Search target (e.g. red bag)...">
    </div>
    <div class="panel">
      <div class="panel-title">💡 Home Automation</div>
      <div class="relay-grid">
        <div class="relay-card"><div class="relay-label">Light 1</div><button class="relay-toggle off" id="light1-btn" onclick="toggleLight(1)">OFF</button></div>
        <div class="relay-card"><div class="relay-label">Light 2</div><button class="relay-toggle off" id="light2-btn" onclick="toggleLight(2)">OFF</button></div>
        <div class="relay-card"><div class="relay-label">Light 3</div><button class="relay-toggle off" id="light3-btn" onclick="toggleLight(3)">OFF</button></div>
        <div class="relay-card"><div class="relay-label">Door 4</div><button class="relay-toggle off" id="door4-btn" onclick="toggleDoor()">CLOSED</button></div>
      </div>
      <button class="mode-btn mode-stop" style="width:100%;margin-top:.5rem" onclick="allOff()">All OFF</button>
    </div>
  </div>
  <div class="camera-wrap">
    <img id="video-feed" src="/video_feed" alt="Live Camera">
    <div style="display:flex;gap:2rem;justify-content:center;align-items:center;flex-wrap:wrap;">
      <div>
        <div class="panel-title" style="text-align:center;margin-bottom:.5rem;">Movement</div>
        <div class="dpad">
          <button class="dpad-btn dn1" onmousedown="hold('forward')" onmouseup="release()" onmouseleave="release()" ontouchstart="hold('forward')" ontouchend="release()">↑</button>
          <button class="dpad-btn dl2" onmousedown="hold('left')" onmouseup="release()" onmouseleave="release()" ontouchstart="hold('left')" ontouchend="release()">←</button>
          <button class="dpad-btn dc2 dpad-stop" onclick="sendCmd('stop')">■</button>
          <button class="dpad-btn dr2" onmousedown="hold('right')" onmouseup="release()" onmouseleave="release()" ontouchstart="hold('right')" ontouchend="release()">→</button>
          <button class="dpad-btn dn3" onmousedown="hold('backward')" onmouseup="release()" onmouseleave="release()" ontouchstart="hold('backward')" ontouchend="release()">↓</button>
        </div>
      </div>
      <div>
        <div class="panel-title" style="text-align:center;margin-bottom:.5rem;">Camera Pan</div>
        <div class="dpad">
          <button class="dpad-btn dn1" onmousedown="camHold('up')" onmouseup="camRelease()" onmouseleave="camRelease()" ontouchstart="camHold('up')" ontouchend="camRelease()">↑</button>
          <button class="dpad-btn dl2" onmousedown="camHold('left')" onmouseup="camRelease()" onmouseleave="camRelease()" ontouchstart="camHold('left')" ontouchend="camRelease()">←</button>
          <button class="dpad-btn dc2 dpad-stop" onclick="camCmd('reset')">⊙</button>
          <button class="dpad-btn dr2" onmousedown="camHold('right')" onmouseup="camRelease()" onmouseleave="camRelease()" ontouchstart="camHold('right')" ontouchend="camRelease()">→</button>
          <button class="dpad-btn dn3" onmousedown="camHold('down')" onmouseup="camRelease()" onmouseleave="camRelease()" ontouchstart="camHold('down')" ontouchend="camRelease()">↓</button>
        </div>
      </div>
    </div>
  </div>
  <div class="panel chat-col">
    <div class="panel-title">🤖 ARIA — AI Chatbot</div>
    <div class="chat-messages" id="chat-messages">
      <div class="chat-msg bot">Hi! I'm ARIA. Type commands below or use D-pad controls.</div>
    </div>
    <div class="chat-input-row">
      <input id="chat-input" type="text" placeholder="Type a command..." onkeydown="if(event.key==='Enter') sendChat()">
      <button class="icon-btn" onclick="sendChat()">➤</button>
    </div>
  </div>
  <div class="bottom-bar">
    Mode: <span id="status-mode">idle</span>
    &nbsp;|&nbsp; Last cmd: <span id="status-cmd">—</span>
  </div>
</div>
<script>
const lightState={1:false,2:false,3:false};let doorOpen=false,holdInterval=null,camInterval=null;
function sendCmd(cmd,speed=55){fetch('/api/control',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:cmd,speed})}).catch(console.error);document.getElementById('status-cmd').textContent=cmd;}
function hold(d){sendCmd(d);holdInterval=setInterval(()=>sendCmd(d),150);}
function release(){clearInterval(holdInterval);holdInterval=null;sendCmd('stop');}
function camCmd(c){fetch('/api/camera',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command:c})}).catch(console.error);}
function camHold(d){camCmd(d);camInterval=setInterval(()=>camCmd(d),180);}
function camRelease(){clearInterval(camInterval);camInterval=null;}
function setMode(m){fetch('/api/mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode:m})}).catch(console.error);document.getElementById('current-mode-badge').textContent=m;document.getElementById('status-mode').textContent=m;if(m==='idle')sendCmd('stop');}
function toggleLight(n){lightState[n]=!lightState[n];const on=lightState[n],btn=document.getElementById('light'+n+'-btn');btn.textContent=on?'ON':'OFF';btn.className='relay-toggle '+(on?'on':'off');addBotMsg('Light '+n+' '+(on?'ON':'OFF'));}
function toggleDoor(){doorOpen=!doorOpen;const btn=document.getElementById('door4-btn');btn.textContent=doorOpen?'OPEN':'CLOSED';btn.className='relay-toggle '+(doorOpen?'on':'off');addBotMsg('Door '+(doorOpen?'opened':'closed'));}
function allOff(){[1,2,3].forEach(n=>{lightState[n]=false;const b=document.getElementById('light'+n+'-btn');b.textContent='OFF';b.className='relay-toggle off';});doorOpen=false;const d=document.getElementById('door4-btn');d.textContent='CLOSED';d.className='relay-toggle off';addBotMsg('All devices OFF');}
function addBotMsg(t){const e=document.createElement('div');e.className='chat-msg bot';e.textContent=t;const b=document.getElementById('chat-messages');b.appendChild(e);b.scrollTop=b.scrollHeight;}
function sendChat(){const inp=document.getElementById('chat-input'),t=inp.value.trim();if(!t)return;inp.value='';const e=document.createElement('div');e.className='chat-msg user';e.textContent=t;const b=document.getElementById('chat-messages');b.appendChild(e);b.scrollTop=b.scrollHeight;addBotMsg('Command received: '+t);}
document.addEventListener('keydown',e=>{if(document.activeElement.tagName==='INPUT')return;const m={ArrowUp:'forward',ArrowDown:'backward',ArrowLeft:'left',ArrowRight:'right',' ':'stop'};if(m[e.key]){e.preventDefault();sendCmd(m[e.key]);}});
document.addEventListener('keyup',e=>{if(['ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(e.key))sendCmd('stop');});
</script>
</body>
</html>'''

# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    camera.start()
    print("=" * 50)
    print("  IOT Robot Server — http://0.0.0.0:5000")
    print("=" * 50)
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except KeyboardInterrupt:
        pass
    finally:
        camera.stop()
        motors.cleanup()
        servos.cleanup()
        if ON_PI:
            GPIO.cleanup()
        print("Shutdown complete.")
