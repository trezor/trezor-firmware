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

"""`trezorlib.ward_relay` -- the HWI-side WARD adapter -- against a scripted wardd and a fake
session: messages relayed by name, the device's pull answered through `answerProofRequest` on the same
socket, and only WARD messages allowed onto the device."""

from __future__ import annotations

import base64
import hashlib
import json
import socket
import struct
import threading
import typing as t

import pytest

from trezorlib import exceptions, messages
from trezorlib.ward_relay import WardAdapter, WarddClient, WarddError

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
WARD_ID = "cd" * 32


class _Conn:
    """The server side of one RFC 6455 connection, JSON frames only."""

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buf = b""

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def handshake(self) -> None:
        while b"\r\n\r\n" not in self.buf:
            self.buf += self.sock.recv(65536)
        head, _, self.buf = self.buf.partition(b"\r\n\r\n")
        lines = head.decode().split("\r\n")
        headers = {
            k.lower(): v.strip() for k, _, v in (ln.partition(":") for ln in lines[1:])
        }
        accept = base64.b64encode(
            hashlib.sha1(headers["sec-websocket-key"].encode() + GUID).digest()
        ).decode()
        self.sock.sendall(
            (
                "HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                f"Connection: Upgrade\r\nSec-WebSocket-Accept: {accept}\r\n\r\n"
            ).encode()
        )

    def recv(self) -> dict:
        b0, b1 = self._read(2)
        assert b1 & 0x80, "a client frame must be masked"
        n = b1 & 0x7F
        if n == 126:
            (n,) = struct.unpack(">H", self._read(2))
        elif n == 127:
            (n,) = struct.unpack(">Q", self._read(8))
        mask = self._read(4)
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(n)))
        if b0 & 0x0F == 0x8:
            raise ConnectionError
        return json.loads(payload)

    def send(self, frame: dict) -> None:
        data = json.dumps(frame).encode()
        n = len(data)
        head = bytes([0x81, n]) if n < 126 else bytes([0x81, 126]) + struct.pack(">H", n)
        self.sock.sendall(head + data)


class StubWardd:
    """One connection: answers `hello`, then runs `script(conn, frame)` per call."""

    def __init__(self, script: t.Callable[[_Conn, dict], None]) -> None:
        self.script = script
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.url = f"ws://127.0.0.1:{self.listener.getsockname()[1]}"
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        sock, _ = self.listener.accept()
        conn = _Conn(sock)
        conn.handshake()
        try:
            while True:
                frame = conn.recv()
                if frame["method"] == "hello":
                    if frame["params"]["token"] != "token":
                        conn.send({"id": frame["id"], "error": {"code": "unauthorised", "message": "x"}})
                        continue
                    conn.send({"id": frame["id"], "result": {"version": "1.0"}})
                else:
                    self.script(conn, frame)
        except ConnectionError:
            pass


class _App:
    ward_proof_callback = None


class FakeSession:
    """A session whose device pulls a proof inside WARDLookup, as the firmware does."""

    def __init__(self) -> None:
        self.client = t.cast(t.Any, type("C", (), {"app": _App()})())
        self.sent: list = []

    def call(
        self,
        msg: messages.MessageType,
        expect: type[messages.MessageType] = messages.MessageType,
    ) -> messages.MessageType:
        self.sent.append(msg)
        if isinstance(msg, messages.WARDSync):
            return messages.WARDSyncAck(nonce=b"\xab" * 32, version=1, ward_id=bytes.fromhex(WARD_ID))
        if isinstance(msg, messages.WARDLookup):
            ack = self.client.app.ward_proof_callback(
                messages.WARDProofRequest(entry_key=b"\x11" * 32)
            )
            self.pulled = ack
            return messages.WARDLookupAck(valid=True, counter=3, membership=True)
        if isinstance(msg, messages.DisplayAddress):
            self.client.app.ward_proof_callback(messages.WARDProofRequest(entry_key=b"\x22" * 32))
            return messages.Success()
        raise exceptions.TrezorFailure(
            messages.Failure(code=messages.FailureType.UnexpectedMessage, message="no")
        )


