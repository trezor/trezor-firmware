import hashlib
import os
import typing as t

import pytest
import typing_extensions as tx

from trezorlib.client import ProtocolV2
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    ButtonAck,
    ButtonRequest,
    ThpCodeEntryChallenge,
    ThpCodeEntryCommitment,
    ThpCodeEntryCpaceTrezor,
    ThpEndRequest,
    ThpEndResponse,
    ThpPairingMethod,
    ThpPairingPreparationsFinished,
    ThpPairingRequest,
    ThpPairingRequestApproved,
    ThpQrCodeSecret,
    ThpQrCodeTag,
    ThpSelectMethod,
)
from trezorlib.transport.thp import curve25519
from trezorlib.transport.thp.protocol_v2 import MANAGEMENT_SESSION_ID, _hkdf

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
    protocol._do_pairing(client.debug)

    # TODO the following is just to make style checker happy
    assert noise_tag is not None


def test_pairing_qr_code(client: Client) -> None:
    protocol: ProtocolV2 = client.protocol
    protocol.sync_bit_send = 0
    protocol.sync_bit_receive = 0

    # Generate ephemeral keys
    host_ephemeral_privkey = curve25519.get_private_key(os.urandom(32))
    host_ephemeral_pubkey = curve25519.get_public_key(host_ephemeral_privkey)

    protocol._do_channel_allocation()

    protocol._do_handshake(host_ephemeral_privkey, host_ephemeral_pubkey)

    # Send StartPairingReqest message
    message = ThpPairingRequest()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)

    # Read ACK
    protocol._read_ack()

    # Read button request
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ButtonRequest)

    # Send button ACK
    message = ButtonAck()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    protocol._read_ack()

    client.debug.press_yes()

    # Read PairingRequestApproved
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)

    assert isinstance(maaa, ThpPairingRequestApproved)

    message = ThpSelectMethod(selected_pairing_method=ThpPairingMethod.QrCode)
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    # Read ACK
    protocol._read_ack()

    # Read ThpPairingPreparationsFinished
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpPairingPreparationsFinished)

    # QR Code shown
    # Read button request
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ButtonRequest)

    # Send button ACK
    message = ButtonAck()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    protocol._read_ack()

    state = client.debug.state(thp_channel_id=protocol.channel_id.to_bytes(2, "big"))

    sha_ctx = hashlib.sha256(protocol.handshake_hash)
    sha_ctx.update(state.thp_pairing_code_qr_code)
    tag = sha_ctx.digest()

    message_type, message_data = protocol.mapping.encode(ThpQrCodeTag(tag=tag))
    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)

    protocol._read_ack()

    # Read ThpQrCodeSecret
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpQrCodeSecret)

    message = ThpEndRequest()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    # Read ACK
    protocol._read_ack()

    # Read ThpEndResponse
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpEndResponse)

    protocol._has_valid_channel = True


@pytest.mark.skip("Cpace is not implemented yet")
def test_pairing_code_entry(client: Client) -> None:
    protocol: ProtocolV2 = client.protocol
    protocol.sync_bit_send = 0
    protocol.sync_bit_receive = 0

    # Generate ephemeral keys
    host_ephemeral_privkey = curve25519.get_private_key(os.urandom(32))
    host_ephemeral_pubkey = curve25519.get_public_key(host_ephemeral_privkey)

    protocol._do_channel_allocation()

    protocol._do_handshake(host_ephemeral_privkey, host_ephemeral_pubkey)

    # Send StartPairingReqest message
    message = ThpPairingRequest()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)

    # Read ACK
    protocol._read_ack()

    # Read button request
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ButtonRequest)

    # Send button ACK
    message = ButtonAck()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    protocol._read_ack()

    client.debug.press_yes()

    # Read PairingRequestApproved
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)

    assert isinstance(maaa, ThpPairingRequestApproved)

    message = ThpSelectMethod(selected_pairing_method=ThpPairingMethod.CodeEntry)
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    # Read ACK
    protocol._read_ack()

    # Read ThpCodeEntryCommitment
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpCodeEntryCommitment)

    challenge = b"\x00\x11\x22\x33\x44\x55\x66\x77\x88\x99\xAA\xBB\xCC\xDD\xEE\xFF"
    message = ThpCodeEntryChallenge(challenge=challenge)
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    # Read ACK
    protocol._read_ack()

    # Read ThpCodeEntryCpaceTrezor
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpCodeEntryCpaceTrezor)

    _ = maaa.cpace_trezor_public_key

    # Code Entry code shown
    # Read button request
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ButtonRequest)

    # Send button ACK
    message = ButtonAck()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    protocol._read_ack()

    state = client.debug.state(thp_channel_id=protocol.channel_id.to_bytes(2, "big"))

    sha_ctx = hashlib.sha256(protocol.handshake_hash)
    sha_ctx.update(state.thp_pairing_code_entry_code)
    tag = sha_ctx.digest()

    message_type, message_data = protocol.mapping.encode(ThpQrCodeTag(tag=tag))
    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)

    protocol._read_ack()

    # Read ThpQrCodeSecret
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpQrCodeSecret)

    message = ThpEndRequest()
    message_type, message_data = protocol.mapping.encode(message)

    protocol._encrypt_and_write(MANAGEMENT_SESSION_ID, message_type, message_data)
    # Read ACK
    protocol._read_ack()

    # Read ThpEndResponse
    _, msg_type, msg_data = protocol.read_and_decrypt()
    maaa = protocol.mapping.decode(msg_type, msg_data)
    assert isinstance(maaa, ThpEndResponse)

    protocol._has_valid_channel = True
