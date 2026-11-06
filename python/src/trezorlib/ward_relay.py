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

"""The WARD adapter for HWI and anything else built on trezorlib.

`wardd` (the WARD daemon) implements every WARD flow: sync, lookup, update, the proofs, the
storage and the WARD Manager. The adapter only relays: it puts wardd's protobuf messages on the
caller's session, and answers the device's mid-call WARDProofRequest by asking wardd. The contract
is `packages/wardd/relay.md` in trezor-suite, version 1.x:

    client -> wardd   {id, method, params}
    wardd  -> client  {id, deviceCall: {name, message}}    send this to the device
    client -> wardd   {id, deviceReply: {name, message}}   the device's final answer
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

if t.TYPE_CHECKING:
    from .client import Session

WARDD_DEFAULT_URL = "ws://127.0.0.1:21329"
RELAY_PROTOCOL_VERSION = "1.0"
DEFAULT_TOKEN_FILE = Path.home() / ".trezor-ward" / "token"

# The only messages wardd may put on the device: its WARD flows. Anything else -- GetPublicKey, a
# silent GetAddress -- is answered as a Failure without reaching the device, so whatever answers
# on the wardd port cannot drive the wallet.
# KNOWN DEFICIENCY: wardd is untrusted, yet this list is global, not per conversation. During a
# `lookup` it may still send WARDQueueUpdate (a confirmation the user did not ask for),
# WARDListEntries, or WARDDiscardPending (silently drops queued intents), and the unused
# WARDPerformUpdate / WARDConfirmedByWM / revert messages stay allowed.
# FIXME(ward): allow per method only the messages that method's flow sends.
DEVICE_CALLS = frozenset(
    "WARDSync WARDIngestAttestation WARDReconcile WARDLookup WARDQueueUpdate "
    "WARDPerformUpdate WARDConfirmedByWM WARDDiscardPending WARDVerifyChain "
    "WARDPerformBatch WARDConfirmBatchByWM WARDPerformRevert WARDConfirmRevertByWM "
    "WARDListPendingEdits WARDListEntries WARDCacheEntry WARDCacheExport WARDCacheImport "
    "WARDValidateCache".split()
)

_WS_GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_OP_CONT, _OP_TEXT, _OP_CLOSE, _OP_PING, _OP_PONG = 0x0, 0x1, 0x8, 0x9, 0xA
# Bounds on what a peer may make this client buffer: a handshake head, and one whole message.
_MAX_HEAD = 16 << 10
_MAX_MESSAGE = 16 << 20


class WarddError(Exception):
    """wardd's refusal. `code` is the contract's code: `device_failure`, `ward_id_mismatch`, ..."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _unmask(payload: bytes, mask: bytes) -> bytes:
    """RFC 6455 masking, which is its own inverse."""
    return bytes(b ^ mask[i % 4] for i, b in enumerate(payload))


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
            if len(self._buf) > _MAX_HEAD:
                raise WarddError("protocol", "oversized WebSocket handshake")
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
        n, op = len(payload), 0x80 | opcode
        if n < 126:
            header = struct.pack(">BB", op, 0x80 | n)
        elif n < 1 << 16:
            header = struct.pack(">BBH", op, 0x80 | 126, n)
        else:
            header = struct.pack(">BBQ", op, 0x80 | 127, n)
        mask = os.urandom(4)
        self.sock.sendall(header + mask + _unmask(payload, mask))

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
            # RFC 6455: a server never masks, and a control frame is short and whole
            if b1 & 0x80 or (opcode >= 8 and (n > 125 or not fin)):
                raise WarddError("protocol", "malformed WebSocket frame")
            if len(message) + n > _MAX_MESSAGE:
                raise WarddError("protocol", "wardd sent an oversized message")
            payload = self._read_exact(n)
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
DeviceCall = t.Callable[[str, dict], t.Tuple[str, dict]]


