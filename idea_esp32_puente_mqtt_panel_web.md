# Sistema de comunicación bidireccional entre dos ESP32 con servidor puente y panel web

## 1. Descripción general

El proyecto consiste en implementar un sistema de comunicación bidireccional entre dos placas ESP32: una versión de 30 pines y otra de 38 pines. Cada placa cuenta con dos pulsadores y cuatro LEDs.

Los pulsadores permiten cambiar el estado de dos canales de comunicación. Cada pulsación alterna el canal correspondiente entre **encendido (ON)** y **apagado (OFF)**. El cambio se refleja en los LEDs locales y se transmite al otro ESP32, donde se actualizan los LEDs que representan los estados recibidos.

Un servidor puente, ejecutado inicialmente en una laptop y migrable posteriormente a un host en Internet, retransmite los mensajes entre ambos dispositivos. El servidor no necesita una base de datos. Además, ofrece una página HTML que permite observar el estado de la comunicación y los estados de los LEDs reportados por cada placa.

## 2. Objetivos

### Objetivo general

Desarrollar un sistema de comunicación bidireccional entre dos ESP32 con un servidor puente MQTT y un panel web para supervisar en tiempo real los estados reportados por los dispositivos, sin utilizar una base de datos.

### Objetivos específicos

- Configurar la comunicación inalámbrica entre los dos ESP32 mediante un broker MQTT.
- Permitir que cada placa cambie dos canales mediante pulsadores.
- Reflejar los cambios en los LEDs locales y transmitirlos al dispositivo remoto.
- Visualizar desde un navegador el estado de conexión de las placas y el estado de los canales.
- Mantener la comunicación entre las placas aunque el panel web no esté abierto.
- Diseñar una arquitectura que pueda migrarse de una laptop local a un servidor alojado en Internet.

## 3. Componentes del sistema

### ESP32 A — placa de 30 pines

- Dos pulsadores para controlar los canales 1 y 2.
- Dos LEDs locales que indican el estado de los canales controlados por esta placa.
- Dos LEDs receptores que muestran los estados de los canales reportados por el ESP32 B.
- Conexión Wi-Fi para comunicarse con el servidor puente.

### ESP32 B — placa de 38 pines

- Dos pulsadores para controlar los canales 1 y 2.
- Dos LEDs locales que indican el estado de los canales controlados por esta placa.
- Dos LEDs receptores que muestran los estados de los canales reportados por el ESP32 A.
- Conexión Wi-Fi para comunicarse con el servidor puente.

### Servidor puente

- Ejecuta un broker MQTT, por ejemplo Mosquitto.
- Recibe y retransmite los mensajes MQTT de ambos ESP32.
- Proporciona conectividad para que los dispositivos intercambien sus estados.
- Puede ejecutarse inicialmente en una laptop y posteriormente en un servidor remoto.
- No utiliza una base de datos para almacenar estados o eventos de forma permanente.

### Panel web

- Página HTML accesible desde un navegador.
- Muestra el estado de conexión de cada ESP32.
- Representa visualmente los LEDs locales y receptores de cada placa.
- Puede mostrar mensajes recientes mientras el servidor está en funcionamiento.
- Obtiene los estados comunicados por los ESP32 a través de una aplicación web, por ejemplo, Flask.
- No es necesario mantener abierta la página para que los ESP32 se comuniquen.

## 4. Distribución lógica de los LEDs

Cada placa tiene cuatro LEDs, con la siguiente función:

| LED | Función |
|---|---|
| LED local 1 | Representa el estado del canal 1 controlado por los pulsadores de la placa |
| LED local 2 | Representa el estado del canal 2 controlado por los pulsadores de la placa |
| LED receptor 1 | Representa el estado del canal 1 recibido desde la otra placa |
| LED receptor 2 | Representa el estado del canal 2 recibido desde la otra placa |

La distribución física de pines debe verificarse para cada modelo de ESP32. Los GPIO seleccionados deben estar disponibles en la placa y ser adecuados para entradas o salidas.

## 5. Funcionamiento de los pulsadores

