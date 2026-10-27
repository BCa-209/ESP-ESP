"""
Simulador Interactivo de ESP32 A y ESP32 B vía MQTT.
Permite probar el sistema completo (broker Mosquitto y panel web) sin necesidad
de tener el hardware físico conectado.
"""

import json
import os
import sys
import time
import paho.mqtt.client as mqtt

BROKER_HOST = os.getenv("MQTT_BROKER", "127.0.0.1")
BROKER_PORT = int(os.getenv("MQTT_PORT", "1883"))

# Estados simulados
state_a = {"device": "A", "channel1": False, "channel2": False}
state_b = {"device": "B", "channel1": False, "channel2": False}

connected_a = True
connected_b = True

def get_client(device_id):
    try:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"Simulador-ESP32-{device_id}")
    except AttributeError:
        client = mqtt.Client(client_id=f"Simulador-ESP32-{device_id}")

    # LWT
    client.will_set(f"lab/esp32/{device_id}/status", payload="offline", qos=1, retain=True)

    def on_connect(c, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[Simulador-{device_id}] Conectado al broker MQTT en {BROKER_HOST}:{BROKER_PORT}")
            c.publish(f"lab/esp32/{device_id}/status", "online", qos=1, retain=True)
            peer = "B" if device_id == "A" else "A"
            c.subscribe(f"lab/esp32/{peer}/state")
            c.subscribe(f"lab/esp32/{peer}/status")

    def on_message(c, userdata, msg):
        topic = msg.topic
        payload = msg.payload.decode("utf-8")
        peer = "B" if device_id == "A" else "A"
        if topic == f"lab/esp32/{peer}/state":
            print(f"\n >>> [Simulador-{device_id}] Recibió estado de {peer}: {payload}")
        elif topic == f"lab/esp32/{peer}/status":
            print(f"\n >>> [Simulador-{device_id}] Notificación de disponibilidad de {peer}: {payload}")

    client.on_connect = on_connect
    client.on_message = on_message
    return client

client_a = get_client("A")
client_b = get_client("B")

def publish_state_a():
    payload = json.dumps(state_a)
    client_a.publish("lab/esp32/A/state", payload, retain=True)
    print(f"[Simulador-A] Publicado: {payload}")

def publish_state_b():
    payload = json.dumps(state_b)
    client_b.publish("lab/esp32/B/state", payload, retain=True)
    print(f"[Simulador-B] Publicado: {payload}")

def main():
    global connected_a, connected_b

    print("=" * 65)
    print("  SIMULADOR INTERACTIVO ESP32 (A & B) VÍA MQTT")
    print("=" * 65)
    print(f"Conectando a {BROKER_HOST}:{BROKER_PORT}...")

    try:
        client_a.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client_a.loop_start()
        client_b.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
        client_b.loop_start()
    except Exception as e:
        print(f"\nERROR: No se pudo conectar al broker MQTT en {BROKER_HOST}:{BROKER_PORT}.")
        print("Asegúrate de que Mosquitto esté en ejecución.")
        print(f"Detalle: {e}")
        sys.exit(1)

    time.sleep(1)
    publish_state_a()
    publish_state_b()

    print("\nComandos disponibles:")
    print("  1: Alternar Canal 1 de ESP32 A (Pulsador 1)")
    print("  2: Alternar Canal 2 de ESP32 A (Pulsador 2)")
    print("  3: Alternar Canal 1 de ESP32 B (Pulsador 1)")
    print("  4: Alternar Canal 2 de ESP32 B (Pulsador 2)")
    print("  a: Desconectar/Reconectar ESP32 A (prueba de offline/online)")
    print("  b: Desconectar/Reconectar ESP32 B (prueba de offline/online)")
    print("  q: Salir del simulador")
    print("-" * 65)

    try:
        while True:
            cmd = input("\n[Acción 1/2/3/4/a/b/q] > ").strip().lower()
            if cmd == "1":
                state_a["channel1"] = not state_a["channel1"]
                publish_state_a()
            elif cmd == "2":
                state_a["channel2"] = not state_a["channel2"]
                publish_state_a()
            elif cmd == "3":
                state_b["channel1"] = not state_b["channel1"]
                publish_state_b()
            elif cmd == "4":
                state_b["channel2"] = not state_b["channel2"]
                publish_state_b()
            elif cmd == "a":
                connected_a = not connected_a
                if connected_a:
                    client_a.publish("lab/esp32/A/status", "online", retain=True)
                    publish_state_a()
                    print("[Simulador-A] ESP32 A ahora está ONLINE")
                else:
                    client_a.publish("lab/esp32/A/status", "offline", retain=True)
                    print("[Simulador-A] ESP32 A ahora está OFFLINE")
            elif cmd == "b":
                connected_b = not connected_b
                if connected_b:
                    client_b.publish("lab/esp32/B/status", "online", retain=True)
                    publish_state_b()
                    print("[Simulador-B] ESP32 B ahora está ONLINE")
                else:
                    client_b.publish("lab/esp32/B/status", "offline", retain=True)
                    print("[Simulador-B] ESP32 B ahora está OFFLINE")
            elif cmd == "q":
                print("Cerrando simulador...")
                break
            else:
                print("Comando no reconocido. Usa 1, 2, 3, 4, a, b o q.")
    except (KeyboardInterrupt, EOFError):
        print("\nSaliendo...")
    finally:
        client_a.loop_stop()
        client_b.loop_stop()
        client_a.disconnect()
        client_b.disconnect()

if __name__ == "__main__":
    main()
