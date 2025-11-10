# -*- coding: utf-8 -*-
"""
VTSurgical SmartCapture v2.2
Sistema de Transmissão Cirúrgica Inteligente (Linux)
"""

import os, cv2, glob, time, json, psutil, socket, threading
import numpy as np
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, session
from datetime import timedelta
import tensorflow as tf
from tensorflow import keras
import subprocess

CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "NOME_EQUIPAMENTO": "VTSurgical - Transmissão Cirúrgica",
    "CAMERA_INDEX": 0,
    "CAMERA_WIDTH": 1280,
    "CAMERA_HEIGHT": 720,
    "CAMERA_FPS": 30,
    "IP_BIND": "0.0.0.0",
    "IA_ENABLED": True,
    "CPU_USAGE": 0,
    "TEMP": 0,
    "USUARIOS": {"hupe": {"password": "hupe@2.0", "role": "admin"}}
}

cap = None
current_frame = None
frame_lock = threading.Lock()
restart_flag = False
segmentation_model = None
IA_ENABLED = True

# =============================================================
# 🧩 Funções de configuração
# =============================================================

def load_config():
    global CONFIG
    CONFIG = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_conf = json.load(f)
                CONFIG.update(user_conf)
        except Exception:
            pass
    save_config(CONFIG)
    return CONFIG

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4)

# =============================================================
# 🎥 Listagem de câmeras
# =============================================================

def listar_cameras():
    """
    Detecta dispositivos de vídeo e lê o nome real do driver via v4l2-ctl.
    """
    cameras = []
    for dev in sorted(glob.glob("/dev/video*")):
        try:
            cap = cv2.VideoCapture(dev)
            if cap.isOpened():
                # obtém nome do dispositivo
                try:
                    name = subprocess.check_output(["v4l2-ctl", "-d", dev, "--info"], text=True)
                    for line in name.splitlines():
                        if "Card type" in line:
                            name = line.split(":")[-1].strip()
                            break
                except Exception:
                    name = dev
                cameras.append(f"{dev} - {name}")
            cap.release()
        except Exception:
            continue
    if not cameras:
        cameras.append("Nenhuma câmera detectada")
    return cameras

# =============================================================
# 🧠 Carregar IA
# =============================================================

def load_segmentation_model():
    global segmentation_model
    try:
        tf.config.set_visible_devices([], "GPU")
        model_path = "seu_modelo_segmentacao.h5"
        if os.path.exists(model_path):
            segmentation_model = keras.models.load_model(model_path, compile=False)
            print("✅ IA carregada com sucesso.")
        else:
            print("⚠️ Modelo de IA ausente (.h5 não encontrado).")
            segmentation_model = None
    except Exception as e:
        print(f"⚠️ Erro IA: {e}")
        segmentation_model = None

def apply_ai(frame):
    """Aplica máscara IA se ativo."""
    if not IA_ENABLED or segmentation_model is None:
        return frame
    try:
        resized = cv2.resize(frame, (256, 256)) / 255.0
        pred = segmentation_model.predict(np.expand_dims(resized, axis=0), verbose=0)[0]
        mask = (pred[:, :, 0] > 0.5).astype(np.uint8) * 255
        mask = cv2.resize(mask, (frame.shape[1], frame.shape[0]))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(frame, contours, -1, (0, 255, 0), 2)
    except Exception:
        pass
    return frame

# =============================================================
# ⚙️ Iniciar câmera
# =============================================================

def start_camera(index):
    global cap
    if cap and cap.isOpened():
        cap.release()

    dev = f"/dev/video{index}" if str(index).isdigit() else str(index)
    cap = cv2.VideoCapture(dev)

    # tenta MJPG → YUYV → H264
    for codec in ["MJPG", "YUYV", "H264"]:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*codec))
        time.sleep(0.2)
        if cap.isOpened():
            print(f"🎥 Codec ativo: {codec} em {dev}")
            break

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CONFIG["CAMERA_WIDTH"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CONFIG["CAMERA_HEIGHT"])
    cap.set(cv2.CAP_PROP_FPS, CONFIG["CAMERA_FPS"])

    # tenta ajustar brilho/exposição automáticos
    try:
        subprocess.run(["v4l2-ctl", "-d", dev, "--set-ctrl=exposure_auto=3"], stdout=subprocess.DEVNULL)
        subprocess.run(["v4l2-ctl", "-d", dev, "--set-ctrl=gain_automatic=1"], stdout=subprocess.DEVNULL)
        subprocess.run(["v4l2-ctl", "-d", dev, "--set-ctrl=brightness=150"], stdout=subprocess.DEVNULL)
    except Exception:
        pass

    if cap.isOpened():
        print(f"✅ Câmera iniciada: {dev}")
        return True
    else:
        print(f"🚫 Falha ao abrir {dev}")
        return False

