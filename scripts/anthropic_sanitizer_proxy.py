#!/usr/bin/env python3
"""Small diagnostic Anthropic API sanitizer proxy.

Phase 3 diagnostic flow:

  Claude Code -> sanitizer on :4010 -> LiteLLM on :4000 -> provider

For router-anthropic-haiku only, this strips top-level fields that the Haiku
backend currently rejects on the Anthropic /v1/messages path.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit

DEFAULT_STRIP_KEYS = ("output_config", "thinking", "reasoning_effort", "effort")


def csv_env(name: str, default: str) -> set[str]:
    raw = os.environ.get(name, default)
    return {item.strip() for item in raw.split(",") if item.strip()}


SANITIZE_MODELS = csv_env("SANITIZER_MODELS", "router-anthropic-haiku")
STRIP_KEYS = tuple(csv_env("SANITIZER_STRIP_KEYS", ",".join(DEFAULT_STRIP_KEYS)))
UPSTREAM = os.environ.get("SANITIZER_UPSTREAM", "http://127.0.0.1:4000").rstrip("/")
HOST = os.environ.get("SANITIZER_HOST", "0.0.0.0")
PORT = int(os.environ.get("SANITIZER_PORT", "4010"))
TIMEOUT = float(os.environ.get("SANITIZER_TIMEOUT_SECONDS", "900"))

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "host",
    "content-length",
}


def sanitize_payload(
    payload: dict[str, Any],
    sanitize_models: set[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Return a sanitized copy of the payload and the stripped key list."""
    models = sanitize_models or SANITIZE_MODELS
    clean = dict(payload)
    stripped: list[str] = []

    model = str(clean.get("model", ""))
    if model in models:
        for key in STRIP_KEYS:
            if key in clean:
                stripped.append(key)
                clean.pop(key, None)

    return clean, stripped


def log(message: str) -> None:
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%S%z')} {message}", flush=True)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_HEAD(self) -> None:
        self.forward()

    def do_GET(self) -> None:
        self.forward()

    def do_POST(self) -> None:
        self.forward()

    def do_OPTIONS(self) -> None:
        self.forward()

    def log_message(self, fmt: str, *args: Any) -> None:
        log(f"{self.client_address[0]} {fmt % args}")

    def forward(self) -> None:
        length = int(self.headers.get("Content-Length") or "0")
        in_body = self.rfile.read(length) if length else b""
        out_body = in_body

        model = ""
        top_keys: list[str] = []
        stripped: list[str] = []

        content_type = self.headers.get("Content-Type", "")
        if self.command in {"POST", "PUT", "PATCH"} and in_body and "application/json" in content_type:
            try:
                payload = json.loads(in_body.decode("utf-8"))
                if isinstance(payload, dict):
                    model = str(payload.get("model", ""))
                    top_keys = sorted(payload.keys())
                    clean, stripped = sanitize_payload(payload)
                    if stripped:
                        out_body = json.dumps(
                            clean,
                            separators=(",", ":"),
                            ensure_ascii=False,
                        ).encode("utf-8")
            except Exception as exc:
                log(f"JSON_PARSE_ERROR path={self.path} error={type(exc).__name__}: {exc}")

        if model or stripped:
            log(
                "REQUEST "
                f"method={self.command} path={self.path} model={model or '-'} "
                f"top_keys={','.join(top_keys) if top_keys else '-'} "
                f"stripped={','.join(stripped) if stripped else '-'}"
            )

        target = f"{UPSTREAM}{self.path}"
        headers: dict[str, str] = {}

        for key, value in self.headers.items():
            if key.lower() not in HOP_BY_HOP_HEADERS:
                headers[key] = value

        headers["Host"] = urlsplit(UPSTREAM).netloc
        headers["Accept-Encoding"] = "identity"

        if self.command in {"POST", "PUT", "PATCH"}:
            headers["Content-Length"] = str(len(out_body))
            data = out_body
        else:
            data = None

        req = urllib.request.Request(target, data=data, headers=headers, method=self.command)

        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                resp_body = b"" if self.command == "HEAD" else resp.read()
                self.send_response(resp.status)
                self.copy_response_headers(resp.headers, len(resp_body))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(resp_body)

        except urllib.error.HTTPError as exc:
            err_body = b"" if self.command == "HEAD" else exc.read()
            log(f"UPSTREAM_HTTP_ERROR status={exc.code} path={self.path} body={err_body[:500]!r}")
            self.send_response(exc.code)
            self.copy_response_headers(exc.headers, len(err_body))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(err_body)

        except Exception as exc:
            msg = f"sanitizer upstream error: {type(exc).__name__}: {exc}"
            log(f"UPSTREAM_ERROR path={self.path} {msg}")
            body = json.dumps(
                {"error": {"message": msg, "type": "sanitizer_upstream_error"}}
            ).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

    def copy_response_headers(self, headers: Any, body_len: int) -> None:
        for key, value in headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP_HEADERS or lower in {"content-length", "content-encoding"}:
                continue
            self.send_header(key, value)

        self.send_header("Content-Length", str(body_len))
        self.send_header("Connection", "close")


def main() -> int:
    log(f"Starting Anthropic sanitizer proxy host={HOST} port={PORT} upstream={UPSTREAM}")
    log(f"sanitize_models={','.join(sorted(SANITIZE_MODELS))}")
    log(f"strip_keys={','.join(STRIP_KEYS)}")

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log("Stopping Anthropic sanitizer proxy")
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
