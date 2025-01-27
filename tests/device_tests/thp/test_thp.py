import os
import typing as t

import pytest
import typing_extensions as tx

from trezorlib.client import ProtocolV2
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.transport.thp import curve25519
from trezorlib.transport.thp.protocol_v2 import _hkdf

if t.TYPE_CHECKING:
    P = tx.ParamSpec("P")

pytestmark = [pytest.mark.protocol("protocol_v2")]


def test_allocate_channel(client: Client) -> None:
    protocol: ProtocolV2 = client.protocol
    nonce = b"\x1A\x2B\x3B\x4A\x5C\x6D\x7E\x8F"

    # Use valid nonce
    protocol._send_channel_allocation_request(nonce)
    protocol._read_channel_allocation_response(nonce)

    # Expect different nonce
    protocol._send_channel_allocation_request(nonce)
    with pytest.raises(Exception, match="Invalid channel allocation response."):
        protocol._read_channel_allocation_response(
            expected_nonce=b"\xDE\xAD\xBE\xEF\xDE\xAD\xBE\xEF"
        )
    client.invalidate()


def test_handshake(client: Client) -> None:
    protocol: ProtocolV2 = client.protocol

    protocol.sync_bit_send = 0
    protocol.sync_bit_receive = 0
    host_ephemeral_privkey = curve25519.get_private_key(os.urandom(32))
    host_ephemeral_pubkey = curve25519.get_public_key(host_ephemeral_privkey)

    protocol._do_channel_allocation()
    protocol._send_handshake_init_request(host_ephemeral_pubkey)
    protocol._read_ack()
    init_response = protocol._read_handshake_init_response()

    trezor_ephemeral_pubkey = init_response[:32]
    encrypted_trezor_static_pubkey = init_response[32:80]
    noise_tag = init_response[80:96]

    # TODO check noise_tag is valid

    ck = protocol._send_handshake_completion_request(
        host_ephemeral_pubkey,
        host_ephemeral_privkey,
        trezor_ephemeral_pubkey,
        encrypted_trezor_static_pubkey,
    )
    protocol._read_ack()
    protocol._read_handshake_completion_response()
    protocol.key_request, protocol.key_response = _hkdf(ck, b"")
    protocol.nonce_request = 0
    protocol.nonce_response = 1

    # TODO - without pairing, the client is damaged and results in fail of the following test
    # so far no luck in solving it - it should be also tackled in FW, as it causes unexpected FW error
    protocol._do_pairing()

    # TODO the following is just to make style checker happy
    assert noise_tag is not None
