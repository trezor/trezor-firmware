# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""The Python binding of the wardd relay, for HWI and anything else built on trezorlib.

`wardd` (the local WARD service) owns the replica, the WM client and the order of every sync and
flush; a binding only carries messages between it and the device on the caller's session. The
contract is `packages/ward-core/relay.md` in trezor-suite, version 1.x:

    client -> wardd   {id, method, params}
    wardd  -> client  {id, deviceCall: {name, message}}    send this to the device
    client -> wardd   {id, deviceReply: {name, message}}   what the device said, pulls included
    wardd  -> client  {id, result} | {id, error: {code, message}}

Messages travel by name with a JSON body (`protobuf.to_dict` / `dict_to_proto`, bytes as hex).
The socket is a stdlib-only RFC 6455 client, so trezorlib takes no new dependency.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import typing as t
from pathlib import Path
from urllib.parse import urlparse

from . import exceptions, messages, protobuf
from .ward import Answer, Leaf, WardResult

if t.TYPE_CHECKING:
    from .client import Session

WARDD_DEFAULT_URL = "ws://127.0.0.1:21329"
RELAY_PROTOCOL_VERSION = "1.0"
DEFAULT_TOKEN_FILE = Path.home() / ".trezor-ward" / "token"

_WS_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_OP_CONT, _OP_TEXT, _OP_CLOSE, _OP_PING, _OP_PONG = 0x0, 0x1, 0x8, 0x9, 0xA


class WarddError(Exception):
    """wardd's refusal. `code` is the contract's code: `wm_conflict`, `needs_rejoin`, ..."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class _WebSocket:
    """A minimal RFC 6455 client: enough for a localhost JSON peer, and no more."""

    def __init__(self, url: str, timeout: float | None) -> None:
        u = urlparse(url)
        if u.scheme != "ws":
            raise ValueError("wardd is reached over ws:// on localhost")
        try:
            self.sock = socket.create_connection(
                (u.hostname or "127.0.0.1", u.port or 80), timeout=timeout
            )
        except OSError as e:
            raise WarddError(
                "unreachable", f"wardd is not reachable at {url}: {e}"
            ) from e
        self._buf = b""
        key = base64.b64encode(os.urandom(16))
        # No Origin header: wardd admits a local process on the pairing token alone.
        request = (
            f"GET {u.path or '/'} HTTP/1.1\r\n"
            f"Host: {u.netloc}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key.decode()}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode())
        head = self._read_until(b"\r\n\r\n").decode("latin-1")
        status, *lines = head.split("\r\n")
        if " 101 " not in status + " ":
            raise WarddError("unreachable", f"wardd refused the connection: {status}")
        headers = {
            k.strip().lower(): v.strip()
            for k, _, v in (line.partition(":") for line in lines if line)
        }
        accept = base64.b64encode(hashlib.sha1(key + _WS_GUID).digest()).decode()
        if headers.get("sec-websocket-accept") != accept:
            raise WarddError("unreachable", "not a WebSocket endpoint")

    def _read_until(self, marker: bytes) -> bytes:
        while marker not in self._buf:
            self._recv()
        head, _, self._buf = self._buf.partition(marker)
        return head

    def _recv(self) -> None:
        chunk = self.sock.recv(65536)
        if not chunk:
            raise WarddError("closed", "wardd closed the connection")
        self._buf += chunk

    def _read_exact(self, n: int) -> bytes:
        while len(self._buf) < n:
            self._recv()
        out, self._buf = self._buf[:n], self._buf[n:]
        return out

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        # A client MUST mask every frame it sends.
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 1 << 16:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header) + mask + masked)

    def send_text(self, text: str) -> None:
        self._send_frame(_OP_TEXT, text.encode())

    def recv_text(self) -> str:
        message = b""
        while True:
            b0, b1 = self._read_exact(2)
            opcode, fin = b0 & 0x0F, bool(b0 & 0x80)
            n = b1 & 0x7F
            if n == 126:
                (n,) = struct.unpack(">H", self._read_exact(2))
            elif n == 127:
                (n,) = struct.unpack(">Q", self._read_exact(8))
            mask = self._read_exact(4) if b1 & 0x80 else None
            payload = self._read_exact(n)
            if mask:
                payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
            if opcode == _OP_PING:
                self._send_frame(_OP_PONG, payload)
            elif opcode == _OP_CLOSE:
                raise WarddError("closed", "wardd closed the connection")
            elif opcode in (_OP_TEXT, _OP_CONT):
                message += payload
                if fin:
                    return message.decode()

    def close(self) -> None:
        try:
            self._send_frame(_OP_CLOSE, b"")
        except OSError:
            pass
        self.sock.close()


# A device for the conversation: (name, json body) -> (name, json body).
DeviceCall = t.Callable[[str, dict], tuple[str, dict]]


class WarddClient:
    """One authenticated socket to wardd. Calls are sequential, as a session's calls are."""

    def __init__(
        self,
        token: str | None = None,
        url: str = WARDD_DEFAULT_URL,
        timeout: float | None = 120.0,
    ) -> None:
        if token is None:
            token = DEFAULT_TOKEN_FILE.read_text().strip()
        self._ws = _WebSocket(url, timeout)
        self._next_id = 1
        try:
            self.call("hello", {"version": RELAY_PROTOCOL_VERSION, "token": token})
        except Exception:
            self._ws.close()
            raise

    def __enter__(self) -> "WarddClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._ws.close()

    def call(
        self,
        method: str,
        params: dict | None = None,
        device: DeviceCall | None = None,
    ) -> dict:
        """One call; a conversation when wardd needs the device, answered through `device`.
        Every deviceCall gets a deviceReply -- a raising device is answered as a `Failure`."""
        call_id = self._next_id
        self._next_id += 1
        self._ws.send_text(
            json.dumps({"id": call_id, "method": method, "params": params or {}})
        )
        while True:
            frame = json.loads(self._ws.recv_text())
            if frame.get("id") != call_id:
                continue
            if "deviceCall" in frame:
                call = frame["deviceCall"]
                try:
                    if device is None:
                        raise RuntimeError(f"no device to answer {call['name']}")
                    name, body = device(call["name"], call.get("message") or {})
                except Exception as e:
                    name, body = "Failure", _failure_body(e)
                self._ws.send_text(
                    json.dumps(
                        {"id": call_id, "deviceReply": {"name": name, "message": body}}
                    )
                )
                continue
            if "error" in frame:
                raise WarddError(frame["error"]["code"], frame["error"]["message"])
            return frame["result"]