Cada pulsador controla un canal independiente:

1. El usuario pulsa el botón correspondiente.
2. El firmware detecta la pulsación aplicando antirrebote (*debounce*).
3. El estado del canal cambia de OFF a ON o de ON a OFF.
4. El LED local refleja el nuevo estado.
5. El ESP32 publica el estado actualizado mediante MQTT.
6. El servidor puente retransmite el mensaje al otro ESP32.
7. El ESP32 receptor actualiza el LED receptor correspondiente.
8. El panel web actualiza los indicadores cuando recibe el nuevo estado reportado.

Una pulsación debe generar un solo cambio de estado, aunque el contacto físico del botón produzca pequeñas oscilaciones eléctricas.

## 6. Arquitectura de comunicación

```text
                ┌────────────────────────┐
                │       ESP32 A          │
                │  2 pulsadores          │
                │  2 LEDs locales        │
                │  2 LEDs receptores     │
                └───────────┬────────────┘
                            │ Wi-Fi / MQTT
                            ▼
                ┌────────────────────────┐
                │    Servidor puente     │
                │    Broker Mosquitto    │
                │    Sin base de datos   │
                └───────────┬────────────┘
                            │ Wi-Fi / MQTT
                            ▼
                ┌────────────────────────┐
                │       ESP32 B          │
                │  2 pulsadores          │
                │  2 LEDs locales        │
                │  2 LEDs receptores     │
                └────────────────────────┘

                ┌────────────────────────┐
                │       Panel web        │
                │  Estado de ESP32 A/B   │
                │  Indicadores de LEDs   │
                │  Eventos temporales    │
                └───────────┬────────────┘
                            │
                  API / WebSocket o
                  actualización periódica
                            │
                    Servidor web Flask
```

El broker MQTT es el componente que retransmite los mensajes. Flask sirve la página web y expone los estados para el navegador. Estos componentes pueden ejecutarse en la misma laptop o en el mismo servidor, pero cumplen funciones distintas.

## 7. Protocolo MQTT propuesto

Se recomienda utilizar temas (*topics*) separados para los estados y la disponibilidad de cada dispositivo.

Ejemplos de temas:

- `lab/esp32/A/state`: estados de los dos canales del ESP32 A.
- `lab/esp32/B/state`: estados de los dos canales del ESP32 B.
- `lab/esp32/A/status`: disponibilidad del ESP32 A.
- `lab/esp32/B/status`: disponibilidad del ESP32 B.

Ejemplo de mensaje de estado:

```json
{
  "device": "A",
  "channel1": true,
  "channel2": false
}
```

El ESP32 A publica su propio estado y se suscribe al estado del ESP32 B. El ESP32 B hace lo contrario. Cada dispositivo debe ignorar los mensajes que representen su propio estado como si fueran datos remotos.

La aplicación web puede suscribirse a los temas de estado y disponibilidad para actualizar el panel.

### Estado y reconexión

- Cada ESP32 debe publicar sus estados actuales al conectarse o reconectarse.
- La disponibilidad debe actualizarse mediante mensajes de estado y, cuando sea posible, un mensaje MQTT de última voluntad (*Last Will and Testament*).
- Debe definirse si el broker conservará los últimos mensajes en memoria. Para evitar almacenamiento persistente, se puede desactivar la persistencia en disco del broker.
- Si se usan mensajes retenidos (`retain`), se debe tener en cuenta que el broker puede conservarlos en memoria mientras esté ejecutándose. Esto no equivale a una base de datos, pero sí mantiene el último estado durante la sesión del broker.
- Para que el panel muestre datos reales, los ESP32 deben publicar sus estados y señales de disponibilidad; el HTML no puede comprobar directamente el estado eléctrico de un LED.

## 8. Panel web de supervisión

El panel web debe presentar una sección independiente para cada placa.

### Información por dispositivo

- Identificador del dispositivo: ESP32 A o ESP32 B.
- Estado de conexión: en línea, desconectado o estado desconocido.
- Estado del canal 1 local.
- Estado del canal 2 local.
- Estado del canal 1 recibido desde el otro ESP32.
- Estado del canal 2 recibido desde el otro ESP32.
- Hora del último mensaje recibido, si se desea.

