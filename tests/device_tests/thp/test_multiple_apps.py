import os
import time

import pytest

from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client

pytestmark = [pytest.mark.protocol("protocol_v2")]


def test_multiple_hosts(client: Client) -> None:
    assert isinstance(client.protocol, ProtocolV2Channel)
    protocol_1 = client.protocol
    protocol_2 = ProtocolV2Channel(protocol_1.transport, protocol_1.mapping)
    protocol_2._reset_sync_bits()

    nonce_1 = os.urandom(8)
    nonce_2 = os.urandom(8)
    if nonce_1 == nonce_2:
        nonce_2 = (int.from_bytes(nonce_1) + 1).to_bytes(8, "big")
    protocol_1._send_channel_allocation_request(nonce_1)
    protocol_1.channel_id, protocol_1.device_properties = (
        protocol_1._read_channel_allocation_response(nonce_1)
    )
    protocol_2._send_channel_allocation_request(nonce_2)
    protocol_2.channel_id, protocol_2.device_properties = (
        protocol_2._read_channel_allocation_response(nonce_2)
    )

    protocol_1._init_noise()
    protocol_2._init_noise()

    protocol_1._send_handshake_init_request()
    protocol_1._read_ack()
    protocol_1._read_handshake_init_response()

    protocol_2._send_handshake_init_request()

    with pytest.raises(Exception) as e:
        protocol_2._read_ack()
    assert e.value.args[0] == "Received ThpError: TRANSPORT BUSY"

    time.sleep(0.2)  # To pass LOCK_TIME
    protocol_2._init_noise()
    protocol_2._send_handshake_init_request()
    protocol_2._read_ack()
    protocol_2._read_handshake_init_response()

    protocol_2._send_handshake_completion_request()
    protocol_2._read_ack()
    protocol_2._read_handshake_completion_response()

    protocol_2._do_pairing(helper_debug=client.debug)

    protocol_1._send_handshake_completion_request()
    protocol_1._read_ack()

    with pytest.raises(Exception) as e:
        protocol_1._read_handshake_completion_response()
    assert e.value.args[0] == "Received ThpError: UNALLOCATED CHANNEL"

    # TODO - test ACK fallback, test standard encrypted message fallback
