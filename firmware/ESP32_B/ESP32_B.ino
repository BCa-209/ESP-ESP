/*
 * =====================================================================
 * FIRMWARE PARA ESP32 B (Placa de 38 pines)
 * Sistema de comunicación bidireccional entre dos ESP32 vía MQTT
 * =====================================================================
 * 
 * Hardware:
 *   - Pulsador Canal 1: GPIO 32 (a GND, usando INPUT_PULLUP)
 *   - Pulsador Canal 2: GPIO 33 (a GND, usando INPUT_PULLUP)
 *   - LED Local Canal 1: GPIO 18 (con resistencia limitadora de 220-330 ohm a GND)
 *   - LED Local Canal 2: GPIO 19 (con resistencia limitadora de 220-330 ohm a GND)
 *   - LED Receptor Canal 1 (Remoto): GPIO 21 (con resistencia limitadora a GND)
 *   - LED Receptor Canal 2 (Remoto): GPIO 22 (con resistencia limitadora a GND)
 *
 * Bibliotecas requeridas (Arduino Library Manager):
 *   - PubSubClient (por Nick O'Leary)
 *   - ArduinoJson (v6 o v7, por Benoit Blanchon)
 * =====================================================================
 */

#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ==================================================
// CONFIGURACION ESPECIFICA DEL DISPOSITIVO
// ==================================================
#define DEVICE_ID "B" // Identificador para esta placa (38 pines)

// Credenciales Wi-Fi (cambiar por las de tu red o hotspot de la laptop)
const char* WIFI_SSID     = "DESKTOP-TSJBC22-6549";
const char* WIFI_PASSWORD = "12345678900";

// IP del servidor broker Mosquitto en la laptop:
// - Si usas la red Wi-Fi compartida con el router: "10.55.14.181"
// - Si usas Zona de cobertura móvil / Hotspot de Windows: "192.168.137.1"
const char* MQTT_HOST     = "10.242.28.66";
const uint16_t MQTT_PORT  = 1883;

// ==================================================
// DEFINICION DE PINES (GPIO)
// ==================================================
const uint8_t BUTTON_1     = 32;
const uint8_t BUTTON_2     = 33;

const uint8_t LED_LOCAL_1  = 18;
const uint8_t LED_LOCAL_2  = 19;

const uint8_t LED_REMOTO_1 = 21;
const uint8_t LED_REMOTO_2 = 22;

const unsigned long DEBOUNCE_MS = 40;

// ==================================================
// CLIENTES DE RED Y MQTT
// ==================================================
WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String ownStateTopic;
String peerStateTopic;
String ownStatusTopic;
String peerStatusTopic;

// Estados de canales locales y remotos
bool channel1       = false;
bool channel2       = false;
bool remoteChannel1 = false;
bool remoteChannel2 = false;

// Estructura para antirrebote no bloqueante
struct ButtonState {
  uint8_t pin;
  bool lastReading;
  bool stableState;
  unsigned long lastChange;
};

ButtonState button1 = {BUTTON_1, HIGH, HIGH, 0};
ButtonState button2 = {BUTTON_2, HIGH, HIGH, 0};

unsigned long lastMqttAttempt = 0;
unsigned long lastWifiAttempt = 0;

// ==================================================
// PUBLICACION DE ESTADOS LOCALES
// ==================================================
void publishState() {
  if (!mqtt.connected()) return;

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  StaticJsonDocument<128> doc;
#endif

  doc["device"]   = DEVICE_ID;
  doc["channel1"] = channel1;
  doc["channel2"] = channel2;

  char payload[128];
  serializeJson(doc, payload, sizeof(payload));

  // Publicar con flag 'retained' = true para que el broker guarde
  // el último estado en RAM y lo entregue a nuevos suscriptores
  mqtt.publish(ownStateTopic.c_str(), payload, true);

  Serial.print("[ESP32-B] Estado local publicado: ");
  Serial.println(payload);
}

// ==================================================
// CALLBACK DE MENSAJES MQTT RECIBIDOS
// ==================================================
void mqttCallback(char* topic, byte* payload, unsigned int length) {
  String receivedTopic(topic);
  String message;
  message.reserve(length);

  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // Si el otro ESP32 se conecta ("online"), le reenviamos nuestro estado actual
  if (receivedTopic == peerStatusTopic) {
    Serial.print("[ESP32-B] Notificación de estado remoto: ");
    Serial.println(message);
    if (message == "online") {
      publishState();
    }
    return;
  }

  // Filtrar que el mensaje corresponda al topic de estado del par (ESP32 A)
  if (receivedTopic != peerStateTopic) return;

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  StaticJsonDocument<128> doc;
#endif

  DeserializationError error = deserializeJson(doc, message);
  if (error) {
    Serial.print("[ESP32-B] Error al deserializar JSON: ");
    Serial.println(error.f_str());
    return;
  }

  remoteChannel1 = doc["channel1"] | false;
  remoteChannel2 = doc["channel2"] | false;

  // Actualizar LEDs receptores físicos
  digitalWrite(LED_REMOTO_1, remoteChannel1 ? HIGH : LOW);
  digitalWrite(LED_REMOTO_2, remoteChannel2 ? HIGH : LOW);

  Serial.print("[ESP32-B] Estado recibido de A -> Ch1: ");
  Serial.print(remoteChannel1 ? "ON" : "OFF");
  Serial.print(" | Ch2: ");
  Serial.println(remoteChannel2 ? "ON" : "OFF");
}

