/**
 * Respuestas simuladas para el prototipo de voz (RF-05).
 *
 * Este archivo SOLO existe para que el módulo de voz funcione hoy sin backend.
 * Devuelve objetos con el MISMO shape que emite engine.py:
 *     { found: boolean, message: string, animate_avatar: boolean }
 *
 * Cuando se conecte el motor real, este archivo deja de usarse: la integración
 * se hace en el cuerpo de obtenerRespuesta() (ver voice.js → PUNTO DE CONEXIÓN).
 */

// Normalización mínima SOLO para que el matcher del mock encuentre coincidencias
// pese a tildes/mayúsculas. NO es interpretación real: la interpretación vive en
// el motor (engine.py). Acá es solo utilería de demostración.
function _normalizarParaMock(texto) {
  return texto
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // quita tildes
    .replace(/\s+/g, " ")
    .trim();
}

// Conjunto acotado de respuestas de demo (4-6), alineadas con la base real.
// Cada entrada matchea por palabras clave presentes en la consulta normalizada.
const _RESPUESTAS_DEMO = [
  {
    claves: ["plan", "materias", "estudio"],
    message:
      "Plan de estudios completo de Tecnicatura Universitaria en Desarrollo de Software. " +
      "Duración: 3 años. Primer año: Matemática Discreta y Diseño Lógico, Álgebra y " +
      "Geometría Analítica, Inglés Técnico, Informática, Análisis de Sistemas I.",
    animate_avatar: true,
  },
  {
    claves: ["sede", "donde", "ubicacion", "lugar"],
    message:
      "La Tecnicatura se dicta en la Sede Río Cuarto de la Universidad de Mendoza.",
    animate_avatar: true,
  },
  {
    claves: ["modalidad", "presencial", "virtual", "horario"],
    message:
      "La modalidad es presencial, de lunes a viernes de 18:00 a 22:00 hs. " +
      "No está pensada como cursado 100% virtual.",
    animate_avatar: true,
  },
  {
    claves: ["titulo", "egresado", "recibo"],
    message:
      "El título otorgado es Tecnicatura Universitaria en Desarrollo de Software.",
    animate_avatar: true,
  },
  {
    claves: ["trabajo", "laboral", "salida", "empleo"],
    message:
      "Un egresado puede trabajar como desarrollador backend/frontend, " +
      "programador Full Stack, Tester QA, analista junior, soporte técnico o " +
      "desarrollo mobile.",
    animate_avatar: true,
  },
];

// Mensaje de no encontrado (equivalente a CU-01 E1 del motor real).
const _MENSAJE_NO_ENCONTRADO =
  "No encontré la información pedida. ¿Podés reformular la consulta?";

/**
 * Busca una respuesta simulada para el texto dado.
 * @param {string} textoConsulta
 * @returns {{found: boolean, message: string, animate_avatar: boolean}}
 */
function buscarRespuestaSimulada(textoConsulta) {
  const normalizado = _normalizarParaMock(textoConsulta || "");
  if (!normalizado) {
    return { found: false, message: _MENSAJE_NO_ENCONTRADO, animate_avatar: false };
  }

  for (const item of _RESPUESTAS_DEMO) {
    if (item.claves.some((clave) => normalizado.includes(clave))) {
      return {
        found: true,
        message: item.message,
        animate_avatar: item.animate_avatar,
      };
    }
  }

  // Caso found: false (requerido por el prompt para demostrar el flujo de fallo).
  return { found: false, message: _MENSAJE_NO_ENCONTRADO, animate_avatar: false };
}

// Exposición global simple (sin bundler).
window.MendobotMock = { buscarRespuestaSimulada };