### Representación visual

- Un indicador verde representa un canal encendido.
- Un indicador gris representa un canal apagado.
- Una etiqueta de conexión distingue los dispositivos en línea de los desconectados.
- Un área opcional puede mostrar los últimos eventos recibidos durante la sesión.

Los colores son una ayuda visual y deben acompañarse de texto para que el estado también sea comprensible sin depender únicamente del color.

### Actualización

El navegador puede actualizar la información mediante consultas periódicas a una API de Flask o mediante WebSockets/SSE. Para un prototipo, la actualización periódica es sencilla; para una interfaz más inmediata, se puede utilizar una conexión en tiempo real.

El panel es un observador del sistema. Si se cierra el navegador o se detiene Flask, la comunicación entre los ESP32 debe continuar siempre que el broker MQTT siga funcionando y ambos dispositivos estén conectados.

## 9. Servidor local inicial

Durante el desarrollo, una laptop puede actuar como punto de acceso Wi-Fi y servidor puente.

Pasos generales:

1. Crear una red Wi-Fi local desde la laptop o conectar ambos ESP32 y la laptop al mismo router.
2. Instalar Mosquitto en la laptop.
3. Configurar el broker para aceptar conexiones desde la red local.
4. Configurar ambos ESP32 con el SSID, la contraseña y la dirección IP local de la laptop.
5. Ejecutar la aplicación Flask que sirve el panel web.
6. Abrir el panel desde un navegador usando la dirección IP de la laptop y el puerto de la aplicación.
7. Comprobar la comunicación en ambos sentidos, la actualización de LEDs y la detección de desconexiones.

La dirección IP de la laptop debe ser accesible desde ambos ESP32 y mantenerse estable durante las pruebas. La configuración de red y el firewall deben permitir el tráfico necesario.

## 10. Migración a un host en Internet

Cuando el sistema funcione correctamente en la red local, el broker MQTT puede trasladarse a un servidor remoto.

Arquitectura prevista:

- Los dos ESP32 se conectan a una red Wi-Fi con acceso a Internet.
- Ambos se conectan al mismo broker MQTT alojado en el servidor remoto.
- El panel web se publica en el mismo host o en un servicio web asociado.
- El servidor retransmite mensajes sin requerir una base de datos.

### Consideraciones de seguridad

- Utilizar MQTT sobre TLS, normalmente en un puerto configurado para conexiones cifradas, como 8883.
- Configurar usuarios y contraseñas o credenciales individuales para los dispositivos.
- Limitar los permisos mediante ACL para que cada ESP32 solo pueda publicar y suscribirse a los temas necesarios.
- No exponer un broker público con acceso anónimo.
- Proteger el panel web si se publica en Internet.
- No incluir contraseñas reales en un repositorio público.
- Verificar que el proveedor de hosting permita conexiones MQTT TCP persistentes; algunos servicios web solo aceptan HTTP/HTTPS.

## 11. Almacenamiento y persistencia

El sistema no necesita una base de datos.

- Los estados actuales pueden mantenerse en la memoria de la aplicación mientras se ejecuta.
- El historial opcional del panel puede conservarse temporalmente en RAM y desaparecer al reiniciar el servidor.
- La persistencia en disco del broker puede desactivarse si se desea que no guarde estados entre reinicios.
- Si se utilizan mensajes MQTT retenidos, el broker puede mantener el último estado en memoria durante su ejecución. Se debe documentar esta decisión.
- No se conservará un historial permanente salvo que en el futuro se agregue expresamente un mecanismo de almacenamiento.

## 12. Tecnologías propuestas

| Componente | Tecnología |
|---|---|
| Microcontroladores | ESP32 de 30 y 38 pines |
| Firmware | Arduino IDE / C++ |
| Comunicación | Wi-Fi y MQTT |
| Broker MQTT | Eclipse Mosquitto |
| Servidor web | Python y Flask |
| Interfaz | HTML, CSS y JavaScript |
| Actualización del panel | API con consultas periódicas, WebSockets o SSE |
| Persistencia | Ninguna base de datos; estados temporales en memoria |