class WarddClient:
    """One authenticated socket to wardd: one relay endpoint.

    A call may nest: while a conversation waits on the device, the device's pull is answered with a
    `answerProofRequest` call on the same socket. wardd sends nothing for the waiting conversation until it
    gets its `deviceReply`, so the nested call's frames are the only ones in flight.
    """

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
                    if call["name"] not in DEVICE_CALLS:
                        raise RuntimeError(f"wardd may not send {call['name']}")
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


class WardAdapter:
    """The WARD adapter on one session: the two hooks every host library has.

    `relay` puts a wardd message on the session and returns the device's final answer;
    `on_proof_request` answers the device's WARDProofRequest through wardd's `answerProofRequest`. While
    the adapter is entered, the second is the client's `ward_proof_callback`, so it also answers the
    pulls of the caller's own calls (`display_address`, signing). `on_node_request` does the same
    for a listing walk's WARDNodeRequest (`answerNodeRequest`).
    """

    def __init__(self, session: "Session", client: WarddClient) -> None:
        self.session = session
        self.client = client
        self._saved: t.Any = None

    # FIXME(ward): redesign. The proof/node hooks are installed on the CLIENT-WIDE AppManifest, so
    # they answer pulls from every session on this client, and entering the adapter again (as
    # `_conversation` does inside a caller's `with adapter:`) overwrites `_saved` with the
    # adapter's own hooks -- the outer exit then leaves them installed for good, and unrelated
    # pulls go to wardd. The hooks should be scoped to one call on one session.
    # Proposed fix: give `client.Session` an optional `ward_hooks` slot (proof, node) that
    # `TrezorClient._call` consults before the AppManifest callbacks, plus a helper
    # `ward_scope(session, hooks)` that sets it and restores the PREVIOUS value from a local
    # variable (so nesting is safe). `relay` and `display_address` then wrap only their own
    # `session.call` in that scope; nothing is installed on the client, other sessions never see
    # the hooks, and `__enter__`/`__exit__` become a session-scoped, nest-safe opt-in for the
    # caller's own calls.
    def __enter__(self) -> "WardAdapter":
        app = self.session.client.app
        self._saved = (app.ward_proof_callback, app.ward_node_callback)
        app.ward_proof_callback = self.on_proof_request
        app.ward_node_callback = self.on_node_request
        return self

    def __exit__(self, *exc: object) -> None:
        app = self.session.client.app
        app.ward_proof_callback, app.ward_node_callback = self._saved

    def relay(self, name: str, body: dict) -> tuple[str, dict]:
        message_type = getattr(messages, name, None)
        if not (
            isinstance(message_type, type)
            and issubclass(message_type, protobuf.MessageType)
        ):
            raise ValueError(f"unknown message {name}")
        res = self.session.call(protobuf.dict_to_proto(message_type, body))
        return type(res).__name__, protobuf.to_dict(res)

    def on_proof_request(self, request: messages.WARDProofRequest) -> messages.WARDProofAck:
        try:
            ack = self.client.call(
                "answerProofRequest", {"request": protobuf.to_dict(request)}
            )
        except (WarddError, OSError):
            # ACCEPTED: any wardd failure is reported as `unavailable`; the device may then
            # show a STICKY cached label, possibly stale, marked as cached.
            return messages.WARDProofAck(unavailable=True)
        return protobuf.dict_to_proto(messages.WARDProofAck, ack)

    def on_node_request(
        self, request: messages.WARDNodeRequest
    ) -> messages.WARDNodeAck:
        ack = self.client.call(
            "answerNodeRequest", {"request": protobuf.to_dict(request)}
        )
        return protobuf.dict_to_proto(messages.WARDNodeAck, ack)

    def _conversation(self, method: str, params: dict) -> dict:
        with self:
            return self.client.call(method, params, self.relay)

    # --- the wallet-facing calls ---------------------------------------------------------

    def sync(self, ward_id: bytes | None = None) -> dict:
        """Install wardd's WM-attested head on the session; returns `{wardId, counter, root}`."""
        return self._conversation("sync", _ward_id(ward_id))

    def lookup(
        self,
        app_id: str,
        address: str,
        network_symbol: str,
        ward_id: bytes | None = None,
    ) -> dict:
        """The device's verdict on (app_id, address) and, for a proven member, its stored label:
        `{wardId, valid, isMember, counter, metadata?}`."""
        return self._conversation(
            "lookup",
            {
                "appId": app_id,
                "address": address,
                "networkSymbol": network_symbol,
                **_ward_id(ward_id),
            },
        )

    def verify(
        self,
        app_id: str,
        address: str,
        network_symbol: str,
        ward_id: bytes | None = None,
    ) -> bool:
        """Whether the device proved (app_id, address) a member of its authenticated tree."""
        res = self.lookup(app_id, address, network_symbol, ward_id)
        return bool(res["valid"] and res["isMember"])

    def update(
        self,
        app_id: str,
        address: str,
        network_symbol: str,
        metadata: dict | None = None,
        delete: bool = False,
        ward_id: bytes | None = None,
    ) -> dict:
        """Write (or, with `delete`, remove) the entry; the user confirms on the device. Returns
        `{wardId, counter, root}`, with `conflict` if the WM head moved on first (retry)."""
        params = {
            "appId": app_id,
            "address": address,
            "networkSymbol": network_symbol,
            "metadata": metadata or {},
            **_ward_id(ward_id),
        }
        if delete:
            params["delete"] = True
        return self._conversation("update", params)

    def cache_entry(
        self, entry_key: bytes, sticky: bool = False, ward_id: bytes | None = None
    ) -> dict:
        """Copy the entry at `entry_key` into the device's offline cache, STICKY if asked:
        wardd syncs, then the device pulls and verifies the entry's proof and stores it.
        Returns `{wardId, replaced, counter}`."""
        params = {"entryKey": entry_key.hex(), **_ward_id(ward_id)}
        if sticky:
            params["sticky"] = True
        return self._conversation("cacheEntry", params)

    def export_cache(self) -> list[bytes]:
        """Back up the device's cached entries, each sealed to the wallet."""
        res = self._conversation("exportCache", {})
        return [bytes.fromhex(blob) for blob in res["entries"]]

    def import_cache(self, blobs: list[bytes]) -> dict:
        """Load a backup into the device's cache: `{imported, skipped}`."""
        return self._conversation(
            "importCache", {"entries": [blob.hex() for blob in blobs]}
        )

    def validate_cache(self, ward_id: bytes | None = None) -> dict:
        """Sync, then check every cached entry by proof: `{wardId, counter, root, cache}`."""
        return self._conversation("validateCache", _ward_id(ward_id))

    def list_entries(
        self,
        app_id: str | None = None,
        key_type: str | None = None,
        device_id: int | None = None,
        ward_id: bytes | None = None,
    ) -> dict:
        """Show every matching entry on the device: wardd syncs, then the device walks its
        trusted root, pulling each node through wardd. Returns counts only:
        `{wardId, shown, entries, counter, complete}`."""
        filters = {"appId": app_id, "keyType": key_type, "deviceId": device_id}
        return self._conversation(
            "listEntries",
            {
                **{k: v for k, v in filters.items() if v is not None},
                **_ward_id(ward_id),
            },
        )

    def display_address(
        self, app_id: str, address: str, ward_id: bytes | None = None
    ) -> dict:
        """Show `address` with its WARD label: wardd syncs the session, then the native
        DisplayAddress runs and its label pull is answered by wardd."""
        with self:
            synced = self.client.call("sync", _ward_id(ward_id), self.relay)
            self.session.call(
                messages.DisplayAddress(address=address, app_id=app_id),
                expect=messages.Success,
            )
        return {"shown": True, "wardId": synced["wardId"]}


def _ward_id(ward_id: bytes | None) -> dict:
    return {} if ward_id is None else {"wardId": ward_id.hex()}
