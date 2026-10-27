"""
Configuración general del Servidor Puente y Panel Web.
Todos los valores pueden ser sobrescritos mediante variables de entorno.
"""
import os

# Configuración del servidor Web Flask
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "5000"))
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

# Configuración del Broker MQTT
MQTT_BROKER = os.getenv("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_USER = os.getenv("MQTT_USER", None)
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", None)

# Tópicos MQTT
TOPIC_STATE_WILDCARD = "lab/esp32/+/state"
TOPIC_STATUS_WILDCARD = "lab/esp32/+/status"

# Parámetros de buffer de eventos en RAM (sin base de datos)
MAX_IN_MEMORY_EVENTS = 50