## 13. Requisitos funcionales

- **RF-01:** Cada ESP32 debe poder conectarse al broker MQTT.
- **RF-02:** Cada pulsador debe alternar el estado de un canal.
- **RF-03:** Los LEDs locales deben representar el estado de los canales de su dispositivo.
- **RF-04:** Los estados deben transmitirse al otro ESP32.
- **RF-05:** Los LEDs receptores deben reflejar los estados reportados por el dispositivo remoto.
- **RF-06:** El panel web debe mostrar el estado de conexión de ambas placas.
- **RF-07:** El panel web debe visualizar los cuatro estados de LED asociados a cada placa.
- **RF-08:** El panel debe actualizarse cuando se reciban nuevos estados.
- **RF-09:** El sistema debe detectar y mostrar desconexiones mediante un mecanismo de disponibilidad o tiempo de espera.
- **RF-10:** La comunicación entre ESP32 debe continuar aunque el navegador esté cerrado.
- **RF-11:** El sistema debe funcionar sin una base de datos.
- **RF-12:** La arquitectura debe permitir cambiar el broker local por uno remoto con los ajustes de red y seguridad correspondientes.

## 14. Requisitos no funcionales

- **RNF-01 — Tiempo de respuesta:** los cambios deben reflejarse con una demora baja, condicionada por la red Wi-Fi y la conexión MQTT.
- **RNF-02 — Fiabilidad:** el firmware debe reconectarse al Wi-Fi y al broker cuando se pierda la conexión.
- **RNF-03 — Consistencia:** al reconectarse, cada ESP32 debe volver a publicar sus estados actuales.
- **RNF-04 — Seguridad:** las conexiones remotas deben utilizar cifrado y autenticación.
- **RNF-05 — Mantenibilidad:** los temas MQTT, pines y parámetros de conexión deben estar claramente documentados.
- **RNF-06 — Independencia del panel:** el panel web no debe ser un requisito para la comunicación entre los dispositivos.
- **RNF-07 — Sin persistencia de aplicación:** no se deben guardar estados ni eventos en una base de datos.

## 15. Pruebas de validación

1. Encender ambos ESP32 y verificar que el panel los muestre en línea.
2. Pulsar el primer botón del ESP32 A y comprobar el LED local y el LED receptor correspondiente del ESP32 B.
3. Repetir la prueba con el segundo botón del ESP32 A.
4. Realizar las mismas pruebas desde el ESP32 B hacia el ESP32 A.
5. Cerrar el navegador y comprobar que los dispositivos sigan comunicándose.
6. Desconectar uno de los ESP32 y comprobar que el panel detecte su ausencia.
7. Reconectar el dispositivo y verificar que publique sus estados actuales.
8. Reiniciar el broker y comprobar la recuperación de la comunicación.
9. Verificar que no se cree ni se utilice una base de datos.
10. Cuando se migre a Internet, probar autenticación, cifrado y acceso desde redes diferentes.

## 16. Alcance y limitaciones

### Alcance

El proyecto cubre la comunicación bidireccional entre dos ESP32, el control de dos canales por dispositivo, la indicación mediante LEDs, el reenvío de mensajes con MQTT y la supervisión a través de una página web.

### Limitaciones

- El panel muestra los estados que los dispositivos comunican; no verifica directamente el voltaje o el funcionamiento físico de los LEDs.
- La comunicación depende de que ambos dispositivos puedan acceder al broker.
- La disponibilidad mostrada en el panel depende del intervalo de publicación, del mecanismo de última voluntad y del tiempo de espera configurado.
- No existe un historial permanente porque no se utiliza una base de datos.
- Un host web convencional puede no permitir conexiones MQTT TCP persistentes; se debe elegir una infraestructura compatible.
- La conexión remota requiere medidas de seguridad adicionales.

## 17. Resultado esperado

