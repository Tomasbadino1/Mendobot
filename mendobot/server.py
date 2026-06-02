"""Servidor HTTP local de MendoBot — puente entre el frontend de voz y el motor.

Reutiliza el motor existente (`src/engine.py`, `src/data_manager.py`) SIN
modificarlo: lo importa igual que `main.py` y lo expone por HTTP.

Rutas:
    GET  /                -> frontend de voz (voice/index.html)
    GET  /<archivo>       -> estáticos de voice/ (voice.js, etc.)
    POST /consulta        -> {"texto": "..."} -> {found, message, animate_avatar}
    POST /transcribir     -> audio WAV (16 kHz mono 16-bit) -> {"texto": "..."}

El frontend y la API se sirven desde el MISMO origen, así el fetch no necesita
CORS. La transcripción usa Vosk OFFLINE (no depende de servidores de Google ni
de internet), resolviendo el fallo `network` del Web Speech API.

Uso:
    cd mendobot
    python server.py            # escucha en http://localhost:8000
"""

from __future__ import annotations

import io
import json
import threading
import wave
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.data_manager import DataManager
from src.engine import MendoBotEngine

# --- Configuración ---
BASE_DIR = Path(__file__).parent
VOICE_DIR = BASE_DIR / "voice"
DATA_PATH = BASE_DIR / "data" / "knowledge_base.json"
MODEL_DIR = VOICE_DIR / "models" / "vosk-model-small-es-0.42"
STT_SAMPLE_RATE = 16000  # el frontend captura PCM mono a 16 kHz
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # tope defensivo (~5 min de audio 16 kHz)
HOST = "127.0.0.1"
PORT = 8000

# Mensaje de servicio no disponible (CU-02 E1 / CA-08.3): no inventar datos.
_MENSAJE_SERVICIO = (
    "El servicio local no puede recuperar la información en este momento. "
    "Intentá nuevamente más tarde."
)

# Tipos MIME mínimos para los estáticos del módulo de voz.
_MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
}


# --- Motor compartido (se construye una sola vez, igual que en main.py) ---
# RNF-01: el índice TF-IDF se precalcula al iniciar, no por consulta.
_engine: MendoBotEngine | None = None
_engine_lock = threading.Lock()  # serializa el acceso al contexto conversacional

# --- Motor de transcripción offline (Vosk), cargado una sola vez al iniciar ---
_stt_model = None  # type: ignore[var-annotated]
_stt_lock = threading.Lock()


def _init_engine() -> None:
    """Inicializa el motor. Si la base falta o está corrupta, queda en None
    y /consulta responderá con el flujo de excepción CU-02 E1."""
    global _engine
    try:
        data_manager = DataManager(DATA_PATH)
        _engine = MendoBotEngine(data_manager)
        print(f"[MendoBot] Motor inicializado desde {DATA_PATH.name}.")
    except Exception as exc:  # JSON corrupto, archivo ilegible, etc.
        _engine = None
        print(f"[MendoBot] ERROR al inicializar el motor: {exc}")


def _init_stt() -> None:
    """Carga el modelo Vosk en español (offline). Si falta el modelo o la lib,
    queda en None y /transcribir responde un error claro sin romper el texto."""
    global _stt_model
    try:
        from vosk import Model  # import diferido: STT es opcional

        if not MODEL_DIR.is_dir():
            print(f"[MendoBot] Modelo Vosk no encontrado en {MODEL_DIR}. STT desactivado.")
            return
        _stt_model = Model(str(MODEL_DIR))
        print(f"[MendoBot] STT (Vosk) inicializado desde {MODEL_DIR.name}.")
    except Exception as exc:  # vosk no instalado, modelo corrupto, etc.
        _stt_model = None
        print(f"[MendoBot] STT no disponible: {exc}")


