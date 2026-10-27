# Carpeta de Fotografías del Experimento Real

Los diagramas de pines (pinouts), conexionado esquemático, diagramas de bloques y flujo del firmware se generan ahora de forma **100% vectorial nativa en LaTeX (TikZ)**, por lo que **no requieren imágenes externas**.

Esta carpeta está reservada exclusivamente para las **fotografías reales del experimento**:

1. `fotografia_montaje_experimental.png` (o `.jpg` / `.pdf`):
   - Fotografía general del banco de pruebas del experimento en el laboratorio.
   - Debe mostrar las dos protoboards con los microcontroladores ESP32 A (30 pines) y ESP32 B (38 pines), cableado con pulsadores y LEDs activos.

2. `fotografia_conmutacion_canales.png` (o `.jpg` / `.pdf`):
   - Fotografía de primer plano o detalle durante la prueba de conmutación.
   - Muestra la pulsación manual de un canal y la respuesta óptica simultánea de los LEDs locales y remotos en el hardware real.

Al guardar tus fotos con estos nombres en esta carpeta, el documento LaTeX las integrará automáticamente al recompilar.