Al finalizar, los dos ESP32 podrán intercambiar estados en ambos sentidos. Cada pulsación cambiará un canal y actualizará el LED local y el LED receptor del otro dispositivo. Desde un navegador, el usuario podrá ver qué canales están encendidos o apagados y si las placas están conectadas. El servidor actuará como puente MQTT y ofrecerá el panel de supervisión sin utilizar una base de datos, con la posibilidad de migrar desde una laptop a un host en Internet.


---

## 18. Cableado y asignación de pines

La propuesta inicial utiliza una asignación de GPIO común para ambas placas. Antes de cablear, hay que verificar el modelo exacto y el pinout impreso de cada ESP32: tener 30 o 38 pines y disponer de una salida de 3.3 V o 5 V no garantiza que todas las variantes expongan los mismos GPIO.

### 18.1 Tabla de pines

| Componente | ESP32 A (30 pines) | ESP32 B (38 pines) | Función |
|---|---:|---:|---|
| Pulsador del canal 1 | GPIO 32 | GPIO 32 | Alterna el canal 1 |
| Pulsador del canal 2 | GPIO 33 | GPIO 33 | Alterna el canal 2 |
| LED local del canal 1 | GPIO 18 | GPIO 18 | Muestra el estado local del canal 1 |
| LED local del canal 2 | GPIO 19 | GPIO 19 | Muestra el estado local del canal 2 |
| LED receptor del canal 1 | GPIO 21 | GPIO 21 | Muestra el canal 1 recibido de la otra placa |
| LED receptor del canal 2 | GPIO 22 | GPIO 22 | Muestra el canal 2 recibido de la otra placa |

Esta tabla es una propuesta inicial para placas ESP32 clásicas. Si alguno de esos pines no está expuesto o tiene una función especial en la variante utilizada, debe elegirse otro GPIO adecuado y actualizar el firmware.

### 18.2 Conexión de los pulsadores

Se utilizará la resistencia *pull-up* interna de cada GPIO mediante `INPUT_PULLUP`. Para cada pulsador:

1. Conectar un terminal del pulsador al GPIO asignado.
2. Conectar el otro terminal del pulsador a GND de la misma placa.
3. No conectar el pulsador directamente a 5 V.

Con `INPUT_PULLUP`, la entrada normalmente se lee como `HIGH`; al pulsar, se conecta a GND y se lee como `LOW`. El firmware interpreta esa transición como una pulsación.

### 18.3 Conexión de los LEDs

Cada LED debe tener una resistencia limitadora de corriente en serie. Como punto de partida para LEDs indicadores comunes puede utilizarse una resistencia de **220 Ω a 330 Ω**, verificando la corriente apropiada para el LED y el GPIO.

Conexión recomendada para cada LED:

`GPIO → resistencia de 220–330 Ω → ánodo (+) del LED; cátodo (−) del LED → GND de la misma placa`

Los cuatro LEDs se conectan a los cuatro GPIO definidos en la tabla. No se debe conectar un LED sin resistencia limitadora.

### 18.4 Diferencia entre alimentación de 3.3 V y 5 V

- En la placa de 30 pines, el pin de 3V3 puede alimentar componentes compatibles de bajo consumo, siempre dentro de los límites de la placa.
- En la placa de 38 pines, el pin marcado 5V o VIN depende del diseño de la placa y de cómo esté alimentada. No debe asumirse que siempre es una salida.
- Los GPIO del ESP32 utilizan lógica de 3.3 V y, por regla general, **no son tolerantes a 5 V**. Nunca aplicar 5 V directamente a un GPIO.
- Los LEDs propuestos se controlan desde los GPIO, no desde el pin de alimentación de 3.3 V o 5 V.
- Cada placa puede alimentarse por su propio USB. Para intercambiar mensajes mediante Wi-Fi y MQTT no es necesario unir físicamente las tierras de ambas placas.

---

## 19. Firmware para ambos ESP32

Las dos placas pueden ejecutar el mismo firmware, cambiando únicamente el identificador del dispositivo. Se recomienda guardar dos copias para que sea fácil programarlas y mantenerlas por separado:

