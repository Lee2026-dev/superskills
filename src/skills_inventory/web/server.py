"""ThreadingHTTPServer + request router for the dashboard."""
from __future__ import annotations

import importlib.resources
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlparse

from . import api as _api

# MIME types for static assets
_MIME = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
}


def _read_asset(filename: str) -> bytes:
    """Read a file from web/assets/ using importlib.resources."""
    pkg = importlib.resources.files("skills_inventory.web.assets")
    return (pkg / filename).read_bytes()


def _make_handler(scan_root_paths: list[Path], initial_refresh: bool = False) -> type[BaseHTTPRequestHandler]:
    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            # Suppress default request logging; dashboard keeps its own log.
            pass

        # ── helpers ──

        def _send(self, body: bytes, status: int = 200, content_type: str = "application/json") -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_api(self, body: bytes, status: int) -> None:
            self._send(body, status, "application/json")

        def _read_body(self) -> dict:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}

        def _query(self) -> dict[str, str]:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            return {k: v[0] for k, v in qs.items()}

        def _path_only(self) -> str:
            return urlparse(self.path).path

        # ── GET ──

        def do_GET(self) -> None:
            path = self._path_only()

            if path in ("/", "/index.html"):
                body = _read_asset("index.html")
                self._send(body, 200, "text/html; charset=utf-8")

            elif path.startswith("/assets/"):
                filename = path.removeprefix("/assets/")
                suffix = Path(filename).suffix
                mime = _MIME.get(suffix, "application/octet-stream")
                try:
                    body = _read_asset(filename)
                    self._send(body, 200, mime)
                except FileNotFoundError:
                    self._send_api(*_api.err(f"asset not found: {filename}", "NOT_FOUND"))

            elif path == "/api/scan":
                q = self._query()
                refresh = initial_refresh or q.get("refresh") == "true"
                fast_mode = q.get("fast") == "true"
                body, status = _api.handle_scan(scan_root_paths, refresh=refresh, fast_mode=fast_mode)
                self._send_api(body, status)

            elif path == "/api/versions":
                q = self._query()
                name = q.get("name", "")
                skill_path = q.get("path") or None
                if not name:
                    self._send_api(*_api.err("'name' query param is required", "BAD_REQUEST"))
                else:
                    body, status = _api.handle_versions(name, skill_path, scan_root_paths)
                    self._send_api(body, status)

            elif path == "/api/log":
                log = _api.get_log()
                self._send_api(_api.ok(log), 200)

            else:
                self._send_api(*_api.err(f"not found: {path}", "NOT_FOUND"))

        # ── POST ──

        def do_POST(self) -> None:
            path = self._path_only()
            body_dict = self._read_body()

            if path == "/api/upgrade":
                body, status = _api.handle_upgrade(body_dict, scan_root_paths)
                self._send_api(body, status)

            elif path == "/api/conflict/resolve":
                body, status = _api.handle_resolve(body_dict, scan_root_paths)
                self._send_api(body, status)

            else:
                self._send_api(*_api.err(f"not found: {path}", "NOT_FOUND"))

        # ── OPTIONS (CORS preflight) ──

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

    return _Handler


def serve(
    scan_root_paths: list[Path],
    host: str = "127.0.0.1",
    port: int = 8080,
    refresh: bool = False,
) -> ThreadingHTTPServer:
    """Create and return a ready-to-run ThreadingHTTPServer."""
    handler = _make_handler(scan_root_paths, refresh)
    server = ThreadingHTTPServer((host, port), handler)
    return server