def _transcribir_wav(audio_bytes: bytes) -> str:
    """Transcribe un WAV (16 kHz, mono, 16-bit PCM) a texto con Vosk."""
    from vosk import KaldiRecognizer

    with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
            raise ValueError("El audio debe ser WAV mono de 16 bits.")
        sample_rate = wf.getframerate()
        with _stt_lock:  # Vosk Recognizer no es thread-safe; serializamos
            recognizer = KaldiRecognizer(_stt_model, sample_rate)
            recognizer.SetWords(False)
            while True:
                frames = wf.readframes(4000)
                if not frames:
                    break
                recognizer.AcceptWaveform(frames)
            resultado = json.loads(recognizer.FinalResult())
    return str(resultado.get("text", "")).strip()


class MendoBotHandler(BaseHTTPRequestHandler):
    """Sirve el frontend de voz y expone el motor en POST /consulta."""

    server_version = "MendoBot/1.0"

    # --- Utilidades de respuesta ---
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_static(self, rel_path: str) -> None:
        # Normaliza "/" -> index.html y previene path traversal fuera de voice/.
        if rel_path in ("", "/"):
            rel_path = "index.html"
        rel_path = rel_path.lstrip("/")
        target = (VOICE_DIR / rel_path).resolve()
        try:
            target.relative_to(VOICE_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN, "Ruta no permitida")
            return
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Recurso no encontrado")
            return

        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", _MIME.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # --- Rutas ---
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/favicon.ico":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        self._send_static(path)

    def do_POST(self) -> None:
        path = self.path.split("?", 1)[0]
        if path == "/transcribir":
            self._handle_transcribir()
            return
        if path != "/consulta":
            self.send_error(HTTPStatus.NOT_FOUND, "Endpoint no encontrado")
            return

        # Lee y parsea el cuerpo JSON {"texto": "..."}.
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b""
            data = json.loads(raw.decode("utf-8")) if raw else {}
            texto = str(data.get("texto", "")).strip()
        except (ValueError, json.JSONDecodeError):
            self._send_json(
                {"found": False, "message": "Solicitud inválida.", "animate_avatar": False},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        # CU-02 E1: motor no disponible (base ausente/corrupta).
        if _engine is None:
            self._send_json(
                {"found": False, "message": _MENSAJE_SERVICIO, "animate_avatar": False}
            )
            return

        # Interpretación delegada al motor existente (sin reimplementar NLP).
        with _engine_lock:
            respuesta = _engine.buscar_respuesta(texto)

        # El shape ya es {found, message, animate_avatar} — idéntico al contrato.
        self._send_json(
            {
                "found": bool(respuesta.get("found", False)),
                "message": str(respuesta.get("message", "")),
                "animate_avatar": bool(respuesta.get("animate_avatar", False)),
            }
        )

    def _handle_transcribir(self) -> None:
        """STT offline: recibe audio WAV y devuelve {"texto": "..."}."""
        # STT no disponible (vosk/modelo ausente): el frontend cae al texto.
        if _stt_model is None:
            self._send_json(
                {
                    "texto": "",
                    "error": "stt_no_disponible",
                    "message": "El reconocimiento de voz local no está disponible.",
                },
                status=HTTPStatus.SERVICE_UNAVAILABLE,
            )
            return

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_AUDIO_BYTES:
            self._send_json(
                {"texto": "", "error": "audio_invalido", "message": "Audio ausente o demasiado grande."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        audio_bytes = self.rfile.read(length)
        try:
            texto = _transcribir_wav(audio_bytes)
        except Exception as exc:  # WAV inválido, formato incorrecto, etc.
            self._send_json(
                {"texto": "", "error": "transcripcion_fallida", "message": str(exc)},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        self._send_json({"texto": texto})

    def log_message(self, fmt: str, *args) -> None:
        # Log compacto en consola (CA-08.1: visibilidad del servicio activo).
        print(f"[MendoBot] {self.address_string()} - {fmt % args}")


def main() -> None:
    _init_engine()
    _init_stt()
    httpd = ThreadingHTTPServer((HOST, PORT), MendoBotHandler)
    url = f"http://{HOST}:{PORT}/"
    print(f"[MendoBot] Servidor activo en {url}  (Ctrl+C para detener)")
    print(f"[MendoBot] Frontend de voz: {url}index.html")
    print(f"[MendoBot] API: POST {url}consulta  |  STT: POST {url}transcribir")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[MendoBot] Servidor detenido.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