def test_lookup_relays_by_name_and_answers_the_pull_on_the_same_socket() -> None:
    seen: list = []

    def script(conn: _Conn, frame: dict) -> None:
        seen.append(frame)
        if frame["method"] == "answerProofRequest":
            conn.send({"id": frame["id"], "result": {"proof": ["aa" * 36], "witness_entry_key": "22" * 32, "witness_commit": "33" * 32}})
            return
        assert frame["method"] == "lookup"
        conn.send({"id": frame["id"], "deviceCall": {"name": "WARDLookup", "message": {"address": "61", "app_id": "btc"}}})
        # the nested answerProofRequest arrives before the deviceReply
        pull = conn.recv()
        seen.append(pull)
        conn.send({"id": pull["id"], "result": {"proof": [], "witness_entry_key": "22" * 32, "witness_commit": "33" * 32}})
        reply = conn.recv()
        seen.append(reply)
        conn.send({"id": frame["id"], "result": {"wardId": WARD_ID, "valid": True, "isMember": True, "counter": 3, "metadata": {"label": "x"}}})

    stub = StubWardd(script)
    session = FakeSession()
    with WarddClient(token="token", url=stub.url) as client:
        result = WardAdapter(t.cast(t.Any, session), client).lookup("btc", "a", "btc")

    assert result["metadata"] == {"label": "x"}
    assert isinstance(session.sent[0], messages.WARDLookup)
    assert session.sent[0].address == b"a" and session.sent[0].app_id == "btc"
    pull, reply = seen[1], seen[2]
    assert pull["method"] == "answerProofRequest"
    assert pull["params"] == {"request": {"entry_key": "11" * 32}}
    assert session.pulled.witness_entry_key == bytes.fromhex("22" * 32)
    assert reply["deviceReply"] == {
        "name": "WARDLookupAck",
        "message": {"valid": True, "counter": 3, "membership": True},
    }
    # the proof callback is restored once the conversation is over
    assert session.client.app.ward_proof_callback is None


def test_a_non_ward_message_never_reaches_the_device() -> None:
    replies: list = []

    def script(conn: _Conn, frame: dict) -> None:
        conn.send({"id": frame["id"], "deviceCall": {"name": "GetPublicKey", "message": {}}})
        replies.append(conn.recv())
        conn.send({"id": frame["id"], "error": {"code": "device_failure", "message": "refused"}})

    stub = StubWardd(script)
    session = FakeSession()
    with WarddClient(token="token", url=stub.url) as client:
        with pytest.raises(WarddError) as e:
            WardAdapter(t.cast(t.Any, session), client).sync()

    assert e.value.code == "device_failure"
    assert session.sent == []
    assert replies[0]["deviceReply"]["name"] == "Failure"
    assert "may not send GetPublicKey" in replies[0]["deviceReply"]["message"]["message"]


def test_a_device_failure_goes_back_to_wardd_as_failure() -> None:
    replies: list = []

    def script(conn: _Conn, frame: dict) -> None:
        conn.send({"id": frame["id"], "deviceCall": {"name": "WARDQueueUpdate", "message": {"address": "61", "new_value": "62"}}})
        replies.append(conn.recv())
        conn.send({"id": frame["id"], "error": {"code": "device_failure", "message": "x"}})

    stub = StubWardd(script)
    with WarddClient(token="token", url=stub.url) as client:
        with pytest.raises(WarddError):
            WardAdapter(t.cast(t.Any, FakeSession()), client).update("btc", "a", "btc", {"label": "x"})

    assert replies[0]["deviceReply"] == {
        "name": "Failure",
        "message": {"code": "UnexpectedMessage", "message": "no"},
    }


def test_display_address_syncs_then_runs_the_native_call_with_pulls_served() -> None:
    calls: list = []

    def script(conn: _Conn, frame: dict) -> None:
        calls.append(frame["method"])
        if frame["method"] == "answerProofRequest":
            conn.send({"id": frame["id"], "result": {"proof": []}})
        else:
            conn.send({"id": frame["id"], "result": {"wardId": WARD_ID, "counter": 0, "root": ""}})

    stub = StubWardd(script)
    session = FakeSession()
    with WarddClient(token="token", url=stub.url) as client:
        result = WardAdapter(t.cast(t.Any, session), client).display_address("btc", "bc1q")

    assert result == {"shown": True, "wardId": WARD_ID}
    assert calls == ["sync", "answerProofRequest"]
    assert session.sent[-1].app_id == "btc"


def test_a_wrong_token_is_refused() -> None:
    stub = StubWardd(lambda conn, frame: None)
    with pytest.raises(WarddError) as e:
        WarddClient(token="wrong", url=stub.url)
    assert e.value.code == "unauthorised"
