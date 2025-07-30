import os

import pytest

from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client

from .connect import deterministic_urandom  # noqa: F401
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


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
def test_handshake_hash(client: Client, deterministic_urandom) -> None:  # noqa:F811
    protocol = prepare_protocol_for_handshake(client)

    randomness_static = os.urandom(32)
    randomness_ephemeral = os.urandom(64)[-32:]
    protocol._do_channel_allocation()
    protocol._init_noise(
        randomness_static=randomness_static, randomness_ephemeral=randomness_ephemeral
    )

    protocol._send_handshake_init_request()

    protocol._read_ack()
    protocol._read_handshake_init_response()

    protocol._send_handshake_completion_request()
    protocol._read_ack()
    protocol._read_handshake_completion_response()
    assert (
        protocol.handshake_hash.hex()
        == "e7f6119408d6767cc7a4710bb2a6e4732998409fe69014e8b1808f789b5fcb7c"
    )
    # assert (
    #     protocol.handshake_hash.hex()
    #     == "9ae9bc5de3fd5e2a45158857573e095a4965f2fd628e95affd2e2c1ee2c387dc"
    # )
    # TODO - without pairing, the client is damaged and results in fail of the following test
    # so far no luck in solving it - it should be also tackled in FW, as it causes unexpected FW error
    client.protocol = protocol
    client.do_pairing()