- `ESP32_A.ino`: placa de 30 pines, con `DEVICE_ID` configurado como `"A"`.
- `ESP32_B.ino`: placa de 38 pines, con `DEVICE_ID` configurado como `"B"`.

### 19.1 Bibliotecas

En Arduino IDE, instalar estas bibliotecas desde el gestor de bibliotecas:

- **PubSubClient**, para MQTT.
- **ArduinoJson**, para codificar y leer mensajes JSON.

`WiFi.h` se incluye con el paquete de placas ESP32 para Arduino IDE.

### 19.2 Código base completo

El siguiente sketch contiene la lógica de los dos dispositivos. Antes de cargarlo, configurar `DEVICE_ID`, la red Wi-Fi y la dirección IP del broker MQTT.

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ==================================================
// CONFIGURACION: CAMBIAR EN CADA PLACA
// ==================================================

// ESP32 de 30 pines: "A"
// ESP32 de 38 pines: "B"
#define DEVICE_ID "A"

const char* WIFI_SSID = "ESP32-LAB";
const char* WIFI_PASSWORD = "CAMBIA_ESTA_CLAVE";

// IP de la laptop donde se ejecuta Mosquitto.
// Sustituirla por la IP real del equipo servidor.
const char* MQTT_HOST = "192.168.137.1";
const uint16_t MQTT_PORT = 1883;

// ==================================================
// PINES: VERIFICAR EL PINOUT DE CADA PLACA
// ==================================================

const uint8_t BUTTON_1 = 32;
const uint8_t BUTTON_2 = 33;

const uint8_t LED_LOCAL_1 = 18;
const uint8_t LED_LOCAL_2 = 19;

const uint8_t LED_REMOTO_1 = 21;
const uint8_t LED_REMOTO_2 = 22;

const unsigned long DEBOUNCE_MS = 40;

// ==================================================
// MQTT Y ESTADOS
// ==================================================

WiFiClient wifiClient;
PubSubClient mqtt(wifiClient);

String ownStateTopic;
String peerStateTopic;
String ownStatusTopic;
String peerStatusTopic;

bool channel1 = false;
bool channel2 = false;
bool remoteChannel1 = false;
bool remoteChannel2 = false;

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
// PUBLICAR LOS ESTADOS LOCALES
// ==================================================

void publishState() {
  if (!mqtt.connected()) return;

  StaticJsonDocument<128> doc;
  doc["device"] = DEVICE_ID;
  doc["channel1"] = channel1;
  doc["channel2"] = channel2;

  char payload[128];
  size_t len = serializeJson(doc, payload, sizeof(payload));

  // El mensaje retenido permanece en memoria del broker
  // mientras este se ejecuta. Configurar persistence false
  // en Mosquitto para no guardar la persistencia en disco.
  mqtt.publish(ownStateTopic.c_str(), payload, true);

  Serial.print("Estado publicado: ");
  Serial.println(payload);
}

// ==================================================
// RECIBIR ESTADOS DEL OTRO ESP32
// ==================================================

void mqttCallback(char* topic, byte* payload,
                  unsigned int length) {
  String receivedTopic(topic);
  String message;
  message.reserve(length);

  for (unsigned int i = 0; i < length; i++) {
    message += (char)payload[i];
  }

  // Cuando el otro dispositivo anuncia que está online,
  // publicar nuevamente nuestros estados actuales.
  if (receivedTopic == peerStatusTopic) {
    if (message == "online") {
      publishState();
    }
    return;
  }

  if (receivedTopic != peerStateTopic) return;

  StaticJsonDocument<128> doc;
  DeserializationError error = deserializeJson(doc, message);

  if (error) {
    Serial.println("Error al leer el JSON recibido por MQTT");
    return;
  }

  remoteChannel1 = doc["channel1"] | false;
  remoteChannel2 = doc["channel2"] | false;

  digitalWrite(LED_REMOTO_1, remoteChannel1 ? HIGH : LOW);
  digitalWrite(LED_REMOTO_2, remoteChannel2 ? HIGH : LOW);

  Serial.print("Estado recibido de ");
  Serial.print(String(DEVICE_ID) == "A" ? "B" : "A");
  Serial.print(": ");
  Serial.println(message);
}

