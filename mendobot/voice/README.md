# MendoBot — Módulo de Voz (RF-05)

Prototipo **autónomo** de interacción por voz: escucha (STT), respuesta hablada
(TTS) e interpretación delegada. Funciona en el navegador **sin backend**, usando
respuestas simuladas.

Cubre los criterios de aceptación del RF-05:

- **CA-05.1 (Escucha):** el micrófono transcribe la voz a texto y la envía por el
  mismo camino que una consulta escrita.
- **CA-05.2 (Voz):** las respuestas válidas (`found: true`) se muestran en
  pantalla y se reproducen con síntesis de voz.
- **CA-05.3 (Fallback):** si el navegador no soporta reconocimiento de voz o se
  deniega el permiso de micrófono, se informa al usuario y la consulta por texto
  sigue disponible (nunca se bloquea la interfaz).

## Cómo ejecutarlo

El reconocimiento de voz requiere un **origen seguro** (`https://` o
`http://localhost`). No alcanza con abrir el archivo con doble clic (`file://`):
el micrófono quedará bloqueado por el navegador.

Levantá un servidor estático simple desde esta carpeta:

```bash
cd mendobot/voice
python -m http.server 5500
```

Luego abrí: <http://localhost:5500>

> Nota: este servidor estático es solo para servir el prototipo de voz. No tiene
> relación con `main.py` ni con el motor; es independiente.

## Modelo Vosk (STT offline)

El reconocimiento de voz del servidor (`server.py`, `POST /transcribir`) usa
**Vosk** de forma **offline**, sin depender de servicios externos. El modelo en
español **no se versiona en el repositorio** (pesa ~58 MB): hay que descargarlo
una vez.

1. Instalar la librería (ya incluida en `requirements.txt`):

   ```bash
   pip install vosk
   ```

2. Descargar el modelo pequeño en español desde la página oficial:
   <https://alphacephei.com/vosk/models> → **`vosk-model-small-es-0.42`**
   (enlace directo: <https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip>).

3. Descomprimir dentro de esta carpeta, de modo que quede la ruta exacta que
   espera `server.py` (`MODEL_DIR`):

   ```
   mendobot/voice/models/vosk-model-small-es-0.42/
   ```

> Si el modelo o la librería faltan, el servidor **no se rompe**: `/transcribir`
> responde `stt_no_disponible` y la consulta por texto sigue disponible (CA-05.3).

## Navegadores soportados

- ✅ **Chrome / Edge** (escritorio): soporte completo de STT + TTS.
- 🟡 **Safari**: TTS sí; STT parcial/variable.
- ❌ **Firefox**: sin `SpeechRecognition` → el módulo cae al modo texto
  automáticamente (CA-05.3).

## Archivos

| Archivo              | Rol                                                        |
| -------------------- | ---------------------------------------------------------- |
| `index.html`         | Interfaz: micrófono, caja de texto y área de conversación. |
| `voice.js`           | STT, TTS, estados de UI y el contrato `obtenerRespuesta()`. |
| `mock-respuestas.js` | Respuestas simuladas de demo (incluye un caso `found:false`). |

## PUNTO DE CONEXIÓN FUTURA

Toda la integración con el sistema real ocurre en **un único lugar**: el cuerpo
de la función `obtenerRespuesta(textoConsulta)` en `voice.js`
(bloque marcado `PUNTO DE CONEXIÓN FUTURA`).

Hoy:

```js
async function obtenerRespuesta(textoConsulta) {
  // --- MOCK (se elimina al conectar el backend) ---
  return window.MendobotMock.buscarRespuestaSimulada(textoConsulta);
}
```

Mañana (cuando exista el backend que expone `engine.buscar_respuesta()`):

```js
async function obtenerRespuesta(textoConsulta) {
  const resp = await fetch("/consulta", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ texto: textoConsulta }),
  });
  return await resp.json(); // { found, message, animate_avatar }
}
```

El resto del módulo **no cambia**: ya espera el shape
`{ found, message, animate_avatar }`, idéntico al que emite `engine.py`.
Cuando se conecte el backend, `mock-respuestas.js` puede eliminarse.

## Fuera de alcance (por diseño)

- No construye ni llama al backend/API real.
- No implementa el avatar 3D ni la rotación (RF-06 / RF-07). La bandera
  `animate_avatar` queda disponible y solo se loguea, lista para uso futuro.
- No modifica el motor ni la base de conocimiento.
