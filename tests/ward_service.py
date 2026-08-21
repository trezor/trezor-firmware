# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

"""A minimal stand-in for `wardd`: enough to bind the service channel and be talked to.

DELIBERATELY NOT `trezorlib.thp.client.TrezorClientThp`. That client assumes it drives the
conversation -- it opens sessions with `ThpCreateNewSession`, which derives a wallet seed the
service must not have, and it reads only in reply to something it sent. The service channel is the
other way round: the daemon speaks once, to announce itself, and answers from then on.

ONE OWNER OF THE CHANNEL, ALWAYS. trezorlib's THP `Channel` is synchronous and stateful -- sync
bits, Noise state, transport reads -- so a reader in one thread plus a writer in another would have
one consume the frame the other is waiting for. With the device as sole initiator there is exactly
one loop and no second thread, which is why this file has no locking in it.

The responder loop and the real client belong in `trezorlib`; this exists so the device side can be
tested before the daemon does.
"""

from __future__ import annotations

import struct
import typing as t

import pytest

from trezorlib import protobuf
from trezorlib.thp.channel import Channel
from trezorlib.transport.udp import UdpTransport

if t.TYPE_CHECKING:
    from trezorlib.debuglink import TrezorTestContext

# Offsets 4 and 5 are BLE's and 6 is the Tropic model's -- see `trezorlib._internal.emulator` and
# `core/embed/io/usb/usb_config.c`, which must agree.
WARD_PORT_OFFSET = 7

# `trezorlib.thp.client`'s application header: session id, message type.
_HEADER = ">BH"
_HEADER_LEN = struct.calcsize(_HEADER)


def ward_transport(client: TrezorTestContext) -> UdpTransport:
    """A transport for the WARD interface, or skip if this build has none.

    Skipped rather than failed because the interface is a BUILD OPTION: a firmware serves WARD
    either over the ordinary connection or over its own channel, never both, so a connect build
    legitimately has nothing listening here. Probed rather than asked, the device having no way to
    report it.
    """
    transport = client.transport
    if not isinstance(transport, UdpTransport):
        pytest.skip("the WARD interface is only reachable over UDP on the emulator")

    host, port = transport.device
    ward = UdpTransport(f"{host}:{port + WARD_PORT_OFFSET}")
    try:
        ward.open()
    except Exception:
        pytest.skip("this build has no WARD service interface")
    if not ward.is_ready():
        ward.close()
        pytest.skip("this build has no WARD service interface")
    return ward


class MockWardService:
    """The daemon's side of the channel: open it, announce, then answer what the device asks."""

    def __init__(self, client: TrezorTestContext, session_id: int = 0) -> None:
        self._client = client
        self._mapping = client.client.mapping
        self.session_id = session_id
        self.transport = ward_transport(client)
        self.channel: Channel | None = None
        # The key the device pins. Recorded so a test can reconnect AS THE SAME daemon, which is
        # what separates "a stranger" from "the same daemon twice".
        self.host_static_privkey: bytes | None = None

    # --- lifecycle ---------------------------------------------------------------------

    def connect(self, host_static_privkey: bytes | None = None) -> Channel:
        """Allocate a channel, handshake, and pair it.

        PAIRING IS NOT OPTIONAL. A handshaked-but-unpaired channel sits in the pairing state, where
        every application message is refused as unrecognised -- so without this the device's own
        checks would never be reached and a test asserting "refused" would pass for the wrong
        reason.

        `host_static_privkey` makes the daemon's identity choosable: the key is what the device
        pins, and a distinct one is how "a different daemon" is expressed. Left unset it is random
        per channel, which is what a real daemon that has lost its key would look like.
        """
        channel = Channel.allocate(self.transport)
        channel._init_noise(static_privkey=host_static_privkey)
        self.host_static_privkey = channel.host_static_privkey
        channel.open([])
        self.channel = channel
        self._pair(channel)
        return channel

    def _pair(self, channel: Channel) -> None:
        """Pair via SkipPairing, borrowing the host's client for the exchange.

        `PairingController` drives the conversation through `client.channel`, so the client is
        pointed at this channel and put back afterwards -- the wallet channel must keep working,
        and these tests exist precisely to check the two do not disturb each other.
        """
        from trezorlib.thp.pairing import PairingController

        client = self._client.client
        saved_channel = client.channel
        saved_pairing = client.pairing
        saved_interact = client._interact_ctx
        try:
            client.channel = channel
            client._interact_ctx = client._interact()
            pairing = PairingController(client)
            client.pairing = pairing
            pairing.skip()
        finally:
            client.channel = saved_channel
            client.pairing = saved_pairing
            client._interact_ctx = saved_interact

    def close(self) -> None:
        if self.channel is not None:
            self.channel.close()
            self.channel = None
        self.transport.close()

    def __enter__(self) -> MockWardService:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- the application layer ---------------------------------------------------------

    def send(self, msg: protobuf.MessageType) -> None:
        assert self.channel is not None
        msg_type, msg_bytes = self._mapping.encode(msg)
        self.channel.write_chunk(
            struct.pack(_HEADER, self.session_id, msg_type) + msg_bytes
        )

    def receive(self, timeout: float | None = None) -> protobuf.MessageType:
        assert self.channel is not None
        raw = self.channel.read_chunk(timeout=timeout)
        session_id, msg_type = struct.unpack(_HEADER, raw[:_HEADER_LEN])
        assert session_id == self.session_id, "reply arrived for another session"
        return self._mapping.decode(msg_type, raw[_HEADER_LEN:])

    def call(
        self, msg: protobuf.MessageType, timeout: float | None = None
    ) -> protobuf.MessageType:
        self.send(msg)
        return self.receive(timeout=timeout)