# =============================================================
# 🔁 Loop de captura
# =============================================================

def capture_frames():
    global cap, current_frame, restart_flag
    if not start_camera(CONFIG["CAMERA_INDEX"]):
        print("❌ Nenhuma câmera disponível.")
        return
    while not restart_flag:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.05)
            continue
        frame = apply_ai(frame)
        with frame_lock:
            current_frame = frame.copy()
    if cap and cap.isOpened():
        cap.release()

def generate_stream():
    global current_frame
    while True:
        with frame_lock:
            frame = current_frame.copy() if current_frame is not None else np.zeros((480, 640, 3), np.uint8)
        _, buf = cv2.imencode(".jpg", frame)
        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n"
        time.sleep(1 / CONFIG["CAMERA_FPS"])

# =============================================================
# 🩺 Telemetria
# =============================================================

def update_system_status():
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)
            temp_path = "/sys/class/thermal/thermal_zone0/temp"
            temp = 0
            if os.path.exists(temp_path):
                with open(temp_path) as f:
                    temp = int(f.read()) / 1000
            CONFIG["CPU_USAGE"] = cpu
            CONFIG["TEMP"] = temp
        except Exception:
            pass
        time.sleep(2)

# =============================================================
# 🌐 Flask
# =============================================================

app = Flask(__name__)
app.secret_key = "vtsurgical_key"
app.permanent_session_lifetime = timedelta(hours=2)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def wrapper(*a, **kw):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u, p = request.form["username"], request.form["password"]
        if u in CONFIG["USUARIOS"] and CONFIG["USUARIOS"][u]["password"] == p:
            session["username"] = u
            return redirect(url_for("index"))
        return render_template("login.html", error="Credenciais inválidas.")
    return render_template("login.html")

@app.route("/")
@login_required
def index():
    return render_template("index.html", config=CONFIG, ia_enabled=IA_ENABLED, session=session)

@app.route("/video_feed")
@login_required
def video_feed():
    return Response(generate_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

@app.route("/toggle_ia", methods=["POST"])
@login_required
def toggle_ia():
    global IA_ENABLED
    IA_ENABLED = not IA_ENABLED
    status = "ativada" if IA_ENABLED else "desativada"
    return jsonify({"status": "success", "message": f"IA {status} com sucesso."})

@app.route("/config", methods=["GET", "POST"])
@login_required
def config():
    if request.method == "POST":
        act = request.form.get("action")
        if act == "save_all":
            CONFIG["NOME_EQUIPAMENTO"] = request.form.get("nome_equipamento")
            CONFIG["CAMERA_INDEX"] = int(request.form.get("camera_index", 0))
            res = request.form.get("camera_resolution", "1280x720").split("x")
            CONFIG["CAMERA_WIDTH"], CONFIG["CAMERA_HEIGHT"] = int(res[0]), int(res[1])
            CONFIG["CAMERA_FPS"] = int(request.form.get("camera_fps", 30))
            save_config(CONFIG)
            return jsonify({"status": "restarting", "message": "Configurações salvas e aplicadas."})
    devices = listar_cameras()
    return render_template("config.html", config=CONFIG, devices=devices, session=session)

# =============================================================
# 🚀 Inicialização
# =============================================================

if __name__ == "__main__":
    load_config()
    load_segmentation_model()
    port = 5000
    threading.Thread(target=capture_frames, daemon=True).start()
    threading.Thread(target=update_system_status, daemon=True).start()
    print(f"🌐 Servidor rodando em http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, threaded=True)