// ==================================================
// GESTION DE CONEXION MQTT
// ==================================================
void connectMQTT() {
  if (mqtt.connected()) return;

  // Intentar reconectar cada 3 segundos sin bloquear el loop
  if (millis() - lastMqttAttempt < 3000) return;
  lastMqttAttempt = millis();

  // Client ID único basado en MAC
  String clientId = "ESP32-";
  clientId += DEVICE_ID;
  clientId += "-";
  clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

  Serial.print("[ESP32-B] Conectando a MQTT Broker...");

  // Configurar Last Will and Testament (LWT) retenido con mensaje "offline"
  bool connected = mqtt.connect(
    clientId.c_str(),
    ownStatusTopic.c_str(),
    1,
    true,
    "offline"
  );

  if (!connected) {
    Serial.print(" Falló, rc=");
    Serial.println(mqtt.state());
    return;
  }

  Serial.println(" Conectado!");

  // Anunciar disponibilidad propia retenida
  mqtt.publish(ownStatusTopic.c_str(), "online", true);

  // Suscribirse a los estados y disponibilidad de ESP32 A
  mqtt.subscribe(peerStateTopic.c_str());
  mqtt.subscribe(peerStatusTopic.c_str());

  // Publicar estado actual inmediatamente al conectar
  publishState();
}

// ==================================================
// LECTURA DE PULSADOR CON ANTIRREBOTE (DEBOUNCE)
// ==================================================
void checkButton(ButtonState &btn, bool &chState, uint8_t ledPin) {
  bool reading = digitalRead(btn.pin);

  if (reading != btn.lastReading) {
    btn.lastChange = millis();
    btn.lastReading = reading;
  }

  if (millis() - btn.lastChange >= DEBOUNCE_MS) {
    if (reading != btn.stableState) {
      btn.stableState = reading;

      // Con INPUT_PULLUP, LOW indica botón presionado
      if (btn.stableState == LOW) {
        chState = !chState;
        digitalWrite(ledPin, chState ? HIGH : LOW);

        Serial.print("[ESP32-B] Pulsador GPIO ");
        Serial.print(btn.pin);
        Serial.print(" presionado -> Canal: ");
        Serial.println(chState ? "ON" : "OFF");

        publishState();
      }
    }
  }
}

// ==================================================
// CONFIGURACION DE TOPICS MQTT
// ==================================================
void setupTopics() {
  String peerId = (String(DEVICE_ID) == "A") ? "B" : "A";

  ownStateTopic   = "lab/esp32/" + String(DEVICE_ID) + "/state";
  ownStatusTopic  = "lab/esp32/" + String(DEVICE_ID) + "/status";

  peerStateTopic  = "lab/esp32/" + peerId + "/state";
  peerStatusTopic = "lab/esp32/" + peerId + "/status";
}

// ==================================================
// SETUP
// ==================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  // Configuración de entradas (pulsadores a GND con pull-up)
  pinMode(BUTTON_1, INPUT_PULLUP);
  pinMode(BUTTON_2, INPUT_PULLUP);

  // Configuración de salidas (LEDs)
  pinMode(LED_LOCAL_1, OUTPUT);
  pinMode(LED_LOCAL_2, OUTPUT);
  pinMode(LED_REMOTO_1, OUTPUT);
  pinMode(LED_REMOTO_2, OUTPUT);

  digitalWrite(LED_LOCAL_1, LOW);
  digitalWrite(LED_LOCAL_2, LOW);
  digitalWrite(LED_REMOTO_1, LOW);
  digitalWrite(LED_REMOTO_2, LOW);

  setupTopics();

  Serial.println();
  Serial.println("==================================================");
  Serial.print("Iniciando ESP32 ");
  Serial.println(DEVICE_ID);
  Serial.println("==================================================");

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(256);
}

// ==================================================
// LOOP PRINCIPAL (No bloqueante)
// ==================================================
void loop() {
  // Reconexión Wi-Fi periódica no bloqueante
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiAttempt >= 5000) {
      lastWifiAttempt = millis();
      Serial.println("[ESP32-B] Intentando reconectar Wi-Fi...");
      WiFi.reconnect();
    }
  } else {
    // Si hay Wi-Fi, atender cliente MQTT
    if (!mqtt.connected()) {
      connectMQTT();
    } else {
      mqtt.loop();
    }
  }

  // Los pulsadores y LEDs locales responden SIEMPRE en tiempo real,
  // incluso si la red o el broker están caídos
  checkButton(button1, channel1, LED_LOCAL_1);
  checkButton(button2, channel2, LED_LOCAL_2);
}
