import pytest

from trezorlib.debuglink import TrezorTestContext
from trezorlib.thp.channel import Channel
from trezorlib.transport.udp import UdpTransport

Client = TrezorTestContext
pytestmark = [pytest.mark.protocol("thp")]

# Offsets 4 and 5 are BLE's and 6 is the Tropic model's -- see
# `trezorlib._internal.emulator` and `core/embed/io/usb/usb_config.c`, which must agree.
WARD_PORT_OFFSET = 7


def _ward_transport(client: Client) -> UdpTransport:
    """A transport for the WARD service interface, or skip if this build has no such interface.

    Skipped rather than failed because the interface is a BUILD OPTION: WARD is served either over
    the ordinary connection or over its own channel, never both, so a connect build legitimately
    has nothing listening here. Detected by probing rather than by asking the device, which has no
    way to report it.
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


def test_the_ward_interface_carries_its_own_channel(client: Client) -> None:
    """A channel on the WARD interface, allocated while the wire interface holds one of its own.

    This is the property the separate interface exists for, and the one that was impossible
    before: buffers were handed out by a single provider that answered once, so whichever
    interface asked second was refused and reported TRANSPORT_BUSY. Two live channels on two
    interfaces is therefore the assertion, not one channel on the new port.
    """
    ward = _ward_transport(client)
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


def test_the_ward_interface_completes_a_handshake(client: Client) -> None:
    """It is a full THP interface, not merely a socket that answers.

    The handshake is what proves the interface is wired through to the THP state machine on the
    device -- its own read loop, write loop and channel state -- rather than just being present in
    the descriptor.
    """
    ward = _ward_transport(client)
    try:
        channel = Channel.allocate(ward)
        channel._init_noise()
        channel._send_handshake_init_request(unlock=False)
        channel._read_handshake_init_response()
    finally:
        ward.close()


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
