import pytest

from trezorlib import exceptions
from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client

pytestmark = [pytest.mark.protocol("protocol_v2"), pytest.mark.invalidate_client]


def _new_channel(client) -> ProtocolV2Channel:
    channel = ProtocolV2Channel(
        transport=client.transport,
        mapping=client.mapping,
        credential=None,
        prepare_channel_without_pairing=False,
    )
    channel._do_channel_allocation()
    channel._init_noise()
    return channel


def test_concurrent_handshakes(client: Client) -> None:
    protocol_1 = _new_channel(client)
    protocol_2 = _new_channel(client)

    # The first host starts handshake
    protocol_1._send_handshake_init_request()
    protocol_1._read_ack()
    protocol_1._read_handshake_init_response()

    # The second host starts handshake
    protocol_2._send_handshake_init_request()

    # The second host should not be able to interrupt the first host's handshake immediately
    with pytest.raises(exceptions.TransportBusy):
        protocol_2._read_ack()

    # The first host can complete handshake and pairing
    protocol_1._send_handshake_completion_request()
    protocol_1._read_ack()
    protocol_1._read_handshake_completion_response()
    client.protocol = protocol_1
    client.do_pairing()

    # Now the second handshake and pairing can be done
    protocol_2._do_handshake()
    client.protocol = protocol_2
    client.do_pairing()
