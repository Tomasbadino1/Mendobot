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
  const $mouthShape = document.getElementById("mouth-shape");

  const MOUTH_IMAGES = {
    neutral: "/model/Bocas/Boca_neutral.png",
    abp: "/model/Bocas/M_B_P.png",
    ldt: "/model/Bocas/L_D_T.png",
    ah: "/model/Bocas/A_H.png",
    ei: "/model/Bocas/E_I.png",
    o: "/model/Bocas/O.png",
    uq: "/model/Bocas/U_Q.png",
  };
  let mouthAnimationTimer = null;

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
  const mediaDevicesDisponible = !!(
    navigator.mediaDevices && navigator.mediaDevices.getUserMedia
  );
  let recognition = null;

  // --- Captura de audio para STT en el servidor (Vosk, offline) ---
  // Se usa cuando el navegador no soporta Web Speech o este falla con
  // `network`/`service-not-allowed` (servicio remoto de Google no disponible).
  const STT_SAMPLE_RATE = 16000; // tasa que espera el modelo Vosk del servidor.
  let usarServidorSTT = !SpeechRecognition && mediaDevicesDisponible;
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
    burbuja.scrollIntoView({ behavior: "smooth", block: "end" });
    $conversacion.scrollTop = $conversacion.scrollHeight;
    window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
  }

  function setEstado(texto) {
    $estado.textContent = texto;
  }

  // ---------------------------------------------------------------------------
  // Animación simple de boca basada en el texto de la respuesta.
  // ---------------------------------------------------------------------------
  function setMouthImage(src, alt) {
    if (!$mouthShape) return;
    $mouthShape.src = src;
    $mouthShape.alt = alt;
  }

  function elegirBocaPorCaracter(caracter) {
    if (/[mbp]/.test(caracter)) return { src: MOUTH_IMAGES.abp, alt: "Boca para M/B/P" };
    if (/[ldt]/.test(caracter)) return { src: MOUTH_IMAGES.ldt, alt: "Boca para L/D/T" };
    if (/[aiáí]/.test(caracter)) return { src: MOUTH_IMAGES.ah, alt: "Boca para A/I" };
    if (/[eé]/.test(caracter)) return { src: MOUTH_IMAGES.ei, alt: "Boca para E" };
    if (/[oó]/.test(caracter)) return { src: MOUTH_IMAGES.o, alt: "Boca para O" };
    if (/[uúüq]/.test(caracter)) return { src: MOUTH_IMAGES.uq, alt: "Boca para U/Q" };
    return null;
  }

  function construirSecuenciaBoca(texto) {
    const negrita = String(texto || "").toLowerCase().replace(/[^a-záéíóúüñ ]+/g, " ");
    const caracteres = negrita.replace(/\s+/g, " ").trim().split("");
    const secuencia = [];

    for (const caracter of caracteres) {
      const boca = elegirBocaPorCaracter(caracter);
      if (!boca) continue;
      if (!secuencia.length || secuencia[secuencia.length - 1].src !== boca.src) {
        secuencia.push(boca);
      }
      if (secuencia.length >= 8) break;
    }

    return secuencia.length ? secuencia : [{ src: MOUTH_IMAGES.neutral, alt: "Boca neutral" }];
  }

  function detenerAnimacionBoca() {
    if (mouthAnimationTimer !== null) {
      clearTimeout(mouthAnimationTimer);
      mouthAnimationTimer = null;
    }
  }

  function animarBocaDesdeTexto(texto) {
    detenerAnimacionBoca();
    const secuencia = construirSecuenciaBoca(texto);
    let indice = 0;

    const siguiente = () => {
      if (indice >= secuencia.length) {
        indice = 0; // reinicia en bucle durante la voz
      }
      setMouthImage(secuencia[indice].src, secuencia[indice].alt);
      indice += 1;
      mouthAnimationTimer = setTimeout(siguiente, 180);
    };

    siguiente();
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
      
      // cuando termina la síntesis, detener la animación de boca
      utter.onend = () => {
        detenerAnimacionBoca();
        setMouthImage(MOUTH_IMAGES.neutral, "Boca neutral");
      };
      
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
      animarBocaDesdeTexto(respuesta.message);
      hablar(respuesta.message); // CA-05.2: solo se sintetiza una respuesta válida.
    } else {
      animarBocaDesdeTexto(respuesta.message);
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
          // disponible. Si podemos grabar, pasamos al STT local (Vosk, offline).
          if (mediaDevicesDisponible) {
            usarServidorSTT = true;
            msg =
              "El reconocimiento del navegador no está disponible. Activé el modo " +
              "local (offline): tocá el micrófono de nuevo para hablar.";
          } else {
            msg =
              "El reconocimiento del navegador no está disponible y este navegador " +
              "no permite grabar audio. Usá la caja de texto.";
          }
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
  // STT local vía servidor (Vosk, offline) — CA-05.3
  // Graba del micrófono, codifica WAV mono 16-bit y lo manda a POST /transcribir.
  // El texto resultante sigue el MISMO camino que una consulta escrita.
  // ---------------------------------------------------------------------------
  async function iniciarGrabacionLocal() {
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (_e) {
      // CA-05.3: permiso denegado → informar y seguir por texto.
      agregarMensaje(
        "No se pudo acceder al micrófono (permiso denegado). " +
          "Habilitá el permiso del sitio y reintentá, o usá la caja de texto.",
        "sys"
      );
      setEstado(Estado.INACTIVO);
      return;
    }

    // Intentamos capturar a 16 kHz (lo que espera Vosk). Si el navegador no
    // respeta la tasa pedida, usamos la real y la escribimos en el header WAV.
    const Ctx = window.AudioContext || window.webkitAudioContext;
    audioCtx = new Ctx({ sampleRate: STT_SAMPLE_RATE });
    try {
      await audioCtx.resume();
    } catch (_e) {
      /* algunos navegadores ya lo entregan activo */
    }

    pcmChunks = [];
    sourceNode = audioCtx.createMediaStreamSource(mediaStream);
    procNode = audioCtx.createScriptProcessor(4096, 1, 1);
    procNode.onaudioprocess = (e) => {
      // Copiamos el canal mono (Float32 en [-1, 1]); no escribimos salida → sin eco.
      pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    sourceNode.connect(procNode);
    procNode.connect(audioCtx.destination); // requerido para que dispare el callback.

    grabando = true;
    $micBtn.classList.add("activo");
    $micBtn.setAttribute("aria-pressed", "true");
    setEstado(Estado.ESCUCHANDO);
  }

  async function detenerGrabacionLocal() {
    grabando = false;
    $micBtn.classList.remove("activo");
    $micBtn.setAttribute("aria-pressed", "false");

    // Cerramos el grafo de audio y liberamos el micrófono.
    if (procNode) {
      procNode.disconnect();
      procNode.onaudioprocess = null;
    }
    if (sourceNode) sourceNode.disconnect();
    if (mediaStream) mediaStream.getTracks().forEach((t) => t.stop());
    const sampleRate = audioCtx ? audioCtx.sampleRate : STT_SAMPLE_RATE;
    if (audioCtx) {
      try {
        await audioCtx.close();
      } catch (_e) {
        /* ya cerrado */
      }
    }
    procNode = sourceNode = mediaStream = audioCtx = null;

    const wav = _codificarWav(pcmChunks, sampleRate);
    pcmChunks = [];
    if (!wav) {
      setEstado(Estado.INACTIVO);
      return;
    }

    setEstado(Estado.TRANSCRIBIENDO);
    let texto = "";
    try {
      const resp = await fetch("/transcribir", {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: wav,
      });
      const data = await resp.json().catch(() => ({}));
      if (!resp.ok || data.error) {
        agregarMensaje(
          data.message ||
            "El reconocimiento de voz local no está disponible. Usá la caja de texto.",
          "sys"
        );
        setEstado(Estado.INACTIVO);
        return;
      }
      texto = (data.texto || "").trim();
    } catch (_e) {
      agregarMensaje(
        "No se pudo contactar el servicio de transcripción. Usá la caja de texto.",
        "sys"
      );
      setEstado(Estado.INACTIVO);
      return;
    }

    if (!texto) {
      agregarMensaje(
        "No se entendió el audio. Probá de nuevo o escribí tu consulta.",
        "sys"
      );
      setEstado(Estado.INACTIVO);
      return;
    }
    procesarConsulta(texto); // mismo camino que el texto escrito.
  }

  /** Codifica PCM Float32 mono → Blob WAV PCM 16-bit. */
  function _codificarWav(chunks, sampleRate) {
    let largo = 0;
    for (const c of chunks) largo += c.length;
    if (largo === 0) return null;

    const pcm = new Float32Array(largo);
    let off = 0;
    for (const c of chunks) {
      pcm.set(c, off);
      off += c.length;
    }

    const buffer = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(buffer);
    const escribirStr = (pos, s) => {
      for (let i = 0; i < s.length; i++) view.setUint8(pos + i, s.charCodeAt(i));
    };
    escribirStr(0, "RIFF");
    view.setUint32(4, 36 + pcm.length * 2, true);
    escribirStr(8, "WAVE");
    escribirStr(12, "fmt ");
    view.setUint32(16, 16, true); // tamaño del subchunk fmt
    view.setUint16(20, 1, true); // formato PCM
    view.setUint16(22, 1, true); // canales: mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true); // byte rate (mono, 16-bit)
    view.setUint16(32, 2, true); // block align
    view.setUint16(34, 16, true); // bits por muestra
    escribirStr(36, "data");
    view.setUint32(40, pcm.length * 2, true);

    let pos = 44;
    for (let i = 0; i < pcm.length; i++) {
      const s = Math.max(-1, Math.min(1, pcm[i]));
      view.setInt16(pos, s < 0 ? s * 0x8000 : s * 0x7fff, true);
      pos += 2;
    }
    return new Blob([view], { type: "audio/wav" });
  }

  /** Enruta el botón de micrófono: STT local (Vosk) o Web Speech del navegador. */
  function manejarMicrofono() {
    if (usarServidorSTT) {
      if (grabando) detenerGrabacionLocal();
      else iniciarGrabacionLocal();
      return;
    }
    alternarEscucha();
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
    }
    if (SpeechRecognition || (usarServidorSTT && mediaDevicesDisponible)) {
      // El mismo botón sirve para Web Speech y para el STT local (Vosk).
      $micBtn.addEventListener("click", manejarMicrofono);
    } else {
      // CA-05.3: sin Web Speech y sin captura de audio → solo texto.
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