def _failure_body(e: Exception) -> dict:
    if isinstance(e, exceptions.TrezorFailure):
        return {"code": e.code.name if e.code else None, "message": e.message or str(e)}
    return {"message": str(e)}


def session_device(session: "Session") -> DeviceCall:
    """Put a named message on `session` and return what the device said, pulls included."""

    def device(name: str, body: dict) -> tuple[str, dict]:
        message_type = getattr(messages, name, None)
        if not (
            isinstance(message_type, type)
            and issubclass(message_type, protobuf.MessageType)
        ):
            raise ValueError(f"unknown message {name}")
        res = session.call(protobuf.dict_to_proto(message_type, body))
        return type(res).__name__, protobuf.to_dict(res)

    return device


def open_store(
    session: "Session",
    client: WarddClient,
    ward_id: bytes | None = None,
    evolu_node: bytes | None = None,
) -> dict:
    """Select the wallet in wardd: `ward_id`, or the session's own (asked with `WardSync`).
    `evolu_node` is the device's `EvoluGetNode` node; a `--memory` wardd needs none."""
    if ward_id is None:
        ack = session.call(messages.WardSync(), expect=messages.WardSyncAck)
        if ack.ward_id is None:
            raise RuntimeError("the device reported no ward_id")
        ward_id = ack.ward_id
    params: dict = {"wardId": ward_id.hex()}
    if evolu_node is not None:
        params["evoluNode"] = evolu_node.hex()
    return client.call("openStore", params)


def sync(session: "Session", client: WarddClient, rejoin: bool = False) -> dict:
    """Bring the device to the WM's head (reconcile, the chain walk, or -- with `rejoin` -- a
    rejoin after a fork, which discards this device's changes above it and is confirmed on the
    device). Run `open_store` first, on the same session."""
    return client.call("sync", {"rejoin": rejoin}, session_device(session))


def flush(session: "Session", client: WarddClient, max_batch: int = 1) -> dict:
    """Publish everything the device holds queued, syncing after each transition -- one change per
    transition, or up to `max_batch` folded into one. One session for the whole drain: the device's
    sync state belongs to the session."""
    return client.call("flush", {"maxBatch": max_batch}, session_device(session))


def status(client: WarddClient) -> dict:
    """The replica's head and the WM's, for the store last opened."""
    return client.call("status")


class WarddProvider:
    """An `EntryProvider` backed by wardd's replica, for the trezorlib calls that pull. Open the
    store first; after a write, `apply_result` makes wardd store and publish it."""

    def __init__(self, client: WarddClient, staged: list | None = None) -> None:
        self.client = client
        self.staged = staged or []

    def __call__(self, entry_key: bytes) -> Answer:
        ack = self.client.call(
            "serveEntry",
            {
                "request": {"entry_key": entry_key.hex()},
                "staged": [[k.hex(), c.hex()] for k, c in self.staged],
            },
        )
        identity, content = ack.get("identity"), ack.get("content")
        identity = identity and protobuf.dict_to_proto(messages.WardLeafIdentity, identity)
        content = content and protobuf.dict_to_proto(messages.WardLeafContent, content)

        def hex_or_none(name: str) -> bytes | None:
            value = ack.get(name)
            return bytes.fromhex(value) if value else None

        return Answer(
            leaf=Leaf(identity or None, content or None) if identity or content else None,
            proof=[bytes.fromhex(p) for p in ack.get("proof") or []],
            witness_entry_key=hex_or_none("witness_entry_key"),
            witness_commit=hex_or_none("witness_commit"),
        )

    def with_staged(self, staged: list) -> "WarddProvider":
        return WarddProvider(self.client, list(staged))

    def apply_result(self, result: WardResult) -> dict:
        return self.client.call("applyResult", protobuf.to_dict(result.response))
