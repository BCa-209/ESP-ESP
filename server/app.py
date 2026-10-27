"""
Servidor Puente y Panel Web para el sistema de dos ESP32 vía MQTT.
No utiliza base de datos: todos los estados e historial reciente residen exclusivamente en memoria RAM.
"""

import json
import logging
import queue
import threading
import time
from collections import deque
from datetime import datetime
from flask import Flask, Response, jsonify, render_template, request

import config

# Configuración de registro en consola
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("BridgeServer")

app = Flask(__name__)

# ==============================================================================
# ALMACENAMIENTO DE ESTADO EN MEMORIA RAM (SIN BASE DE DATOS)
# ==============================================================================
state_lock = threading.Lock()

devices_state = {
    "A": {
        "id": "A",
        "name": "ESP32 A (30 pines)",
        "status": "offline",      # "online", "offline", "unknown"
        "local_ch1": False,
        "local_ch2": False,
        "remote_ch1": False,
        "remote_ch2": False,
        "last_seen": None
    },
    "B": {
        "id": "B",
        "name": "ESP32 B (38 pines)",
        "status": "offline",
        "local_ch1": False,
        "local_ch2": False,
        "remote_ch1": False,
        "remote_ch2": False,
        "last_seen": None
    }
}

system_info = {
    "broker_connected": False,
    "broker_host": config.MQTT_BROKER,
    "broker_port": config.MQTT_PORT,
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

# Historial reciente en memoria (anillo circular FIFO)
recent_events = deque(maxlen=config.MAX_IN_MEMORY_EVENTS)

# Lista de suscriptores para Server-Sent Events (SSE)
sse_clients = []
sse_lock = threading.Lock()


def add_event(device_id, event_type, description, details=None):
    """Registra un evento temporal en el buffer circular de RAM."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    event_entry = {
        "time": timestamp,
        "device": device_id,
        "type": event_type,
        "desc": description,
        "details": details or {}
    }
    recent_events.appendleft(event_entry)
    broadcast_update({"type": "event", "data": event_entry})


def broadcast_update(message_dict):
    """Envía actualizaciones en tiempo real a todos los navegadores conectados por SSE."""
    payload = f"data: {json.dumps(message_dict)}\n\n"
    with sse_lock:
        stale_clients = []
        for q in sse_clients:
            try:
                q.put_nowait(payload)
            except queue.Full:
                stale_clients.append(q)
        for q in stale_clients:
            if q in sse_clients:
                sse_clients.remove(q)


# ==============================================================================
# INTEGRACION CON CLIENTE MQTT (PAHO-MQTT)
# ==============================================================================
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc, properties=None):
    """Callback de conexión al broker MQTT."""
    if rc == 0:
        system_info["broker_connected"] = True
        logger.info(f"Conectado exitosamente al broker MQTT en {config.MQTT_BROKER}:{config.MQTT_PORT}")
        
        # Suscribirse a tópicos de estado y disponibilidad
        client.subscribe(config.TOPIC_STATE_WILDCARD)
        client.subscribe(config.TOPIC_STATUS_WILDCARD)
        logger.info(f"Suscrito a: {config.TOPIC_STATE_WILDCARD} y {config.TOPIC_STATUS_WILDCARD}")
        
        add_event("SYSTEM", "info", f"Conectado al broker MQTT ({config.MQTT_BROKER}:{config.MQTT_PORT})")
        broadcast_update({"type": "broker_status", "connected": True})
    else:
        system_info["broker_connected"] = False
        logger.error(f"Error al conectar con broker MQTT. Código de retorno: {rc}")
        add_event("SYSTEM", "error", f"Fallo de conexión con broker MQTT (rc={rc})")
        broadcast_update({"type": "broker_status", "connected": False})


def on_disconnect(client, userdata, rc, properties=None):
    """Callback de desconexión del broker MQTT."""
    system_info["broker_connected"] = False
    logger.warning(f"Desconectado del broker MQTT (rc={rc})")
    add_event("SYSTEM", "warning", "Desconectado del broker MQTT")
    broadcast_update({"type": "broker_status", "connected": False})


def on_message(client, userdata, msg):
    """Procesa los mensajes MQTT entrantes."""
    topic = msg.topic
    payload_str = msg.payload.decode("utf-8", errors="ignore").strip()
    logger.debug(f"Mensaje MQTT recibido [{topic}]: {payload_str}")

    parts = topic.split("/")
    if len(parts) != 4 or parts[0] != "lab" or parts[1] != "esp32":
        return

    device_id = parts[2]
    topic_type = parts[3]

    if device_id not in ("A", "B"):
        return

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with state_lock:
        if topic_type == "status":
            status_val = payload_str.lower()
            devices_state[device_id]["status"] = status_val
            devices_state[device_id]["last_seen"] = now_str
            
            status_label = "En línea" if status_val == "online" else "Desconectado"
            add_event(
                device_id,
                "status",
                f"ESP32 {device_id} cambió su estado a: {status_label}",
                {"status": status_val}
            )

        elif topic_type == "state":
            try:
                data = json.loads(payload_str)
            except json.JSONDecodeError:
                logger.warning(f"Payload no válido como JSON en {topic}: {payload_str}")
                return

            ch1 = bool(data.get("channel1", False))
            ch2 = bool(data.get("channel2", False))

            # Actualizar estados locales del dispositivo emisor
            devices_state[device_id]["local_ch1"] = ch1
            devices_state[device_id]["local_ch2"] = ch2
            devices_state[device_id]["status"] = "online"
            devices_state[device_id]["last_seen"] = now_str

            # Actualizar los LEDs receptores en la placa par:
            # Lo que emite A como local_ch1/2 es lo que B recibe en remote_ch1/2
            peer_id = "B" if device_id == "A" else "A"
            devices_state[peer_id]["remote_ch1"] = ch1
            devices_state[peer_id]["remote_ch2"] = ch2

            add_event(
                device_id,
                "channel_toggle",
                f"ESP32 {device_id} actualizó canales -> Ch1: {'ON' if ch1 else 'OFF'} | Ch2: {'ON' if ch2 else 'OFF'}",
                {"channel1": ch1, "channel2": ch2}
            )

    # Notificar a los clientes web con el estado consolidado completo
    broadcast_update({
        "type": "state_snapshot",
        "devices": devices_state,
        "broker_connected": system_info["broker_connected"]
    })


def start_mqtt_client():
    """Inicializa el cliente MQTT compatible con paho-mqtt v1 y v2."""
    client_id = f"esp32_bridge_web_{int(time.time())}"
    
    # Compatibilidad con API v2 y v1 de paho-mqtt
    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
    except AttributeError:
        mqtt_client = mqtt.Client(client_id=client_id)

    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_message = on_message

    if config.MQTT_USER and config.MQTT_PASSWORD:
        mqtt_client.username_pw_set(config.MQTT_USER, config.MQTT_PASSWORD)

    def _mqtt_thread():
        while True:
            try:
                logger.info(f"Conectando a broker MQTT en {config.MQTT_BROKER}:{config.MQTT_PORT}...")
                mqtt_client.connect(config.MQTT_BROKER, config.MQTT_PORT, keepalive=config.MQTT_KEEPALIVE)
                mqtt_client.loop_forever()
            except Exception as e:
                system_info["broker_connected"] = False
                logger.error(f"Excepción en bucle MQTT: {e}. Reintentando en 5 segundos...")
                time.sleep(5)

    th = threading.Thread(target=_mqtt_thread, daemon=True, name="MQTT-Worker")
    th.start()
    return mqtt_client


# ==============================================================================
# RUTAS WEB Y ENDPOINTS DE LA API
# ==============================================================================
@app.route("/")
def index():
    """Sirve la página principal del panel de supervisión."""
    return render_template("index.html")


@app.route("/api/status", methods=["GET"])
def get_status():
    """Retorna el estado completo actual de ambos dispositivos y del sistema."""
    with state_lock:
        return jsonify({
            "system": system_info,
            "devices": devices_state,
            "recent_events": list(recent_events)
        })


@app.route("/api/reset-events", methods=["POST"])
def reset_events():
    """Limpia el buffer de eventos temporales en memoria RAM."""
    recent_events.clear()
    add_event("SYSTEM", "info", "Registro de eventos temporales limpiado por el usuario")
    return jsonify({"success": True})


@app.route("/api/stream")
def sse_stream():
    """
    Canal de Server-Sent Events (SSE) para actualizaciones en tiempo real instantáneas
    hacia el panel web sin sobrecarga de sondeo continuo.
    """
    client_queue = queue.Queue(maxsize=100)
    with sse_lock:
        sse_clients.append(client_queue)

    def event_generator():
        # Enviar estado inicial de bienvenida
        with state_lock:
            initial_payload = {
                "type": "state_snapshot",
                "devices": devices_state,
                "broker_connected": system_info["broker_connected"],
                "recent_events": list(recent_events)
            }
        yield f"data: {json.dumps(initial_payload)}\n\n"

        try:
            while True:
                try:
                    # Esperar hasta 20 segundos por un mensaje nuevo; si no, enviar keepalive ping
                    message = client_queue.get(timeout=20.0)
                    yield message
                except queue.Empty:
                    # Ping para mantener la conexión viva a través de proxies/firewalls
                    yield ": ping\n\n"
        except GeneratorExit:
            with sse_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)

    return Response(
        event_generator(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


# ==============================================================================
# PUNTO DE ENTRADA PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    start_mqtt_client()
    logger.info(f"Iniciando panel web en http://{config.WEB_HOST}:{config.WEB_PORT}")
    app.run(
        host=config.WEB_HOST,
        port=config.WEB_PORT,
        debug=config.DEBUG,
        threaded=True
    )