// ==================================================
// CONECTAR AL BROKER MQTT
// ==================================================

void connectMQTT() {
  if (mqtt.connected()) return;

  if (millis() - lastMqttAttempt < 3000) return;
  lastMqttAttempt = millis();

  String clientId = "ESP32-";
  clientId += DEVICE_ID;
  clientId += "-";
  clientId += String((uint32_t)ESP.getEfuseMac(), HEX);

  Serial.print("Conectando a MQTT... ");

  // El broker publicará "offline" si detecta que esta
  // conexión se pierde inesperadamente.
  bool connected = mqtt.connect(
    clientId.c_str(),
    ownStatusTopic.c_str(),
    1,
    true,
    "offline"
  );

  if (!connected) {
    Serial.print("Error MQTT: ");
    Serial.println(mqtt.state());
    return;
  }

  Serial.println("conectado");

  mqtt.publish(ownStatusTopic.c_str(), "online", true);
  mqtt.subscribe(peerStateTopic.c_str());
  mqtt.subscribe(peerStatusTopic.c_str());

  // Publicar los estados locales actuales al reconectar.
  publishState();
}

// ==================================================
// LEER UN PULSADOR CON ANTIRREBOTE
// ==================================================

void checkButton(ButtonState &button,
                 bool &channelState,
                 uint8_t ledPin) {
  bool reading = digitalRead(button.pin);

  if (reading != button.lastReading) {
    button.lastChange = millis();
    button.lastReading = reading;
  }

  if (millis() - button.lastChange >= DEBOUNCE_MS) {
    if (reading != button.stableState) {
      button.stableState = reading;

      // Con INPUT_PULLUP, LOW significa pulsado.
      if (button.stableState == LOW) {
        channelState = !channelState;

        digitalWrite(ledPin, channelState ? HIGH : LOW);

        Serial.print("Canal cambiado: ");
        Serial.println(channelState ? "ON" : "OFF");

        publishState();
      }
    }
  }
}

// ==================================================
// CONFIGURAR TEMAS MQTT
// ==================================================

void setupTopics() {
  String peerId = (String(DEVICE_ID) == "A") ? "B" : "A";

  ownStateTopic = "lab/esp32/" + String(DEVICE_ID) + "/state";
  ownStatusTopic = "lab/esp32/" + String(DEVICE_ID) + "/status";

  peerStateTopic = "lab/esp32/" + peerId + "/state";
  peerStatusTopic = "lab/esp32/" + peerId + "/status";
}

// ==================================================
// SETUP
// ==================================================

