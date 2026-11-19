#!/usr/bin/env python3
"""Development WARD Manager REST service for the encrypted WARD protocol.

Run with ``uv run python tools/ward_manager.py --debug-key``. The service stores
WARD checkpoints and can retain the latest batch's opaque keys and digests.
The debug signing key is accepted only by debug firmware.
"""

from __future__ import annotations

import argparse
import hmac
import json
import logging
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable
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

from trezorlib.authdb_tree import root_from_value_digests
from trezorlib.ward_protocol import (
    EMPTY_ROOT,
    attestation_message,
    finalization_message,
    transition_message,
)

DEBUG_SEED = b"AUTHDB QM DEBUG KEY SEED v1 ...."
DEFAULT_PORT = 21330
MAX_BODY_BYTES = 4096
MAX_COUNTER = 0xFFFFFFFF
MAX_RECOVERY_LEAVES = 8  # The firmware's per-wallet pending batch limit.
ZERO_MAC = bytes(32)
RecoveryChanges = dict[bytes, bytes | None]
TRANSITION_FIELDS = {
    "wardId",
    "kind",
    "fromCounter",
    "fromRoot",
    "counter",
    "root",
    "mac",
    "authCommit",
    "signature",
}


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


def _recovery_changes(value: Any, *, batch: bool = True) -> RecoveryChanges:
    if not isinstance(value, list) or (
        batch and not 1 <= len(value) <= MAX_RECOVERY_LEAVES
    ):
        raise ApiError(400, "Invalid recovery leaf list")
    changes: RecoveryChanges = {}
    for leaf in value:
        if not isinstance(leaf, dict) or leaf.keys() != {"entryKey", "valueDigest"}:
            raise ApiError(
                400, "Expected entryKey and valueDigest for each recovery leaf"
            )
        key = bytes.fromhex(_hex32(leaf["entryKey"], "entryKey"))
        if key in changes:
            raise ApiError(400, "Duplicate recovery entryKey")
        digest = leaf["valueDigest"]
        changes[key] = (
            None if digest is None else bytes.fromhex(_hex32(digest, "valueDigest"))
        )
    return changes


def _recovery_body(changes: RecoveryChanges) -> list[dict[str, str | None]]:
    return [
        {"entryKey": key.hex(), "valueDigest": None if digest is None else digest.hex()}
        for key, digest in sorted(changes.items())
    ]


@dataclass(frozen=True)
class Head:
    counter: int = 0
    mac: str | None = None
    root: str = ""
    timestamp: int = 0

    def body(self) -> dict[str, Any]:
        return {
            "counter": self.counter,
            "root": self.root,
            "timestamp": self.timestamp,
            **({"mac": self.mac} if self.mac else {}),
        }


ReadReplica = Callable[[str, Head, list[dict[str, Any]]], dict[bytes, bytes]]


def replica_command(command: list[str]) -> ReadReplica:
    def read(
        ward_id: str, head: Head, history: list[dict[str, Any]]
    ) -> dict[bytes, bytes]:
        try:
            result = subprocess.run(
                command,
                input=json.dumps(
                    {"wardId": ward_id, "head": head.body(), "history": history}
                ),
                capture_output=True,
                text=True,
                timeout=6,
                check=True,
            )
            leaves = _recovery_changes(json.loads(result.stdout), batch=False)
        except (OSError, ValueError, subprocess.SubprocessError, ApiError) as error:
            raise ApiError(503, "recovery_replica_unavailable") from error
        if any(digest is None for digest in leaves.values()):
            raise ApiError(503, "recovery_replica_unavailable")
        return {key: digest for key, digest in leaves.items() if digest is not None}

    return read


