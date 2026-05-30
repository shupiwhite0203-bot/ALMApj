from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import socket
import struct
import threading
import time
import webbrowser
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from mh_assistant.live2d_assets import (
    DEFAULT_NURSE_ROBOT_LIVE2D_DIR,
    prepare_nurse_robot_assets,
)


ROOT = Path(__file__).resolve().parent
OVERLAY_DIR = ROOT / "mh_assistant" / "overlay"
EVENT_PATH = ROOT / "runs" / "live2d" / "latest_event.json"
MODEL_DIR = ROOT / "runs" / "live2d_model" / "nurse_robot_type_t"
OPEN_LLM_FRONTEND = Path(r"C:\Users\spieler\Open-LLM-VTuber\frontend")
LOCAL_CUBISM_CORE = ROOT / "vendor" / "live2d" / "live2dcubismcore.min.js"
WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class OverlayHandler(BaseHTTPRequestHandler):
    server_version = "ALMALive2DOverlay/0.1"

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path != "/api/client-log":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b"{}"
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {"raw": body.decode("utf-8", errors="replace")}

        level = payload.get("level", "log")
        message = payload.get("message", "")
        print(f"[client:{level}] {message}", flush=True)
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/client-ws":
            self._handle_websocket()
            return
        if path == "/" or path == "/olv" or path == "/olv/":
            self._send_file(OVERLAY_DIR / "openllm_live2d.html")
            return
        if path == "/preview" or path == "/preview/":
            self._send_file(OVERLAY_DIR / "index.html")
            return
        if path == "/api/event":
            self._send_event()
            return
        if path.startswith("/overlay/"):
            self._send_file(OVERLAY_DIR / path.removeprefix("/overlay/"))
            return
        if path.startswith("/live2d-model/"):
            self._send_file(_resolve_model_path(path.removeprefix("/live2d-model/")))
            return
        if path.startswith("/openllm-assets/"):
            self._send_file(OPEN_LLM_FRONTEND / "assets" / path.removeprefix("/openllm-assets/"))
            return
        if path.startswith("/libs/"):
            lib_name = path.removeprefix("/libs/")
            if lib_name == "live2dcubismcore.js" and LOCAL_CUBISM_CORE.exists():
                self._send_file(LOCAL_CUBISM_CORE)
                return
            self._send_file(OPEN_LLM_FRONTEND / "libs" / lib_name)
            return
        if path.startswith("/audio/"):
            self._send_audio_from_event(path.removeprefix("/audio/"))
            return

        self.send_error(404)

    def _handle_websocket(self) -> None:
        ws_key = self.headers.get("Sec-WebSocket-Key")
        if not ws_key:
            self.send_error(400, "Missing Sec-WebSocket-Key")
            return

        accept = base64.b64encode(hashlib.sha1((ws_key + WS_GUID).encode("ascii")).digest()).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()

        self.connection.settimeout(0.25)
        self._ws_send_json({"type": "full-text", "text": "ALMA Monster Hunter assistant connected."})
        self._ws_send_json(
            {
                "type": "set-model-and-conf",
                "model_info": self._model_info(),
                "conf_name": "ALMA Monster Hunter Assistant",
                "conf_uid": "alma-mh",
                "client_uid": "alma-local",
            }
        )
        self._ws_send_json({"type": "group-update", "members": [], "is_owner": True})

        connection_started_at = time.monotonic()
        initial_audio_delay = 3.0
        last_signature: tuple[float, int] | None = None
        while True:
            try:
                frame = self._ws_recv_frame()
            except TimeoutError:
                frame = None
            except (ConnectionError, OSError, socket.timeout):
                break

            if frame is not None:
                opcode, payload = frame
                if opcode == 8:
                    break
                if opcode == 9:
                    self._ws_send_frame(payload, opcode=10)
                elif opcode == 1:
                    self._handle_ws_text(payload.decode("utf-8", errors="replace"))

            signature = self._event_signature()
            if signature and signature != last_signature:
                if time.monotonic() - connection_started_at >= initial_audio_delay:
                    last_signature = signature
                    message = self._event_to_openllm_audio()
                    if message:
                        self._ws_send_json(message)

            time.sleep(0.05)

    def _handle_ws_text(self, text: str) -> None:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return

        message_type = payload.get("type")
        if message_type == "fetch-backgrounds":
            self._ws_send_json({"type": "background-files", "files": []})
        elif message_type == "fetch-configs":
            self._ws_send_json({"type": "config-files", "configs": []})
        elif message_type == "fetch-history-list":
            self._ws_send_json({"type": "history-list", "histories": []})
        elif message_type == "create-new-history":
            # Open-LLM's frontend clears the visible chat when it receives
            # new-history-created. ALMA drives the conversation from hunt
            # events, so keep the current advice visible instead.
            print("[overlay] ignored frontend create-new-history request", flush=True)
        elif message_type == "audio-play-start":
            print("[overlay] frontend playback started", flush=True)
        elif message_type == "frontend-playback-complete":
            print("[overlay] frontend playback completed", flush=True)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[overlay] {self.address_string()} - {fmt % args}", flush=True)

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_event(self) -> None:
        if not EVENT_PATH.exists():
            self._send_json({"type": "empty", "text": "", "audio_url": None})
            return

        try:
            payload = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            self._send_json({"type": "error", "message": str(exc)}, status=500)
            return

        if payload.get("audio_path"):
            payload["audio_url"] = f"/audio/{Path(payload['audio_path']).name}"
        else:
            payload["audio_url"] = None

        self._send_json(payload)

    def _send_audio_from_event(self, filename: str) -> None:
        if not EVENT_PATH.exists():
            self.send_error(404)
            return

        payload = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
        audio_path = payload.get("audio_path")
        if not audio_path:
            self.send_error(404)
            return

        candidate = Path(audio_path)
        if candidate.name != filename or not candidate.exists():
            self.send_error(404)
            return

        self._send_file(candidate)

    def _model_info(self) -> dict:
        host = self.headers.get("Host", "127.0.0.1:18080")
        return {
            "name": "nurse_robot_type_t",
            "url": f"http://{host}/live2d-model/nurse_robot_type_t/nurse_robot_type_t.model3.json",
            "kScale": 1.35,
            "initialXshift": 0,
            "initialYshift": 0.18,
            "pointerInteractive": True,
            "scrollToResize": True,
        }

    def _event_signature(self) -> tuple[float, int] | None:
        try:
            stat = EVENT_PATH.stat()
        except FileNotFoundError:
            return None
        return (stat.st_mtime, stat.st_size)

    def _event_to_openllm_audio(self) -> dict | None:
        try:
            payload = json.loads(EVENT_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"[overlay] failed to read event: {exc}")
            return None

        text = str(payload.get("text") or "")
        audio_path = Path(payload["audio_path"]) if payload.get("audio_path") else None
        audio_base64 = None
        volumes: list[float] = []
        slice_length = 20

        if audio_path and audio_path.exists():
            audio_bytes = audio_path.read_bytes()
            audio_base64 = base64.b64encode(audio_bytes).decode("ascii")
            volumes = _wav_volumes(audio_path, slice_ms=slice_length)

        return {
            "type": "audio",
            "audio": audio_base64,
            "volumes": volumes,
            "slice_length": slice_length,
            "display_text": {
                "text": text,
                "name": "ナースロボ＿タイプＴ",
                "avatar": "",
            },
            "actions": {"expressions": [payload.get("expression", "neutral")]},
            "forwarded": False,
            "metadata": payload.get("metadata", {}),
        }

    def _ws_recv_frame(self) -> tuple[int, bytes] | None:
        header = self._recv_exact(2)
        if not header:
            return None

        first, second = header
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]

        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _recv_exact(self, length: int) -> bytes:
        data = bytearray()
        while len(data) < length:
            try:
                chunk = self.connection.recv(length - len(data))
            except socket.timeout as exc:
                if not data:
                    raise TimeoutError from exc
                raise ConnectionError from exc
            if not chunk:
                raise ConnectionError
            data.extend(chunk)
        return bytes(data)

    def _ws_send_json(self, payload: dict) -> None:
        self._ws_send_frame(json.dumps(payload, ensure_ascii=False).encode("utf-8"), opcode=1)

    def _ws_send_frame(self, payload: bytes, opcode: int = 1) -> None:
        length = len(payload)
        header = bytearray([0x80 | opcode])
        if length < 126:
            header.append(length)
        elif length < 65536:
            header.extend((126, *struct.pack("!H", length)))
        else:
            header.extend((127, *struct.pack("!Q", length)))
        self.connection.sendall(bytes(header) + payload)

    def _send_file(self, path: Path) -> None:
        resolved = path.resolve()
        if not resolved.exists() or not resolved.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        data = resolved.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def _wav_volumes(path: Path, slice_ms: int = 20) -> list[float]:
    try:
        with wave.open(str(path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            frame_rate = wav_file.getframerate()
            frames_per_slice = max(1, int(frame_rate * slice_ms / 1000))
            volumes: list[float] = []

            while True:
                chunk = wav_file.readframes(frames_per_slice)
                if not chunk:
                    break
                volumes.append(_pcm_rms(chunk, sample_width, channels))
            return volumes
    except Exception as exc:
        print(f"[overlay] failed to calculate wav volumes: {exc}")
        return []


def _pcm_rms(chunk: bytes, sample_width: int, channels: int) -> float:
    if sample_width != 2 or not chunk:
        return 0.0

    sample_count = len(chunk) // 2
    if sample_count == 0:
        return 0.0

    values = struct.unpack("<" + "h" * sample_count, chunk)
    if channels > 1:
        values = values[::channels]
    square_sum = sum(value * value for value in values)
    rms = (square_sum / max(1, len(values))) ** 0.5
    return min(1.0, rms / 32768.0)


def _resolve_model_path(relative_url_path: str) -> Path:
    relative_path = Path(relative_url_path)
    parts = relative_path.parts
    if parts and parts[0] == "nurse_robot_type_t":
        relative_path = Path(*parts[1:])
    return MODEL_DIR / relative_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the ALMA Live2D overlay server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18080)
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--model-source", type=Path, default=DEFAULT_NURSE_ROBOT_LIVE2D_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    bundle = prepare_nurse_robot_assets(source_dir=args.model_source, output_dir=MODEL_DIR)
    print(f"prepared Live2D model: {bundle.model_json}")

    server = ThreadingHTTPServer((args.host, args.port), OverlayHandler)
    url = f"http://{args.host}:{args.port}/"
    print(f"overlay: {url}")

    if not args.no_open:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("overlay stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
