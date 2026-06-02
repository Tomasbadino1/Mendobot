/**
 * MendoBot — Módulo de Escucha, Voz e Interpretación (RF-05).
 *
 * Autónomo: funciona en el navegador sin backend, usando respuestas simuladas.
 * - ESCUCHA       → Web Speech API (SpeechRecognition).            [CA-05.1]
 * - VOZ           → Web Speech API (SpeechSynthesis).              [CA-05.2]
 * - FALLBACK      → entrada por texto si no hay micrófono/permiso. [CA-05.3]
 * - INTERPRETACIÓN→ el texto crudo se delega a obtenerRespuesta(); la
 *                   normalización/NLP vive en el motor (engine.py), no acá.
 */

"use strict";

(function () {
  // ---------------------------------------------------------------------------
  // PUNTO DE CONEXIÓN  ←  ÚNICO BLOQUE QUE CAMBIA AL INTEGRAR EL MOTOR REAL
  // ---------------------------------------------------------------------------
  /**
   * Obtiene la respuesta para una consulta llamando al backend real (server.py),
   * que expone engine.buscar_respuesta() en POST /consulta.
   *
   * Si el backend no responde (p. ej. se abrió el HTML estático sin servidor),
   * cae al mock local para que el prototipo siga demostrable offline.
   *
   * @param {string} textoConsulta
   * @returns {Promise<{found: boolean, message: string, animate_avatar: boolean}>}
   */
  async function obtenerRespuesta(textoConsulta) {
    try {
      const resp = await fetch("/consulta", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texto: textoConsulta }),
      });
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      return await resp.json(); // { found, message, animate_avatar }
    } catch (_e) {
      // Fallback offline: sin backend, se usa el mock local (si está cargado).
      if (window.MendobotMock) {
        return window.MendobotMock.buscarRespuestaSimulada(textoConsulta);
      }
      throw _e;
    }
  }
  // ---------------------------------------------------------------------------
  // FIN PUNTO DE CONEXIÓN
  // ---------------------------------------------------------------------------

  // --- Referencias a la UI ---
  const $conversacion = document.getElementById("conversacion");
  const $micBtn = document.getElementById("mic-btn");
  const $textInput = document.getElementById("text-input");
  const $sendBtn = document.getElementById("send-btn");
  const $estado = document.getElementById("estado");
  const $vozChk = document.getElementById("voz-activa");

  // --- Estado del módulo ---
  const Estado = {
    INACTIVO: "Listo",
    ESCUCHANDO: "Escuchando…",
    TRANSCRIBIENDO: "Transcribiendo…",
    PROCESANDO: "Procesando…",
  };
  let escuchando = false;

  // --- Detección de capacidades (CA-05.3) ---
  const SpeechRecognition =
    window.SpeechRecognition || window.webkitSpeechRecognition || null;
  const sintesisDisponible = "speechSynthesis" in window;
  let recognition = null;

  // --- Captura de audio para STT en el servidor (Vosk, offline) ---
  // Se usa como fallback cuando el navegador no soporta Web Speech o este falla
  // con `network`/`service-not-allowed` (servicio remoto de Google no disponible).
  let usarServidorSTT = !SpeechRecognition;
  let grabando = false;
  let audioCtx = null;
  let mediaStream = null;
  let procNode = null;
  let sourceNode = null;
  let pcmChunks = [];

  // ---------------------------------------------------------------------------
  // Render de conversación (RNF-02: legible y usable)
  // ---------------------------------------------------------------------------
  function agregarMensaje(texto, autor) {
    const burbuja = document.createElement("div");
    burbuja.className = "msg msg-" + autor; // autor: "user" | "bot" | "sys"
    burbuja.textContent = texto;
    $conversacion.appendChild(burbuja);
    $conversacion.scrollTop = $conversacion.scrollHeight;
  }

  function setEstado(texto) {
    $estado.textContent = texto;
  }

  // ---------------------------------------------------------------------------
  // Síntesis de voz / TTS (CA-05.2)
  // ---------------------------------------------------------------------------
  function hablar(texto) {
    if (!sintesisDisponible || !$vozChk.checked) return;
    try {
      window.speechSynthesis.cancel(); // corta lo anterior si seguía hablando
      const utter = new SpeechSynthesisUtterance(texto);
      utter.lang = "es-AR";
      const vozEs = window.speechSynthesis
        .getVoices()
        .find((v) => v.lang && v.lang.toLowerCase().startsWith("es"));
      if (vozEs) utter.voice = vozEs;
      window.speechSynthesis.speak(utter);
    } catch (_e) {
      // La voz es complementaria: si falla, el texto ya quedó en pantalla.
    }
  }

  // ---------------------------------------------------------------------------
  // Pipeline central: una consulta (de voz o texto) → respuesta
  // INTERPRETACIÓN: se envía el texto crudo, sin reimplementar NLP.
  // ---------------------------------------------------------------------------
  async function procesarConsulta(texto) {
    const limpio = (texto || "").trim();
    if (!limpio) return;

    agregarMensaje(limpio, "user");
    setEstado(Estado.PROCESANDO);
    $textInput.value = "";

    let respuesta;
    try {
      respuesta = await obtenerRespuesta(limpio);
    } catch (_e) {
      respuesta = {
        found: false,
        message: "Ocurrió un problema al obtener la respuesta. Intentá de nuevo.",
        animate_avatar: false,
      };
    }

    agregarMensaje(respuesta.message, "bot");

    // animate_avatar se deja disponible para RF-06 (uso futuro). Hoy solo se loguea.
    if (respuesta.animate_avatar) {
      console.debug("[avatar] animación activada (uso futuro RF-06)");
    }

    if (respuesta.found) {
      hablar(respuesta.message); // CA-05.2: solo se sintetiza una respuesta válida.
    }

    setEstado(Estado.INACTIVO);
  }

  // ---------------------------------------------------------------------------
  // Escucha / STT (CA-05.1) + Fallback (CA-05.3)
  // ---------------------------------------------------------------------------
  function configurarReconocimiento() {
    recognition = new SpeechRecognition();
    recognition.lang = "es-AR";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    recognition.onstart = () => {
      escuchando = true;
      $micBtn.classList.add("activo");
      $micBtn.setAttribute("aria-pressed", "true");
      setEstado(Estado.ESCUCHANDO);
    };

    recognition.onresult = (evento) => {
      const transcripcion = evento.results[0][0].transcript;
      procesarConsulta(transcripcion); // mismo camino que el texto escrito.
    };

    recognition.onerror = (evento) => {
      escuchando = false;
      $micBtn.classList.remove("activo");
      $micBtn.setAttribute("aria-pressed", "false");

      // Diagnóstico en consola (F12) con el código crudo del navegador.
      console.warn("[voz] SpeechRecognition error:", evento.error, evento);

      let msg;
      switch (evento.error) {
        case "not-allowed":
          // CA-05.3: permiso denegado → informar y permitir continuar por texto.
          msg =
            "No se pudo acceder al micrófono (permiso denegado). " +
            "Habilitá el permiso del sitio y reintentá, o usá la caja de texto.";
          break;
        case "no-speech":
          msg = "No se detectó voz. Probá de nuevo o escribí tu consulta.";
          break;
        case "audio-capture":
          msg =
            "No se detectó ningún micrófono. Verificá que haya uno conectado " +
            "y habilitado, o usá la caja de texto.";
          break;
        case "network":
        case "service-not-allowed":
          // El reconocimiento del navegador (servidor remoto de Google) no está
          // disponible. Cambiamos al STT local del backend (Vosk, offline).
          usarServidorSTT = true;
          msg =
            "El reconocimiento del navegador no está disponible. Activé el modo " +
            "local (offline): tocá el micrófono de nuevo para hablar.";
          break;
        case "aborted":
          msg = "La escucha se interrumpió. Reintentá tocando el micrófono.";
          break;
        default:
          msg =
            "La entrada por voz no está disponible ahora (" +
            (evento.error || "desconocido") +
            "). Usá la caja de texto.";
      }
      agregarMensaje(msg, "sys");
      setEstado(Estado.INACTIVO);
    };

    recognition.onend = () => {
      escuchando = false;
      $micBtn.classList.remove("activo");
      $micBtn.setAttribute("aria-pressed", "false");
      if ($estado.textContent === Estado.ESCUCHANDO) setEstado(Estado.INACTIVO);
    };
  }

  function alternarEscucha() {
    if (!recognition) return;
    if (escuchando) {
      recognition.stop();
      return;
    }
    try {
      recognition.start();
    } catch (_e) {
      // start() lanza si ya está activo; se ignora de forma segura.
    }
  }

  // ---------------------------------------------------------------------------
  // Inicialización
  // ---------------------------------------------------------------------------
  function init() {
    // Entrada por texto: siempre disponible (CA-05.3 / fallback permanente).
    $sendBtn.addEventListener("click", () => procesarConsulta($textInput.value));
    $textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") procesarConsulta($textInput.value);
    });

    if (SpeechRecognition) {
      configurarReconocimiento();
      $micBtn.addEventListener("click", alternarEscucha);
    } else {
      // CA-05.3: navegador sin soporte → deshabilitar mic, informar, no bloquear.
      $micBtn.disabled = true;
      $micBtn.title = "Reconocimiento de voz no soportado en este navegador";
      $micBtn.classList.add("deshabilitado");
      agregarMensaje(
        "Tu navegador no soporta reconocimiento de voz. " +
          "Podés usar MendoBot escribiendo en la caja de texto.",
        "sys"
      );
    }

    if (!sintesisDisponible) {
      $vozChk.checked = false;
      $vozChk.disabled = true;
    }

    setEstado(Estado.INACTIVO);
    agregarMensaje(
      "¡Hola! Soy MendoBot. Tocá el micrófono y hablá, o escribí tu consulta.",
      "bot"
    );
  }

  // Algunas implementaciones cargan las voces de TTS de forma asíncrona.
  if (sintesisDisponible && typeof window.speechSynthesis.onvoiceschanged !== "undefined") {
    window.speechSynthesis.onvoiceschanged = () => {};
  }

  document.addEventListener("DOMContentLoaded", init);
})();
