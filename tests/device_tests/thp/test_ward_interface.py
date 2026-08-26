import pytest

from trezorlib import messages
from trezorlib.debuglink import TrezorTestContext
from trezorlib.thp.channel import Channel
from trezorlib.transport.udp import UdpTransport

from ...ward_service import MockWardService, ward_transport

Client = TrezorTestContext
pytestmark = [pytest.mark.protocol("thp")]

# NOT A FILE-LEVEL MARKER, on purpose. Most tests here reach the interface through `ward_transport`,
# which skips on a connect build by itself -- and one of them,
# `test_the_existing_interfaces_keep_their_ports`, must run on BOTH builds, since what it guards is
# that appending an interface did not move the ones every existing host pins. Marking the file would
# skip exactly the regression test that matters most to a connect build.


@pytest.mark.ward_transport("service-thp")
def test_the_ward_interface_carries_its_own_channel(client: Client) -> None:
    """A channel on the WARD interface, allocated while the wire interface holds one of its own.

    This is the property the separate interface exists for, and the one that was impossible
    before: buffers were handed out by a single provider that answered once, so whichever
    interface asked second was refused and reported TRANSPORT_BUSY. Two live channels on two
    interfaces is therefore the assertion, not one channel on the new port.
    """
    ward = ward_transport(client)
    try:
        on_wire = Channel.allocate(client.transport)
        on_wire._init_noise()

        on_ward = Channel.allocate(ward)
        on_ward._init_noise()

        # Distinct channels, and both usable -- a refused interface would have failed to allocate
        # rather than returning a second id.
        assert on_wire.channel_id != on_ward.channel_id
    finally:
        ward.close()


@pytest.mark.ward_transport("service-thp")
def test_the_ward_interface_completes_a_handshake(client: Client) -> None:
    """It is a full THP interface, not merely a socket that answers.

    The handshake is what proves the interface is wired through to the THP state machine on the
    device -- its own read loop, write loop and channel state -- rather than just being present in
    the descriptor.
    """
    ward = ward_transport(client)
    try:
        channel = Channel.allocate(ward)
        channel._init_noise()
        channel._send_handshake_init_request(unlock=False)
        channel._read_handshake_init_response()
    finally:
        ward.close()


@pytest.mark.ward_transport("service-thp")
def test_it_answers_while_the_wire_interface_holds_a_channel(client: Client) -> None:
    """A message arriving here is HANDLED, not merely reassembled.

    The session dispatches exactly one channel -- whichever received a packet first -- because a
    wallet host's conversation is the session and the session restarts around it. A wallet channel
    is normally live and holding that slot, so before the service interface had a dispatcher of its
    own a message arriving here was reassembled and then read by nobody: the symptom was a daemon
    that hung, with nothing on the device to indicate anything was wrong.

    So the assertion is only that SOMETHING comes back. Which message it is depends on what the
    interface is willing to serve, and that is a separate question from whether anyone is listening.
    """
    with MockWardService(client) as wardd:
        # The wire interface has a live channel throughout: `client` is connected over it.
        assert wardd.call(messages.GetFeatures(), timeout=10) is not None


def test_the_existing_interfaces_keep_their_ports(client: Client) -> None:
    """Wire and debuglink must be where every existing host already expects them.

    Interface numbers and endpoint addresses are handed out in registration order, and hosts pin
    the ones they know: trezorlib takes wire as interface 0 / endpoint 1 and debug as 1 / endpoint
    2. The WARD interface is appended last for exactly this reason, and this asserts it -- on the
    emulator via the port offsets, which are derived from the same registration order.
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