class WardManager:
    """A persistent per-ward checkpoint register and the WM signing key."""

    def __init__(
        self, database: str | Path, seed: bytes, read_replica: ReadReplica | None = None
    ) -> None:
        self.key = Ed25519PrivateKey.from_private_bytes(seed)
        self.read_replica = read_replica
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
                    "timestamp INTEGER NOT NULL)"
                )
                columns = {
                    row[1] for row in self.db.execute("PRAGMA table_info(heads)")
                }
                if columns != {"ward_id", "counter", "mac", "root", "timestamp"}:
                    raise ValueError(
                        "Legacy WARD database with incompatible signatures: start a new database"
                    )
                self.db.execute(
                    "CREATE TABLE IF NOT EXISTS transitions "
                    "(ward_id TEXT NOT NULL, counter INTEGER NOT NULL, body TEXT NOT NULL, "
                    "PRIMARY KEY (ward_id, counter))"
                )
                self.db.execute(
                    "CREATE TABLE IF NOT EXISTS recovery "
                    "(ward_id TEXT PRIMARY KEY, counter INTEGER NOT NULL, body TEXT NOT NULL)"
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
            "SELECT counter, mac, root, timestamp FROM heads WHERE ward_id = ?",
            (ward_id,),
        ).fetchone()
        return Head(*row) if row else Head()

    def _latest(self, ward_id: str, head: Head) -> dict[str, Any]:
        """The ward ID and the latest accepted transition, absent at genesis."""
        row = self.db.execute(
            "SELECT body FROM transitions WHERE ward_id = ? AND counter = ?",
            (ward_id, head.counter),
        ).fetchone()
        return {
            "wardId": ward_id,
            **({"transition": json.loads(row[0])} if row else {}),
        }

    def head(self, ward_id: str) -> dict[str, Any]:
        ward_id = _hex32(ward_id, "wardId")
        with self.lock:
            return self._latest(ward_id, self._head(ward_id))

    def attest(self, request: dict[str, Any]) -> dict[str, Any]:
        ward_id = _hex32(request.get("wardId"), "wardId")
        nonce = _hex32(request.get("nonce"), "nonce")
        with self.lock:
            head = self._head(ward_id)
            timestamp = max(int(time.time()), head.timestamp)
            message = attestation_message(
                ward_id, nonce, head.counter, head.mac, timestamp
            )
            return {
                **self._latest(ward_id, head),
                "nonce": nonce,
                "timestamp": timestamp,
                "signature": self.key.sign(message).hex(),
            }

    def _recovery(self, ward_id: str) -> tuple[int, str] | None:
        return self.db.execute(
            "SELECT counter, body FROM recovery WHERE ward_id = ?", (ward_id,)
        ).fetchone()

    def _history(self, ward_id: str, counter: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            "SELECT body FROM transitions WHERE ward_id = ? AND counter <= ? ORDER BY counter",
            (ward_id, counter),
        ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def _check_recovery(
        self, record: dict[str, Any], changes: RecoveryChanges | None
    ) -> bool:
        ward_id = record["wardId"]
        with self.lock, self.db:
            self.db.execute("BEGIN")
            head = self._head(ward_id)
            if (head.counter, head.root) != (
                record["fromCounter"],
                record["fromRoot"],
            ):
                return False  # Exact retries are handled by the final transaction.
            previous = self._recovery(ward_id)
            if changes is None and previous is None:
                return True
            read_replica = self.read_replica
            if read_replica is None:
                raise ApiError(503, "recovery_replica_unavailable")
            if record["kind"] == "revert":
                # A revert can release the slot only if its destination is recoverable.
                history = self._history(ward_id, head.counter - 1)
                last = history[-1] if history else None
                if record["root"] != (last["root"] if last else ""):
                    raise ApiError(400, "Invalid recovery revert target")
                head = Head(
                    counter=head.counter - 1,
                    root=record["root"],
                    mac=last["mac"] if last else None,
                )
            else:
                if changes is None:
                    raise ApiError(400, "recoveryLeaves required for this ward")
                history = self._history(ward_id, head.counter)

        values = read_replica(ward_id, head, history) if head.counter else {}
        if root_from_value_digests(values).hex() != (head.root or EMPTY_ROOT.hex()):
            raise ApiError(503, "recovery_predecessor_unavailable")
        if changes is None:
            return True
        for key, digest in changes.items():
            if digest is None:
                if key not in values:
                    raise ApiError(400, "Recovery delete must name a present entry")
                del values[key]
            elif values.get(key) == digest:
                raise ApiError(400, "Recovery set must change the value digest")
            else:
                values[key] = digest
        if root_from_value_digests(values).hex() != (
            record["root"] or EMPTY_ROOT.hex()
        ):
            raise ApiError(
                400, "Recovery leaves do not reconstruct the signed target root"
            )
        return True

    def commit(self, request: dict[str, Any]) -> dict[str, Any]:
        transition = request.get("transition")
        if not isinstance(transition, dict) or transition.keys() != TRANSITION_FIELDS:
            raise ApiError(400, "Expected a complete transition object")
        ward_id = _hex32(transition["wardId"], "wardId")
        counter = _counter(transition["counter"])
        from_counter = _counter(transition["fromCounter"])

        def root(value: Any) -> str:
            if value == "":
                return ""
            result = _hex32(value, "root")
            return "" if result == EMPTY_ROOT.hex() else result

        to_root, from_root = root(transition["root"]), root(transition["fromRoot"])
        mac = _mac(transition["mac"])
        if mac is None or counter != from_counter + 1:
            raise ApiError(
                400, "A successor transition and nonzero wallet MAC are required"
            )
        kind = transition["kind"]
        if kind not in ("commit", "revert"):
            raise ApiError(400, "Invalid transition kind")
        changes = None
        if "recoveryLeaves" in request:
            if kind != "commit":
                raise ApiError(400, "recoveryLeaves are allowed only for a commit")
            changes = _recovery_changes(request["recoveryLeaves"])
        recovery_body = (
            json.dumps(_recovery_body(changes), separators=(",", ":"))
            if changes is not None
            else None
        )
        auth_commit = _hex32(transition["authCommit"], "authCommit")
        signature = transition["signature"]
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
        }
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(ward_id)).verify(
                bytes.fromhex(signature), transition_message(record)
            )
        except (ValueError, InvalidSignature):
            raise ApiError(403, "Invalid wallet transition signature") from None
        checked = self._check_recovery(record, changes)
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
            if retry:
                recovery = self._recovery(ward_id)
                if recovery != (
                    (counter, recovery_body) if recovery_body is not None else None
                ):
                    raise ApiError(
                        409, "recovery_batch_conflict", **self._latest(ward_id, head)
                    )
            if not retry and (
                not checked or from_counter != head.counter or from_root != head.root
            ):
                raise ApiError(
                    409, "checkpoint_conflict", **self._latest(ward_id, head)
                )
            candidate = (
                head
                if retry
                else Head(counter, mac, to_root, max(int(time.time()), head.timestamp))
            )
            if not retry:
                self.db.execute(
                    "INSERT INTO transitions VALUES (?, ?, ?)", (ward_id, counter, body)
                )
                if recovery_body is not None:
                    self.db.execute(
                        "INSERT OR REPLACE INTO recovery VALUES (?, ?, ?)",
                        (ward_id, counter, recovery_body),
                    )
                elif kind == "revert":
                    self.db.execute(
                        "DELETE FROM recovery WHERE ward_id = ?", (ward_id,)
                    )
                self.db.execute(
                    "INSERT INTO heads VALUES (?, ?, ?, ?, ?) ON CONFLICT(ward_id) "
                    "DO UPDATE SET counter = excluded.counter, mac = excluded.mac, root = excluded.root, "
                    "timestamp = excluded.timestamp",
                    (
                        ward_id,
                        candidate.counter,
                        candidate.mac,
                        candidate.root,
                        candidate.timestamp,
                    ),
                )
            message = finalization_message(record, candidate.timestamp)
            response = {
                "wardId": ward_id,
                "transition": record,
                "timestamp": candidate.timestamp,
                "signature": self.key.sign(message).hex(),
            }
        # The durable transaction commits before the signature leaves this method.
        return response

    def history(
        self, ward_id: str, *, include_recovery: bool = False
    ) -> dict[str, Any]:
        ward_id = _hex32(ward_id, "wardId")
        with self.lock, self.db:
            self.db.execute("BEGIN")
            head = self._head(ward_id)
            recovery = self._recovery(ward_id) if include_recovery else None
            return {
                "wardId": ward_id,
                "transitions": self._history(ward_id, head.counter),
                **(
                    {"recoveryLeaves": json.loads(recovery[1])}
                    if recovery is not None and recovery[0] == head.counter
                    else {}
                ),
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
        recovery_read_token: str | None = None,
    ) -> None:
        self.manager = manager
        self.logger = logger or logging.getLogger("ward-manager")
        self.delays = delays
        self.recovery_read_token = recovery_read_token
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
        allowed = (
            {"wardId", "nonce"}
            if self.path == "/ward/attest"
            else {"transition", "recoveryLeaves"}
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
                self._event(
                    "request_body",
                    request_id,
                    body={
                        key: value
                        for key, value in request.items()
                        if key != "recoveryLeaves"
                    },
                )
                if self.path == "/ward/attest":
                    body = self.server.manager.attest(request)
                else:
                    body = self.server.manager.commit(request)
            elif (
                self.command in ("GET", "HEAD")
                and self.path.startswith("/ward/")
                and self.path.endswith("/history")
            ):
                token = self.server.recovery_read_token
                authorization = self.headers.get("Authorization", "")
                include_recovery = token is not None and hmac.compare_digest(
                    authorization.encode(), f"Bearer {token}".encode()
                )
                body = self.server.manager.history(
                    self.path[len("/ward/") : -len("/history")],
                    include_recovery=include_recovery,
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
            body={key: value for key, value in body.items() if key != "recoveryLeaves"},
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
    parser.add_argument(
        "--recovery-replica-command",
        help="Command that reconstructs a checkpoint from an independent Evolu replica",
    )
    parser.add_argument(
        "--recovery-read-token-file",
        type=Path,
        help="Bearer token for reading recovery leaves through the history endpoint",
    )
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
        recovery_token = (
            args.recovery_read_token_file.read_text().strip()
            if args.recovery_read_token_file
            else None
        )
        if args.recovery_replica_command is not None and not recovery_token:
            parser.error("Recovery requires a nonempty --recovery-read-token-file")
        command = shlex.split(args.recovery_replica_command or "")
        if args.recovery_replica_command is not None and not command:
            parser.error("Recovery requires a nonempty --recovery-replica-command")
        manager = WardManager(
            ":memory:" if args.memory else args.db,
            seed,
            replica_command(command) if command else None,
        )
    except (OSError, ValueError, sqlite3.Error) as error:
        parser.error(str(error))

    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    try:
        with WardManagerServer(
            manager,
            args.port,
            args.host,
            delays=args.delays,
            recovery_read_token=recovery_token,
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
