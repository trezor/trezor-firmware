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

"""What the V1 codec service endpoint does that the THP one does not.

The statements every service build has to satisfy live in the sibling files, which is where they
belong -- binding, syncing and publishing are protocol properties and do not care what carries
them. What is here is the handful of behaviours that only exist because the codec has no channel:
there is nothing to displace, nothing to pin, and one reader that never lets go of the interface.
"""

import struct

import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.transport.udp import UdpTransport

from ...ward_service import MockWardService

# NOT `protocol("v1")` ANY MORE. That marker describes the WALLET transport, and the codec
# service endpoint is no longer tied to it: the service interface speaks codec v1 on every build,
# including one whose wallet interface speaks THP. What these tests need is a codec SERVICE
# endpoint, which is what the marker below asks for.
pytestmark = [
    pytest.mark.ward,
    pytest.mark.models("core"),
    pytest.mark.ward_transport("service-codec"),
]


def test_a_daemon_that_restarts_while_idle_simply_rebinds(client: Client) -> None:
    """No lock-out is possible here, and that is structural rather than fixed.

    Under THP a daemon reconnecting arrives as a new channel on an interface that tracks exactly
    one, so an incumbent that had gone away without saying so used to hold the role until the
    device rebooted -- `InterfaceContext._retire_displaced_channel` is what that cost. The codec
    endpoint has no channel to be an incumbent: the reader owns the interface for the whole life of
    the session and a second announcement is just another message it reads.
    """
    first = MockWardService(client)
    try:
        first.connect()
        assert isinstance(first.open_service(), messages.WardServiceOpenAck)
    finally:
        first.close()

    again = MockWardService(client)
    try:
        again.connect()
        assert isinstance(again.open_service(), messages.WardServiceOpenAck)
    finally:
        again.close()


def test_rebinding_the_same_daemon_is_idempotent(client: Client) -> None:
    """Repeated announcements are answered, not refused.

    Under THP a repeat open on the bound channel is never even dispatched, because binding hands
    the channel to the device. Here the reader keeps reading whenever no RPC is in flight, so the
    message does arrive -- and the right answer is to say yes again. There is no channel to strand
    and no identity to re-check, so refusing would only give a restarting daemon a state to get out
    of.
    """
    with MockWardService(client) as wardd:
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)


def test_an_unbound_endpoint_refuses_everything_but_the_bootstrap(client: Client) -> None:
    """The receive boundary, and where it is enforced.

    On a codec build `WardServiceOpen` is not registered with the workflow dispatcher at all: the
    interface's own reader recognises it and calls the handler directly. Anything else is refused
    before a dispatcher or a workflow sees it, which is the point -- going through
    `handle_single_message` would mean `workflow.spawn`, and a daemon must not be able to close a
    live wallet workflow by sending a message.
    """
    with MockWardService(client) as wardd:
        for msg in (
            messages.GetFeatures(),
            messages.Initialize(),
            messages.Cancel(),
            messages.EndSession(),
        ):
            resp = wardd.call(msg)
            assert isinstance(
                resp, messages.Failure
            ), f"{type(msg).__name__} was accepted on an unbound service endpoint"
            assert resp.message == "not accepted on the WARD service channel"


def test_a_refusal_does_not_stop_the_endpoint_serving(client: Client) -> None:
    """The reader must survive what it refuses.

    A single reader owning the interface is what makes the inversion work, so an exception path
    that ended the loop would turn one malformed message into a service that is gone until the next
    MicroPython session restart -- and the daemon would have no way to tell.
    """
    with MockWardService(client) as wardd:
        assert isinstance(wardd.call(messages.GetFeatures()), messages.Failure)
        assert isinstance(
            wardd.call(messages.WardServiceOpen(protocol_version=99)), messages.Failure
        )
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)


def test_a_half_sent_message_does_not_take_the_endpoint_with_it(client: Client) -> None:
    """A header is a promise of more, and a peer that breaks it must not cost the interface.

    EVERY OTHER REFUSAL IS DEFERRED UNTIL THE MESSAGE HAS BEEN DRAINED, so that the wire is left at
    a frame boundary and the next read starts on a real header. That is right for a message that
    arrives, and it is exactly what strands the reader on one that does not: it waited inside the
    frame for continuation reports that were never coming, and every later message queued behind
    one it would never finish.

    Worse when it happens mid-RPC, which is not what this test can reach but is what the bound
    exists for: the frame took the shared receive buffer before the loop began, and on a THP build
    that buffer is the wallet's too. The unit tests assert the lease directly; this asserts the
    part only real firmware can show -- that the interface comes back.
    """
    with MockWardService(client) as wardd:
        # A header promising far more than an unbound endpoint will ever accept, and then silence.
        header = struct.pack(
            ">3sHL", b"?##", messages.WardServiceOpen.MESSAGE_WIRE_TYPE, 4096
        )
        transport = wardd.service.transport
        assert isinstance(transport, UdpTransport)
        transport.write_chunk(header + b"\x00" * (UdpTransport.CHUNK_SIZE - len(header)))

        # The frame is given up on, and the daemon is told so rather than left guessing.
        abandoned = wardd.service.read(timeout=5)
        assert isinstance(abandoned, messages.Failure), abandoned

        # And the endpoint is still there to be bound, which is the whole point.
        assert isinstance(wardd.open_service(), messages.WardServiceOpenAck)


def test_the_existing_interfaces_keep_their_ports(client: Client) -> None:
    """Wire and debuglink must be where every existing host already expects them.

    Interface numbers and endpoint addresses are handed out in registration order, and hosts pin
    the ones they know: trezorlib takes wire as interface 0 / endpoint 1 and debug as 1 / endpoint
    2. The WARD interface is appended last for exactly this reason, and this asserts it -- on the
    emulator via the port offsets, which are derived from the same registration order.

    Duplicated from the THP file rather than shared, because it guards the thing a Safe 5 owner
    would notice first if appending an interface went wrong, and a file the codec build skips
    cannot guard it.
    """
    transport = client.transport
    if not isinstance(transport, UdpTransport):
        pytest.skip("port layout is an emulator concept")

    host, port = transport.device
    for offset, what in ((0, "wire"), (1, "debuglink")):
        probe = UdpTransport(f"{host}:{port + offset}")
        probe.open()
        try:
            assert probe.is_ready(), f"{what} moved off its port"
        finally:
            probe.close()
