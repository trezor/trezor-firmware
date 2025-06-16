import os

import pytest

from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client

from .connect import prepare_protocol_for_handshake

pytestmark = [pytest.mark.protocol("protocol_v2"), pytest.mark.invalidate_client]


def test_allocate_channel(client: Client) -> None:
    assert isinstance(client.protocol, ProtocolV2Channel)

    nonce = os.urandom(8)

    # Use valid nonce
    client.protocol._send_channel_allocation_request(nonce)
    client.protocol._read_channel_allocation_response(nonce)

    # Expect different nonce
    client.protocol._send_channel_allocation_request(nonce)
    with pytest.raises(Exception, match="Invalid channel allocation response."):
        client.protocol._read_channel_allocation_response(
            expected_nonce=b"\xde\xad\xbe\xef\xde\xad\xbe\xef"
        )
    client.invalidate()


def test_handshake(client: Client) -> None:
    protocol = prepare_protocol_for_handshake(client)

    randomness_static = os.urandom(32)

    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static,
    )
    protocol._send_handshake_init_request()
    protocol._read_ack()
    protocol._read_handshake_init_response()

    protocol._send_handshake_completion_request()
    protocol._read_ack()
    protocol._read_handshake_completion_response()

    # TODO - without pairing, the client is damaged and results in fail of the following test
    # so far no luck in solving it - it should be also tackled in FW, as it causes unexpected FW error
    client.protocol = protocol
    client.do_pairing()
