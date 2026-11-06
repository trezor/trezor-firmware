#!/usr/bin/env python3
"""Development WARD Manager REST service for the encrypted WARD protocol.

Run with ``uv run python tools/ward_manager.py --debug-key``. Only opaque WARD
checkpoints reach this service; plaintext entries and device keys stay with their
owners. The debug signing key is accepted only by debug firmware.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sqlite3
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from trezorlib.ward_protocol import (
    EMPTY_ROOT,
    attestation_message,
    genesis_nonce,
    transition_message,
)

DEBUG_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."
DEFAULT_PORT = 21330
MAX_BODY_BYTES = 4096
MAX_COUNTER = 0xFFFFFFFF
ZERO_MAC = bytes(32)


class ApiError(Exception):
    def __init__(self, status: int, message: str, **details: Any) -> None:
        super().__init__(message)
        self.status = status
        self.body = {"error": message, **details}


def _hex32(value: Any, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        raise ApiError(400, f"{field} must be 32 bytes encoded as hex")
    return value.lower()


def _counter(value: Any) -> int:
    if type(value) is not int or not 0 <= value <= MAX_COUNTER:
        raise ApiError(400, "counter must be an unsigned 32-bit integer")
    return value


def _mac(value: Any) -> str | None:
    if value is None:
        return None
    result = _hex32(value, "mac")
    return None if result == ZERO_MAC.hex() else result


@dataclass(frozen=True)
class Head:
    counter: int = 0
    mac: str | None = None
    root: str = ""
    head_nonce: str = ""
    timestamp: int = 0

    def body(self) -> dict[str, Any]:
        return {
            "counter": self.counter,
            "root": self.root,
            "headNonce": self.head_nonce,
            "timestamp": self.timestamp,
            **({"mac": self.mac} if self.mac else {}),
        }


class WardManager:
    """A persistent per-ward checkpoint register and the WM signing key."""

    def __init__(self, database: str | Path, seed: bytes) -> None:
        self.key = Ed25519PrivateKey.from_private_bytes(seed)
        self.public_key = self.key.public_key().public_bytes_raw().hex()
        self.lock = threading.Lock()
        self.db = sqlite3.connect(str(database), check_same_thread=False, timeout=10)
        try:
            with self.db:
                self.db.execute(
                    "CREATE TABLE IF NOT EXISTS metadata (name TEXT PRIMARY KEY, value TEXT NOT NULL)"
                )
                self.db.execute(
                    "CREATE TABLE IF NOT EXISTS heads "
                    "(ward_id TEXT PRIMARY KEY, counter INTEGER NOT NULL, mac TEXT, root TEXT NOT NULL, "
                    "head_nonce TEXT NOT NULL, timestamp INTEGER NOT NULL)"
                )
                columns = {
                    row[1] for row in self.db.execute("PRAGMA table_info(heads)")
                }
                if not {"root", "head_nonce", "timestamp"} <= columns:
                    raise ValueError(
                        "Unsigned legacy WARD database: explicit migration is required"
                    )
                self.db.execute(
                    "CREATE TABLE IF NOT EXISTS transitions "
                    "(ward_id TEXT NOT NULL, counter INTEGER NOT NULL, body TEXT NOT NULL, "
                    "PRIMARY KEY (ward_id, counter))"
                )
                self.db.execute(
                    "INSERT OR IGNORE INTO metadata VALUES ('public_key', ?)",
                    (self.public_key,),
                )
                stored_key = self.db.execute(
                    "SELECT value FROM metadata WHERE name = 'public_key'"
                ).fetchone()[0]
                if stored_key != self.public_key:
                    raise ValueError("Database belongs to a different WM signing key")
        except Exception:
            self.db.close()
            raise

    def close(self) -> None:
        self.db.close()

    def _head(self, ward_id: str) -> Head:
        row = self.db.execute(
            "SELECT counter, mac, root, head_nonce, timestamp FROM heads WHERE ward_id = ?",
            (ward_id,),
        ).fetchone()
        return Head(*row) if row else Head(head_nonce=genesis_nonce(ward_id))

    def head(self, ward_id: str) -> dict[str, Any]:
        ward_id = _hex32(ward_id, "wardId")
        with self.lock:
            return {"wardId": ward_id, **self._head(ward_id).body()}

    def attest(self, request: dict[str, Any]) -> dict[str, Any]:
        ward_id = _hex32(request.get("wardId"), "wardId")
        nonce = _hex32(request.get("nonce"), "nonce")
        expected = None
        if "counter" in request:
            expected = Head(_counter(request["counter"]), _mac(request.get("mac")))
        elif "mac" in request:
            raise ApiError(400, "mac requires counter")

        with self.lock:
            head = self._head(ward_id)
            if expected is not None and (
                expected.counter != head.counter or expected.mac != head.mac
            ):
                raise ApiError(409, "checkpoint_conflict", **head.body())
            timestamp = max(int(time.time()), head.timestamp)
            message = attestation_message(
                ward_id, nonce, head.counter, head.mac, timestamp, head.head_nonce
            )
            return {
                **head.body(),
                "timestamp": timestamp,
                "signature": self.key.sign(message).hex(),
            }

    def commit(self, request: dict[str, Any]) -> dict[str, Any]:
        # ACCEPTED (trust model): the WM accepts a root without evidence that its leaves
        # are available. A host that withholds them after the commit freezes the wallet
        # for every device; the user-confirmed WARDPerformRevert is the way out.
        ward_id = _hex32(request.get("wardId"), "wardId")
        counter = _counter(request.get("counter"))
        from_counter = _counter(request.get("fromCounter"))

        def root(value: Any) -> str:
            if value == "":
                return ""
            result = _hex32(value, "root")
            return "" if result == EMPTY_ROOT.hex() else result

        to_root, from_root = root(request.get("root")), root(request.get("fromRoot"))
        mac = _mac(request.get("mac"))
        if mac is None or counter != from_counter + 1:
            raise ApiError(
                400, "A successor transition and nonzero wallet MAC are required"
            )
        kind = request.get("kind", "commit")
        if kind not in ("commit", "revert"):
            raise ApiError(400, "Invalid transition kind")
        auth_commit = _hex32(request.get("authCommit"), "authCommit")
        head_nonce = _hex32(request.get("headNonce"), "headNonce")
        signature = request.get("signature")
        if (
            not isinstance(signature, str)
            or re.fullmatch(r"[0-9a-fA-F]{128}", signature) is None
        ):
            raise ApiError(400, "A wallet transition signature is required")
        record = {
            "wardId": ward_id,
            "fromCounter": from_counter,
            "fromRoot": from_root,
            "counter": counter,
            "root": to_root,
            "mac": mac,
            "authCommit": auth_commit,
            "signature": signature.lower(),
            "kind": kind,
            "headNonce": head_nonce,
        }
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(ward_id)).verify(
                bytes.fromhex(signature), transition_message(record)
            )
        except (ValueError, InvalidSignature):
            raise ApiError(403, "Invalid wallet transition signature") from None
        body = json.dumps(record, sort_keys=True, separators=(",", ":"))
        with self.lock, self.db:
            # SQLite serializes this CAS across threads and manager processes.
            self.db.execute("BEGIN IMMEDIATE")
            head = self._head(ward_id)
            previous = self.db.execute(
                "SELECT body FROM transitions WHERE ward_id = ? AND counter = ?",
                (ward_id, counter),
            ).fetchone()
            retry = (
                previous is not None
                and previous[0] == body
                and (counter, mac, to_root) == (head.counter, head.mac, head.root)
            )
            if not retry and (
                from_counter != head.counter
                or from_root != head.root
                or head_nonce != head.head_nonce
            ):
                raise ApiError(409, "checkpoint_conflict", **head.body())
            candidate = (
                head
                if retry
                else Head(
                    counter,
                    mac,
                    to_root,
                    os.urandom(32).hex(),
                    max(int(time.time()), head.timestamp),
                )
            )
            if not retry:
                self.db.execute(
                    "INSERT INTO transitions VALUES (?, ?, ?)", (ward_id, counter, body)
                )
                self.db.execute(
                    "INSERT INTO heads VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(ward_id) "
                    "DO UPDATE SET counter = excluded.counter, mac = excluded.mac, root = excluded.root, "
                    "head_nonce = excluded.head_nonce, timestamp = excluded.timestamp",
                    (
                        ward_id,
                        candidate.counter,
                        candidate.mac,
                        candidate.root,
                        candidate.head_nonce,
                        candidate.timestamp,
                    ),
                )
            message = (
                b"WARD FINAL v1"
                + bytes.fromhex(ward_id)
                + candidate.counter.to_bytes(4, "big")
                + (bytes.fromhex(candidate.mac) if candidate.mac else ZERO_MAC)
            )
            response = {
                **candidate.body(),
                "signature": self.key.sign(message).hex(),
            }
        # The durable transaction commits before the signature leaves this method.
        return response

    def history(self, ward_id: str) -> dict[str, Any]:
        ward_id = _hex32(ward_id, "wardId")
        with self.lock:
            rows = self.db.execute(
                "SELECT body FROM transitions WHERE ward_id = ? ORDER BY counter",
                (ward_id,),
            ).fetchall()
            return {
                "wardId": ward_id,
                **self._head(ward_id).body(),
                "transitions": [json.loads(row[0]) for row in rows],
            }


class WardManagerServer(ThreadingHTTPServer):
    daemon_threads = False

    def __init__(
        self,
        manager: WardManager,
        port: int = DEFAULT_PORT,
        host: str = "127.0.0.1",
        logger: logging.Logger | None = None,
        delays: bool = False,
    ) -> None:
        self.manager = manager
        self.logger = logger or logging.getLogger("ward-manager")
        self.delays = delays
        super().__init__((host, port), _Handler)


class _Handler(BaseHTTPRequestHandler):
    server: WardManagerServer

    def __getattr__(self, name: str) -> Any:
        if name.startswith("do_"):
            return self._dispatch
        raise AttributeError(name)

    def log_message(self, format: str, *args: Any) -> None:
        pass

    def _read_body(self) -> dict[str, Any]:
        if self.headers.get_content_type() != "application/json":
            raise ApiError(415, "Content-Type must be application/json")
        if self.headers.get("Transfer-Encoding"):
            raise ApiError(400, "Transfer-Encoding is not supported")
        length = self.headers.get("Content-Length")
        if length is None:
            raise ApiError(411, "Content-Length is required")
        try:
            size = int(length)
        except ValueError:
            raise ApiError(400, "Invalid Content-Length") from None
        if not 0 <= size <= MAX_BODY_BYTES:
            raise ApiError(413, "Request body is too large")
        try:
            raw = self.rfile.read(size)
            if len(raw) != size:
                raise ApiError(400, "Incomplete request body")
            body = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ApiError(400, "Invalid JSON") from None
        if not isinstance(body, dict):
            raise ApiError(400, "Expected a JSON object")
        allowed = {"wardId", "counter", "mac"}
        if self.path == "/ward/attest":
            allowed.add("nonce")
        else:
            allowed.add("headNonce")
            allowed.update(
                {"fromCounter", "fromRoot", "root", "authCommit", "signature", "kind"}
            )
        if body.keys() - allowed:
            raise ApiError(400, "Unknown request fields")
        return body

    def _event(self, event: str, request_id: str, **details: Any) -> None:
        self.server.logger.info(
            json.dumps(
                {
                    "time": datetime.now(timezone.utc).isoformat(
                        timespec="milliseconds"
                    ),
                    "id": request_id,
                    "event": event,
                    **details,
                }
            )
        )

    def _dispatch(self) -> None:
        self.connection.settimeout(5)
        started = time.monotonic()
        request_id = uuid.uuid4().hex[:12]
        self._event("request", request_id, method=self.command, path=self.path)
        status = 200
        try:
            if self.command in ("GET", "HEAD") and self.path == "/health":
                body = {"status": "ok", "publicKey": self.server.manager.public_key}
            elif self.path in ("/ward/attest", "/ward/commit"):
                if self.command != "POST":
                    raise ApiError(405, "Use POST for this endpoint")
                request = self._read_body()
                self._event("request_body", request_id, body=request)
                if self.path == "/ward/attest":
                    body = self.server.manager.attest(request)
                else:
                    body = self.server.manager.commit(request)
            elif (
                self.command in ("GET", "HEAD")
                and self.path.startswith("/ward/")
                and self.path.endswith("/history")
            ):
                body = self.server.manager.history(
                    self.path[len("/ward/") : -len("/history")]
                )
            elif self.command in ("GET", "HEAD") and self.path.startswith("/ward/"):
                body = self.server.manager.head(self.path.removeprefix("/ward/"))
            elif self.path == "/health" or self.path.startswith("/ward/"):
                raise ApiError(405, "Use GET for this endpoint")
            else:
                raise ApiError(404, "not_found")
        except ApiError as error:
            status, body = error.status, error.body
        except TimeoutError:
            status, body = 408, {"error": "request_timeout"}
        except sqlite3.Error:
            self.server.logger.exception("WARD Manager database operation failed")
            status, body = 503, {"error": "storage_unavailable"}
        except Exception:
            self.server.logger.exception("WARD Manager request failed")
            status, body = 500, {"error": "internal_error"}

        self._respond(status, body, request_id, started)

    def send_error(
        self, code: int, message: str | None = None, explain: str | None = None
    ) -> None:
        request_id = uuid.uuid4().hex[:12]
        self._event(
            "request",
            request_id,
            method=getattr(self, "command", None),
            path=getattr(self, "path", None),
        )
        self._respond(
            code,
            {"error": message or "invalid_http_request"},
            request_id,
            time.monotonic(),
        )

    def _respond(
        self, status: int, body: dict[str, Any], request_id: str, started: float
    ) -> None:
        if self.server.delays:
            self._event("forward.delay", request_id, hop="WM -> wardd", delayMs=1000)
            time.sleep(1)
        self._event(
            "response",
            request_id,
            status=status,
            durationMs=round((time.monotonic() - started) * 1000, 2),
            body=body,
        )
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Request-ID", request_id)
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            if self.command != "HEAD":
                self.wfile.write(payload)
        except (BrokenPipeError, ConnectionResetError):
            pass
        self.close_connection = True

    do_GET = _dispatch
    do_POST = _dispatch
    do_PUT = _dispatch
    do_DELETE = _dispatch
    do_PATCH = _dispatch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--delays",
        action="store_true",
        default=os.environ.get("WARD_DELAYS") == "1",
        help="Pause one second before sending each response",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=os.environ.get("WARD_MANAGER_PORT", str(DEFAULT_PORT)),
    )
    parser.add_argument("--host", default="127.0.0.1")
    storage = parser.add_mutually_exclusive_group()
    storage.add_argument(
        "--db", type=Path, default=Path.home() / ".trezor-ward-manager/heads.sqlite3"
    )
    storage.add_argument("--memory", action="store_true")
    signing = parser.add_mutually_exclusive_group(required=True)
    signing.add_argument("--debug-key", action="store_true")
    signing.add_argument(
        "--key-file", type=Path, help="File containing a 32-byte hex seed"
    )
    args = parser.parse_args()

    try:
        seed = (
            DEBUG_SEED
            if args.debug_key
            else bytes.fromhex(args.key_file.read_text().strip())
        )
        if len(seed) != 32:
            parser.error("The signing seed must be exactly 32 bytes")
        if not args.memory:
            args.db.parent.mkdir(parents=True, exist_ok=True)
        manager = WardManager(":memory:" if args.memory else args.db, seed)
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.error(str(error))

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    try:
        with WardManagerServer(
            manager, args.port, args.host, delays=args.delays
        ) as server:
            print(
                f"WARD Manager listening on http://{args.host}:{server.server_port} "
                f"(key: {'debug' if args.debug_key else 'custom'}, "
                f"storage: {':memory:' if args.memory else args.db})",
                flush=True,
            )
            print(f"Public key: {manager.public_key}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
    finally:
        manager.close()


if __name__ == "__main__":
    main()
