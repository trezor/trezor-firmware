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

"""`trezorlib.ward_relay` against a scripted wardd, and -- when the suite checkout is at hand
(`WARDD_SUITE_DIR`) -- against the real one, with a small fake device whose signatures wardd
verifies for real."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import struct
import subprocess
import threading
import time
import typing as t
from pathlib import Path

import pytest

from trezorlib import _ed25519, exceptions, messages, protobuf, ward_trie
from trezorlib.ward_relay import (
    WarddClient,
    WarddError,
    WarddProvider,
    _WebSocket,
    flush,
    open_store,
    session_device,
    status,
    sync,
)

GUID = b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# --- a scripted wardd: server-side RFC 6455, one conversation script per method -----------------


class _ServerConn:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buf = b""
        self.pongs: list[bytes] = []

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
            k.lower(): v.strip() for k, _, v in (l.partition(":") for l in lines[1:])
        }
        self.origin = headers.get("origin")
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
        while True:
            b0, b1 = self._read(2)
            assert b1 & 0x80, "a client frame must be masked"
            n = b1 & 0x7F
            if n == 126:
                (n,) = struct.unpack(">H", self._read(2))
            elif n == 127:
                (n,) = struct.unpack(">Q", self._read(8))
            mask = self._read(4)
            payload = bytes(b ^ mask[i % 4] for i, b in enumerate(self._read(n)))
            opcode = b0 & 0x0F
            if opcode == 0x8:
                raise ConnectionError
            if opcode == 0xA:
                # the pong our ping asked for -- recorded, since answering one is the client's job
                self.pongs.append(payload)
                continue
            return json.loads(payload)

    def send(self, frame: dict, ping_first: bool = False) -> None:
        if ping_first:
            self.sock.sendall(bytes([0x89, 2]) + b"hi")
        data = json.dumps(frame).encode()
        n = len(data)
        if n < 126:
            head = bytes([0x81, n])
        elif n < 1 << 16:
            head = bytes([0x81, 126]) + struct.pack(">H", n)
        else:
            head = bytes([0x81, 127]) + struct.pack(">Q", n)
        self.sock.sendall(head + data)


class StubWardd:
    """Accepts connections; answers `hello`, runs SCRIPTS (method -> fn(conn, frame))."""

    def __init__(self, scripts: dict[str, t.Callable]) -> None:
        self.scripts = scripts
        self.received: list[dict] = []
        self.origins: list = []
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen()
        self.url = f"ws://127.0.0.1:{self.listener.getsockname()[1]}"
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        while True:
            try:
                sock, _ = self.listener.accept()
            except OSError:
                return
            threading.Thread(target=self._conn, args=(sock,), daemon=True).start()

    def _conn(self, sock: socket.socket) -> None:
        conn = _ServerConn(sock)
        conn.handshake()
        self.origins.append(conn.origin)
        try:
            while True:
                frame = conn.recv()
                self.received.append(frame)
                if frame["method"] == "hello":
                    if frame["params"]["token"] == "good":
                        conn.send({"id": frame["id"], "result": {"version": "1.0"}})
                    else:
                        conn.send(
                            {
                                "id": frame["id"],
                                "error": {"code": "unauthorised", "message": "no"},
                            }
                        )
                    continue
                self.scripts[frame["method"]](conn, frame)
        except ConnectionError:
            pass

    def close(self) -> None:
        self.listener.close()


def _conversation(conn: _ServerConn, frame: dict) -> None:
    i = frame["id"]
    conn.send(
        {"id": i, "deviceCall": {"name": "WardSync", "message": {}}}, ping_first=True
    )
    first = conn.recv()["deviceReply"]
    conn.send({"id": i, "deviceCall": {"name": "WardReconcile", "message": {}}})
    second = conn.recv()["deviceReply"]
    conn.send({"id": i, "result": {"replies": [first, second]}})


def _echo(conn: _ServerConn, frame: dict) -> None:
    conn.send(
        {"id": frame["id"], "result": {"params": frame["params"], "big": "x" * 70000}}
    )


def _refuse(conn: _ServerConn, frame: dict) -> None:
    conn.send(
        {"id": frame["id"], "error": {"code": "needs_rejoin", "message": "fork at 3"}}
    )


@pytest.fixture
def stub() -> t.Iterator[StubWardd]:
    s = StubWardd({"sync": _conversation, "echo": _echo, "refused": _refuse})
    yield s
    s.close()


def test_hello_sends_the_token_and_no_origin(stub: StubWardd) -> None:
    WarddClient("good", stub.url).close()
    assert stub.received[0] == {
        "id": 1,
        "method": "hello",
        "params": {"version": "1.0", "token": "good"},
    }
    # only a browser sends Origin; wardd admits a local process on the token
    assert stub.origins == [None]


def test_a_wrong_token_is_refused_with_its_code(stub: StubWardd) -> None:
    with pytest.raises(WarddError) as e:
        WarddClient("bad", stub.url)
    assert e.value.code == "unauthorised"


def test_wardd_not_running_is_said_plainly() -> None:
    with pytest.raises(WarddError, match="not reachable"):
        WarddClient("good", "ws://127.0.0.1:1")


def test_a_conversation_answers_each_device_call_in_order(stub: StubWardd) -> None:
    seen = []

    def device(name: str, body: dict) -> tuple[str, dict]:
        seen.append(name)
        return f"{name}Ack", {"n": len(seen)}

    with WarddClient("good", stub.url) as client:
        result = client.call("sync", {}, device)
    assert seen == ["WardSync", "WardReconcile"]
    assert result == {
        "replies": [
            {"name": "WardSyncAck", "message": {"n": 1}},
            {"name": "WardReconcileAck", "message": {"n": 2}},
        ]
    }


def test_a_device_that_raises_is_answered_as_a_failure(stub: StubWardd) -> None:
    def device(name: str, body: dict) -> tuple[str, dict]:
        raise exceptions.TrezorFailure(
            messages.Failure(code=messages.FailureType.DataError, message="no")
        )

    with WarddClient("good", stub.url) as client:
        result = client.call("sync", {}, device)
    assert result["replies"][0] == {
        "name": "Failure",
        "message": {"code": "DataError", "message": "no"},
    }


def test_large_frames_and_error_codes(stub: StubWardd) -> None:
    with WarddClient("good", stub.url) as client:
        out = client.call("echo", {"blob": "y" * 300})
        assert len(out["big"]) == 70000 and out["params"] == {"blob": "y" * 300}
        with pytest.raises(WarddError) as e:
            client.call("refused")
        assert e.value.code == "needs_rejoin"


def test_session_device_maps_names_to_messages_and_back() -> None:
    class Session:
        def call(self, msg: protobuf.MessageType) -> protobuf.MessageType:
            assert isinstance(msg, messages.WardFlushQueue) and msg.max_batch == 4
            return messages.WardEntryRequest(entry_key=b"\x11" * 32)

    device = session_device(Session())  # type: ignore [arg-type]
    assert device("WardFlushQueue", {"max_batch": 4}) == (
        "WardEntryRequest",
        {"entry_key": "11" * 32},
    )
    with pytest.raises(ValueError, match="unknown message"):
        device("NotAMessage", {})


def test_the_provider_converts_wardds_answer_and_sends_the_staged_set(
    stub: StubWardd,
) -> None:
    def serve(conn: _ServerConn, frame: dict) -> None:
        conn.send(
            {
                "id": frame["id"],
                "result": {
                    "content": {"encoding": 1, "plaintext": {"content": "aa"}},
                    "proof": ["00" * 34],
                    "staged_seen": frame["params"]["staged"],
                },
            }
        )

    stub.scripts["serveEntry"] = serve
    with WarddClient("good", stub.url) as client:
        answer = WarddProvider(client).with_staged([(b"\x01" * 32, b"\x02" * 32)])(
            b"\x03" * 32
        )
    assert answer.leaf is not None and answer.leaf.identity is None
    assert answer.leaf.content == messages.WardLeafContent(
        encoding=1, plaintext=messages.WardPlaintextLeaf(content=b"\xaa")
    )
    assert answer.proof == [b"\x00" * 34]
    assert stub.received[-1]["params"]["staged"] == [["01" * 32, "02" * 32]]


def test_websocket_refuses_a_non_ws_url() -> None:
    with pytest.raises(ValueError):
        _WebSocket("http://127.0.0.1:1", 1)


# --- against the real wardd -------------------------------------------------------------------

SUITE = os.environ.get("WARDD_SUITE_DIR")
TAG_WM_HEAD = b"WARD WM COMMIT v3"
TAG_WM_INIT = b"WARD WM INIT v3"


def _preimage(
    tag: bytes, ward_id: bytes, fc: int, fr: bytes | None, tc: int, tr: bytes | None
) -> bytes:
    empty = ward_trie.EMPTY_ROOT
    return (
        bytes([len(tag)])
        + tag
        + ward_id
        + fc.to_bytes(4, "big")
        + (fr or empty)
        + tc.to_bytes(4, "big")
        + (tr or empty)
    )


class FakeDevice:
    """Just enough of a device for wardd: genuine signatures, a one-entry queue, no checks of
    its own -- the Rust and TS fakes verify the host; this one exists to exercise the binding.
    """

    def __init__(self) -> None:
        self.k_sig = os.urandom(32)
        self.ward_id = _ed25519.publickey_unsafe(self.k_sig)
        self.counter: int = 0
        self.root: bytes | None = None
        self.head_nonce: bytes = b"\x00" * 32
        self.inflight: int | None = None  # the counter the change in flight would reach
        self.queue: list[tuple[bytes, messages.WardLeafContent]] = []

    def _sign(self, preimage: bytes) -> bytes:
        return _ed25519.signature_unsafe(preimage, self.k_sig, self.ward_id)

    def call(self, msg: protobuf.MessageType, **_: object) -> protobuf.MessageType:
        if isinstance(msg, messages.WardSync):
            pre = _preimage(
                TAG_WM_INIT,
                self.ward_id,
                self.counter,
                self.root,
                self.counter,
                self.root,
            )
            return messages.WardSyncAck(
                nonce=os.urandom(32),
                ward_id=self.ward_id,
                counter=self.counter,
                root=self.root,
                head_init_sig=self._sign(pre + b"\x00" * 32),
            )
        if isinstance(msg, messages.WardIngestAttestation):
            self.pending = msg
            return messages.WardIngestAttestationAck(counter=self.counter)
        if isinstance(msg, messages.WardReconcile):
            assert self.pending.to_counter is not None and self.pending.to_head_nonce
            self.counter, self.root = self.pending.to_counter, self.pending.to_root
            self.head_nonce = self.pending.to_head_nonce
            if self.inflight is not None and self.counter == self.inflight:
                self.queue.pop(0)
            self.inflight = None
            return messages.WardReconcileAck(counter=self.counter, new_root=self.root)
        if isinstance(msg, messages.WardFlushQueue):
            if not self.queue:
                return messages.WardFlushQueueAck(remaining=0)
            return messages.WardEntryRequest(entry_key=self.queue[0][0])
        if isinstance(msg, messages.WardEntryAck):
            # the tree is empty in this scenario, so the new root is the one leaf
            entry_key, content = self.queue[0]
            assert msg.proof == [] and msg.witness_entry_key is None
            root = ward_trie.leaf_hash(
                entry_key, ward_trie.commit_of("address", None, content)
            )
            to = self.counter + 1
            self.inflight = to
            wm_sig = self._sign(
                _preimage(TAG_WM_HEAD, self.ward_id, self.counter, self.root, to, root)
                + self.head_nonce
            )
            return messages.WardFlushQueueAck(
                entry_key=entry_key,
                content=content,
                counter=to,
                auth_commit=os.urandom(32),
                wm_sig=wm_sig,
                remaining=len(self.queue) - 1,
            )
        raise AssertionError(f"unexpected {type(msg).__name__}")


@pytest.fixture
def wardd(tmp_path: Path) -> t.Iterator[str]:
    if not SUITE:
        pytest.skip(
            "set WARDD_SUITE_DIR to the trezor-suite checkout to run against real wardd"
        )
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    (tmp_path / "token").write_text("relay-test")
    log = (tmp_path / "wardd.log").open("w")
    # `node --import tsx`, not the tsx binary: that one spawns a child node, and terminating it
    # would orphan the daemon
    proc = subprocess.Popen(
        [
            "node",
            "--import",
            "tsx",
            "packages/wardd/src/cli.ts",
            "--memory",
            "--port",
            str(port),
            "--data-dir",
            str(tmp_path),
            "--token-file",
            str(tmp_path / "token"),
        ],
        cwd=SUITE,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    url = f"ws://127.0.0.1:{port}"
    for _ in range(100):
        try:
            WarddClient("relay-test", url).close()
            break
        except WarddError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail(f"wardd did not start: {(tmp_path / 'wardd.log').read_text()}")
    yield url
    proc.terminate()
    proc.wait(10)
    log.close()


def test_against_wardd_sync_flush_status(wardd: str) -> None:
    device = FakeDevice()
    device.queue.append(
        (
            os.urandom(32),
            messages.WardLeafContent(
                encoding=1, plaintext=messages.WardPlaintextLeaf(content=b"bc1q")
            ),
        )
    )
    with WarddClient("relay-test", wardd) as client:
        assert open_store(device, client)["counter"] == 0  # type: ignore [arg-type]
        assert sync(device, client) == {"counter": 0, "root": None, "how": "reconcile"}  # type: ignore [arg-type]
        out = flush(device, client)  # type: ignore [arg-type]
        assert out["counter"] == 1 and out["published"] == 1 and out["remaining"] == 0
        assert device.counter == 1 and device.root is not None
        assert out["root"] == device.root.hex()
        assert status(client)["wmCounter"] == 1