void setup() {
  Serial.begin(115200);

  pinMode(BUTTON_1, INPUT_PULLUP);
  pinMode(BUTTON_2, INPUT_PULLUP);

  pinMode(LED_LOCAL_1, OUTPUT);
  pinMode(LED_LOCAL_2, OUTPUT);
  pinMode(LED_REMOTO_1, OUTPUT);
  pinMode(LED_REMOTO_2, OUTPUT);

  digitalWrite(LED_LOCAL_1, LOW);
  digitalWrite(LED_LOCAL_2, LOW);
  digitalWrite(LED_REMOTO_1, LOW);
  digitalWrite(LED_REMOTO_2, LOW);

  setupTopics();

  Serial.print("Iniciando ESP32 ");
  Serial.println(DEVICE_ID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(mqttCallback);
  mqtt.setBufferSize(256);
}

// ==================================================
// LOOP
// ==================================================

void loop() {
  // Gestionar la conexión Wi-Fi sin bloquear los botones.
  if (WiFi.status() != WL_CONNECTED) {
    if (millis() - lastWifiAttempt >= 5000) {
      lastWifiAttempt = millis();
      WiFi.reconnect();
    }
  } else {
    if (!mqtt.connected()) {
      connectMQTT();
    } else {
      mqtt.loop();
    }
  }

  // Los LEDs locales y pulsadores siguen funcionando
  // aunque el Wi-Fi o el broker estén desconectados.
  checkButton(button1, channel1, LED_LOCAL_1);
  checkButton(button2, channel2, LED_LOCAL_2);
}
```

### 19.3 Configuración para el ESP32 A de 30 pines

En el sketch, usar:

```cpp
#define DEVICE_ID "A"
```

Guardar una copia como `ESP32_A.ino` y configurar `WIFI_SSID`, `WIFI_PASSWORD` y `MQTT_HOST`.

### 19.4 Configuración para el ESP32 B de 38 pines

En la copia del sketch, cambiar a:

```cpp
#define DEVICE_ID "B"
```

Guardar como `ESP32_B.ino`. La red Wi-Fi, la contraseña y la dirección MQTT deben apuntar al mismo servidor que utiliza la placa A.

### 19.5 Funcionamiento durante una desconexión

Los pulsadores y los LEDs locales continúan funcionando aunque se pierda la conexión Wi-Fi o MQTT. Sin embargo, los cambios realizados mientras no hay conexión no se publican inmediatamente. Al reconectarse, el firmware publica el estado local actual. Si se necesita conservar y transmitir cada cambio individual ocurrido durante una desconexión, será necesario añadir una cola temporal de eventos.

---

## 20. Configuración inicial de Mosquitto

Para pruebas en una red local aislada, una configuración mínima puede ser:

```conf
listener 1883 0.0.0.0
allow_anonymous true
persistence false
```

**Esta configuración anónima es únicamente para laboratorio local y no debe exponerse directamente a Internet.** Antes de migrar el broker a un host público, configurar autenticación, cifrado TLS y permisos de publicación/suscripción por dispositivo.

Con `persistence false`, Mosquitto no guarda su estado persistente en disco. Como el firmware publica los estados con `retain=true`, el broker conserva el último estado en memoria mientras se ejecuta. Tras reiniciar el broker, cada ESP32 debe reconectarse y publicar su estado actual.

La dirección `192.168.137.1` utilizada en el ejemplo es solo un valor de muestra. Debe sustituirse por la dirección IP real de la laptop o del servidor que ejecuta Mosquitto.

---

## 21. Pruebas físicas y de comunicación

1. Confirmar el modelo exacto y el pinout de ambas placas.
2. Conectar los dos pulsadores y los cuatro LEDs en cada placa, con resistencias limitadoras para los LEDs.
3. Instalar las bibliotecas necesarias en Arduino IDE.
4. Cargar `ESP32_A.ino` en la placa de 30 pines.
5. Cargar `ESP32_B.ino` en la placa de 38 pines.
6. Iniciar Mosquitto y verificar que ambos ESP32 puedan alcanzar el broker.
7. Abrir los monitores serie a 115200 baudios y comprobar los mensajes de conexión.
8. Pulsar el botón 1 de A y comprobar que cambia su LED local y el LED receptor 1 de B.
9. Repetir con el botón 2 de A y después realizar ambas pruebas desde B hacia A.
10. Cerrar el navegador y comprobar que la comunicación entre las placas continúe.
11. Desconectar una placa y verificar que el panel web detecte la falta de disponibilidad mediante el estado MQTT o un tiempo de espera.
12. Reconectar la placa y verificar que vuelva a publicar sus estados actuales.
13. Reiniciar el broker y verificar que la comunicación se recupere sin una base de datos.

## 22. Notas de implementación

- El panel web muestra los estados que los ESP32 reportan al servidor; no mide directamente el voltaje ni confirma eléctricamente que un LED esté encendido.
- La detección de desconexión en el panel debe basarse en los temas de disponibilidad MQTT y/o en un tiempo de espera desde el último mensaje.
- El panel web es opcional para el funcionamiento de los dispositivos. El broker debe continuar retransmitiendo mensajes aunque el navegador esté cerrado.
- Los pines indicados son una asignación propuesta y deben verificarse con las placas reales antes del montaje definitivo.
- Para un host público, no se debe reutilizar la configuración MQTT anónima del laboratorio.
