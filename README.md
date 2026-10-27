# Sistema de Comunicación Bidireccional entre dos ESP32 con Servidor Puente MQTT y Panel Web

Este proyecto implementa una arquitectura IoT desacoplada para la comunicación bidireccional en tiempo real entre dos microcontroladores ESP32 (uno de 30 pines y otro de 38 pines) a través de un broker MQTT (Eclipse Mosquitto) y un panel web de supervisión desarrollado en Flask, **sin utilizar ninguna base de datos** (todos los estados se gestionan en memoria RAM).

---

## 📁 Estructura del Proyecto

```text
ESP-ESP/
│
├── idea_esp32_puente_mqtt_panel_web.md   # Documento de especificación y requerimientos
├── informe_tecnico.tex                  # Informe técnico formal en LaTeX (documento académico/industrial)
├── README.md                            # Guía de instalación, cableado y uso
├── requirements.txt                     # Dependencias de Python (Flask, paho-mqtt)
│
├── firmware/
│   ├── ESP32_A/
│   │   └── ESP32_A.ino                  # Firmware para ESP32 A (30 pines, DEVICE_ID "A")
│   └── ESP32_B/
│       └── ESP32_B.ino                  # Firmware para ESP32 B (38 pines, DEVICE_ID "B")
│
├── mosquitto/
│   ├── mosquitto.conf                   # Configuración para Mosquitto en red local
│   └── mosquitto_prod_sample.conf       # Plantilla con TLS y autenticación para Internet
│
├── server/
│   ├── app.py                           # Servidor Flask puente con cliente MQTT y SSE en memoria
│   ├── config.py                        # Variables de configuración del servidor y MQTT
│   ├── static/
│   │   ├── css/
│   │   │   └── style.css                # Estilos modernos Cyber-Glassmorphism con LEDs realistas
│   │   └── js/
│   │       └── app.js                   # Lógica frontend con Server-Sent Events (SSE) en tiempo real
│   └── templates/
│       └── index.html                   # Panel web de supervisión responsivo
│
└── tools/
    └── simulator.py                     # Simulador interactivo en Python para pruebas sin hardware
```

---

## 🔌 Cableado y Asignación de Pines

Cada placa cuenta con **2 pulsadores** y **4 LEDs**:
- **Pulsadores:** Conectados entre el GPIO asignado y `GND` (el microcontrolador activa su resistencia `INPUT_PULLUP` interna).
- **LEDs:** Conectados desde el GPIO a través de una resistencia en serie de **220 Ω a 330 Ω** hacia `GND`.

| Componente | ESP32 A (30 pines) | ESP32 B (38 pines) | Función |
| :--- | :---: | :---: | :--- |
| **Pulsador Canal 1** | `GPIO 32` | `GPIO 32` | Alterna el Canal 1 local (`ON` / `OFF`) |
| **Pulsador Canal 2** | `GPIO 33` | `GPIO 33` | Alterna el Canal 2 local (`ON` / `OFF`) |
| **LED Local 1** | `GPIO 18` | `GPIO 18` | Refleja el estado del Canal 1 de esta placa |
| **LED Local 2** | `GPIO 19` | `GPIO 19` | Refleja el estado del Canal 2 de esta placa |
| **LED Receptor 1** | `GPIO 21` | `GPIO 21` | Muestra el estado del Canal 1 recibido del otro ESP32 |
| **LED Receptor 2** | `GPIO 22` | `GPIO 22` | Muestra el estado del Canal 2 recibido del otro ESP32 |

> **Nota de seguridad eléctrica:** Los GPIO del ESP32 operan a 3.3V y no toleran 5V. No conectar pulsadores a 5V ni LEDs sin resistencia limitadora.

---

## 🚀 Guía de Puesta en Marcha

### 1. Iniciar el Broker MQTT (Mosquitto)

Si tienes Eclipse Mosquitto instalado en tu equipo, inícialo usando el archivo de configuración provisto:

```powershell
mosquitto -c mosquitto/mosquitto.conf -v
```

*Si usas Docker:*
```powershell
docker run -d --name mosquitto -p 1883:1883 -v ${PWD}/mosquitto/mosquitto.conf:/mosquitto/config/mosquitto.conf eclipse-mosquitto
```

### 2. Iniciar el Servidor Web Flask

1. Instalar las dependencias de Python:
   ```powershell
   pip install -r requirements.txt
   ```
2. Ejecutar el servidor:
   ```powershell
   python server/app.py
   ```
3. Abrir en el navegador: [http://localhost:5000](http://localhost:5000) (o con la IP local de tu laptop desde cualquier dispositivo de la red).

### 3. Cargar el Firmware en las Placas ESP32

1. Abrir **Arduino IDE**.
2. En el *Gestor de Bibliotecas* (`Ctrl + Shift + I`), instalar:
   - **PubSubClient** (por Nick O'Leary)
   - **ArduinoJson** (v6 o v7, por Benoit Blanchon)
3. Modificar en ambos archivos `ESP32_A.ino` y `ESP32_B.ino`:
   - `WIFI_SSID`: Nombre de tu red Wi-Fi o Hotspot móvil.
   - `WIFI_PASSWORD`: Contraseña de la red Wi-Fi.
   - `MQTT_HOST`: Dirección IP de la laptop/servidor donde corre Mosquitto.
4. Conectar la placa de 30 pines y subir:
   `firmware/ESP32_A/ESP32_A.ino`
5. Conectar la placa de 38 pines y subir:
   `firmware/ESP32_B/ESP32_B.ino`

---

## 🧪 Pruebas con el Simulador (Sin Hardware)

Puedes comprobar el panel web y el broker inmediatamente antes de cablear los circuitos:

1. Asegúrate de tener Mosquitto y el servidor Flask corriendo.
2. Abre una terminal y ejecuta:
   ```powershell
   python tools/simulator.py
   ```
3. Usa las teclas `1`, `2`, `3`, `4` para alternar canales, y `a` o `b` para simular desconexiones en tiempo real. Observa cómo el panel web actualiza los indicadores luminosos de inmediato.

---

## 🌐 Migración a Producción / Internet

Para desplegar en una VPS o servidor en la nube:
1. Usar la plantilla `mosquitto/mosquitto_prod_sample.conf` para habilitar el puerto `8883` con certificados TLS (Let's Encrypt) y credenciales de usuario.
2. En el firmware ESP32, sustituir `WiFiClient` por `WiFiClientSecure` y configurar el certificado raíz CA.
3. El panel web puede alojarse detrás de Nginx con Gunicorn o como servicio systemd.
