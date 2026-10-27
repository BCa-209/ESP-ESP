/**
 * Controlador de Frontend para el Panel de Supervisión Puente MQTT ESP32
 * Actualizaciones en tiempo real mediante Server-Sent Events (SSE) y fallback a Polling.
 */

document.addEventListener("DOMContentLoaded", () => {
  // Elementos DOM
  const brokerPill = document.getElementById("broker-pill");
  const brokerVal = document.getElementById("broker-status-val");
  const streamPill = document.getElementById("stream-pill");
  const streamVal = document.getElementById("stream-status-val");
  const eventsLog = document.getElementById("events-log");
  const btnClear = document.getElementById("btn-clear-events");

  let eventSource = null;
  let pollingInterval = null;

  // =========================================================================
  // ACTUALIZACIÓN VISUAL DE DISPOSITIVOS Y LEDS
  // =========================================================================

  function updateDeviceUI(devId, data) {
    const idLower = devId.toLowerCase(); // 'a' o 'b'

    // Estado de conexión
    const statusBox = document.getElementById(`status-${idLower}`);
    if (statusBox) {
      const indicator = statusBox.querySelector(".status-indicator");
      const text = statusBox.querySelector(".status-text");
      const isOnline = data.status === "online";

      indicator.className = `status-indicator ${isOnline ? "online" : "offline"}`;
      text.textContent = isOnline ? "En línea" : "Desconectado";
    }

    // Telemetría / Timestamp
    const lastSeen = document.getElementById(`last-seen-${idLower}`);
    if (lastSeen && data.last_seen) {
      lastSeen.textContent = data.last_seen;
    }

    // LEDs Locales (1 y 2)
    setLedVisual(`led-lamp-${idLower}-local-1`, `tag-${idLower}-local-1`, data.local_ch1, false);
    setLedVisual(`led-lamp-${idLower}-local-2`, `tag-${idLower}-local-2`, data.local_ch2, false);

    // LEDs Receptores / Remotos (1 y 2)
    setLedVisual(`led-lamp-${idLower}-remote-1`, `tag-${idLower}-remote-1`, data.remote_ch1, true);
    setLedVisual(`led-lamp-${idLower}-remote-2`, `tag-${idLower}-remote-2`, data.remote_ch2, true);
  }

  function setLedVisual(lampId, tagId, state, isRemote) {
    const lamp = document.getElementById(lampId);
    const tag = document.getElementById(tagId);

    if (lamp) {
      if (state) {
        lamp.classList.add("on");
      } else {
        lamp.classList.remove("on");
      }
    }

    if (tag) {
      if (state) {
        tag.textContent = "ON";
        tag.className = isRemote ? "led-tag remote-on" : "led-tag on";
      } else {
        tag.textContent = "OFF";
        tag.className = "led-tag off";
      }
    }
  }

  function updateBrokerStatus(connected) {
    if (connected) {
      brokerPill.className = "status-pill connected";
      brokerVal.textContent = "Conectado";
    } else {
      brokerPill.className = "status-pill disconnected";
      brokerVal.textContent = "Desconectado";
    }
  }

  // =========================================================================
  // GESTIÓN DE EVENTOS TEMPORALES EN PANTALLA
  // =========================================================================

  function renderEventRow(event) {
    const emptyPlaceholder = eventsLog.querySelector(".events-empty");
    if (emptyPlaceholder) {
      emptyPlaceholder.remove();
    }

    const row = document.createElement("div");
    let typeClass = "event-toggle";
    if (event.type === "status") typeClass = "event-status";
    if (event.type === "warning") typeClass = "event-warning";
    if (event.type === "error") typeClass = "event-error";

    row.className = `event-row ${typeClass}`;
    row.innerHTML = `
      <span class="event-time">${escapeHtml(event.time)}</span>
      <span class="event-dev">${escapeHtml(event.device)}</span>
      <span class="event-desc">${escapeHtml(event.desc)}</span>
    `;

    eventsLog.prepend(row);

    // Limitar elementos visibles en el DOM a 50
    while (eventsLog.children.length > 50) {
      eventsLog.removeChild(eventsLog.lastChild);
    }
  }

  function renderEventsList(eventsArray) {
    eventsLog.innerHTML = "";
    if (!eventsArray || eventsArray.length === 0) {
      eventsLog.innerHTML = '<div class="events-empty">Sin eventos registrados aún.</div>';
      return;
    }
    // eventsArray viene del deque más reciente al más antiguo
    eventsArray.slice().reverse().forEach((ev) => {
      renderEventRow(ev);
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  // =========================================================================
  // CONEXIÓN EN TIEMPO REAL VÍA SERVER-SENT EVENTS (SSE)
  // =========================================================================

  function initSSE() {
    if (eventSource) {
      eventSource.close();
    }

    streamPill.className = "status-pill";
    streamVal.textContent = "Conectando...";

    eventSource = new EventSource("/api/stream");

    eventSource.onopen = () => {
      streamPill.className = "status-pill connected";
      streamVal.textContent = "En vivo (SSE)";
      stopPolling();
    };

    eventSource.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        handleServerMessage(msg);
      } catch (err) {
        console.error("Error al procesar mensaje SSE:", err, e.data);
      }
    };

    eventSource.onerror = () => {
      streamPill.className = "status-pill disconnected";
      streamVal.textContent = "Reconectando / Polling";
      startPolling();
    };
  }

  function handleServerMessage(msg) {
    if (msg.type === "state_snapshot") {
      if (msg.devices) {
        if (msg.devices.A) updateDeviceUI("A", msg.devices.A);
        if (msg.devices.B) updateDeviceUI("B", msg.devices.B);
      }
      if (typeof msg.broker_connected !== "undefined") {
        updateBrokerStatus(msg.broker_connected);
      }
      if (msg.recent_events && eventsLog.children.length <= 1) {
        renderEventsList(msg.recent_events);
      }
    } else if (msg.type === "event" && msg.data) {
      renderEventRow(msg.data);
    } else if (msg.type === "broker_status") {
      updateBrokerStatus(msg.connected);
    }
  }

  // =========================================================================
  // FALLBACK MEDIANTE POLLING (Si SSE se interrumpe)
  // =========================================================================

  function fetchStatusOnce() {
    fetch("/api/status")
      .then((res) => res.json())
      .then((data) => {
        if (data.devices) {
          if (data.devices.A) updateDeviceUI("A", data.devices.A);
          if (data.devices.B) updateDeviceUI("B", data.devices.B);
        }
        if (data.system) {
          updateBrokerStatus(data.system.broker_connected);
        }
      })
      .catch((err) => {
        console.warn("Fallo en sondeo /api/status:", err);
      });
  }

  function startPolling() {
    if (pollingInterval) return;
    fetchStatusOnce();
    pollingInterval = setInterval(fetchStatusOnce, 2500);
  }

  function stopPolling() {
    if (pollingInterval) {
      clearInterval(pollingInterval);
      pollingInterval = null;
    }
  }

  // =========================================================================
  // ACCIONES DE USUARIO
  // =========================================================================

  btnClear.addEventListener("click", () => {
    fetch("/api/reset-events", { method: "POST" })
      .then(() => {
        eventsLog.innerHTML = '<div class="events-empty">Registro de eventos limpiado.</div>';
      })
      .catch((err) => console.error("Error al limpiar eventos:", err));
  });

  // Carga inicial y arranque de SSE
  fetchStatusOnce();
  initSSE();
});
