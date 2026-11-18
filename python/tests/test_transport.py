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

from __future__ import annotations

import importlib
import struct
from unittest import mock

import pytest
import requests

from trezorlib import mapping, messages, protobuf, protocol_v1
from trezorlib.transport import Timeout, Transport, all_transports
from trezorlib.transport.bridge import BridgeException, BridgeTransport


def _encode(msg: protobuf.MessageType) -> str:
    msg_type, data = mapping.DEFAULT_MAPPING.encode(msg)
    return (struct.pack(protocol_v1.HEADER_FMT, msg_type, len(data)) + data).hex()


class MockBridge:
    """Answers a Cancel with a Failure of the given code. Like Bridge v2, a read
    with nothing pending times out and the aborted request releases the session."""

    def __init__(self, code: messages.FailureType) -> None:
        self.code = code
        self.session: str | None = None
        self.pending: list[str] = []

    def __call__(
        self, path: str, data: str | None = None, timeout: float | None = None
    ) -> mock.Mock:
        action, *_, session = path.split("/")
        if action == "acquire":
            self.session = "1"
            return mock.Mock(json=lambda: {"session": "1"})
        if session != self.session:
            raise BridgeException(path, 400, "session not found")
        if action == "release":
            self.session = None
        if action in ("post", "call"):
            assert data == _encode(messages.Cancel())
            self.pending.append(_encode(messages.Failure(code=self.code)))
        if action in ("read", "call"):
            if not self.pending:
                self.session = None
                raise requests.ReadTimeout
            return mock.Mock(text=self.pending.pop(0))
        return mock.Mock(text="")


def test_disabled_transport():
    assert BridgeTransport.ENABLED
    assert BridgeTransport in all_transports()

    BridgeTransport.ENABLED = False
    assert BridgeTransport not in all_transports()
    # re-enable
    BridgeTransport.ENABLED = True


def test_import_all_transports():
    from trezorlib.transport.bridge import BridgeTransport
    from trezorlib.transport.hid import HidTransport
    from trezorlib.transport.udp import UdpTransport
    from trezorlib.transport.webusb import WebUsbTransport

    assert BridgeTransport
    assert HidTransport
    assert WebUsbTransport
    assert UdpTransport


def test_udp_transport_throttles_packets():
    from trezorlib.transport.udp import UdpTransport

    transport = UdpTransport()
    transport.socket = mock.Mock()
    packet = bytes(64)
    chunk_count = UdpTransport.SEND_WINDOW_MAX_CHUNKS + 1

    with (
        mock.patch(
            "trezorlib.transport.udp.time.monotonic",
            side_effect=[0.0] * chunk_count + [UdpTransport.SEND_WINDOW_SEC],
        ) as monotonic,
        mock.patch("trezorlib.transport.udp.time.sleep") as sleep,
    ):
        for _ in range(chunk_count):
            transport.write_chunk(packet)

    assert transport.socket.sendall.call_count == chunk_count
    assert monotonic.call_count == chunk_count + 1
    sleep.assert_called_once_with(UdpTransport.SEND_WINDOW_SEC)


def test_discard_stale_packets():
    transport = mock.create_autospec(Transport, instance=True)
    transport.read_chunk.side_effect = [b"stale", b"stale", Timeout()]
    Transport._discard_stale_packets(transport)
    assert transport.read_chunk.call_count == 3


@pytest.mark.parametrize("legacy", (False, True))
@pytest.mark.parametrize(
    "code, is_v1",
    (
        (messages.FailureType.ActionCancelled, True),
        (messages.FailureType.InvalidProtocol, False),
    ),
)
def test_probe_over_bridge(legacy: bool, code: messages.FailureType, is_v1: bool):
    # https://github.com/trezor/trezor-firmware/issues/8317
    with mock.patch("trezorlib.transport.bridge.call_bridge", MockBridge(code)):
        transport = BridgeTransport({"path": "1", "session": None}, legacy=legacy)
        with transport:
            assert protocol_v1.probe(transport) is is_v1


def test_transport_dependencies():
    import trezorlib.transport.hid as hid_transport

    with mock.patch.dict("sys.modules", {"hid": None}):
        importlib.reload(hid_transport)
        assert not hid_transport.HidTransport.ENABLED

    with mock.patch.dict("sys.modules", {"hid": mock.Mock()}):
        importlib.reload(hid_transport)
        assert hid_transport.HidTransport.ENABLED
