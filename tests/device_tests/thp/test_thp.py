import os
import random
import typing as t
from hashlib import sha256

import pytest
import typing_extensions as tx

from trezorlib import protobuf
from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    ButtonAck,
    ButtonRequest,
    ThpCodeEntryChallenge,
    ThpCodeEntryCommitment,
    ThpCodeEntryCpaceHostTag,
    ThpCodeEntryCpaceTrezor,
    ThpCodeEntrySecret,
    ThpCredentialRequest,
    ThpCredentialResponse,
    ThpEndRequest,
    ThpEndResponse,
    ThpNfcTagHost,
    ThpNfcTagTrezor,
    ThpPairingMethod,
    ThpPairingPreparationsFinished,
    ThpPairingRequest,
    ThpPairingRequestApproved,
    ThpQrCodeSecret,
    ThpQrCodeTag,
    ThpSelectMethod,
)
from trezorlib.transport.thp import curve25519
from trezorlib.transport.thp.cpace import Cpace
from trezorlib.transport.thp.protocol_v2 import _hkdf

if t.TYPE_CHECKING:
    P = tx.ParamSpec("P")

MT = t.TypeVar("MT", bound=protobuf.MessageType)

pytestmark = [pytest.mark.protocol("protocol_v2")]


def _prepare_protocol(client: Client) -> ProtocolV2Channel:
    protocol = client.protocol
    assert isinstance(protocol, ProtocolV2Channel)
    protocol._reset_sync_bits()
    return protocol


def _prepare_protocol_for_pairing(client: Client) -> ProtocolV2Channel:
    protocol = _prepare_protocol(client)
    protocol._do_channel_allocation()
    protocol._do_handshake()
    return protocol


def _handle_pairing_request(client: Client, protocol: ProtocolV2Channel) -> None:
    protocol._send_message(ThpPairingRequest())
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "pairing_request"

    protocol._send_message(ButtonAck())

    client.debug.press_yes()

    protocol._read_message(ThpPairingRequestApproved)


def test_allocate_channel(client: Client) -> None:
    protocol = _prepare_protocol(client)

    nonce = random.randbytes(8)

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
    protocol = _prepare_protocol(client)

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
    protocol = _prepare_protocol_for_pairing(client)
    _handle_pairing_request(client, protocol)
    protocol._send_message(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.QrCode)
    )
    protocol._read_message(ThpPairingPreparationsFinished)

    # QR Code shown
    protocol._read_message(ButtonRequest)
    protocol._send_message(ButtonAck())

    # Read code from "Trezor's display" using debuglink

    pairing_info = client.debug.pairing_info(
        thp_channel_id=protocol.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_qr_code

    # Compute tag for response
    sha_ctx = sha256(protocol.handshake_hash)
    sha_ctx.update(code)
    tag = sha_ctx.digest()

    protocol._send_message(ThpQrCodeTag(tag=tag))

    secret_msg = protocol._read_message(ThpQrCodeSecret)

    # Check that the `code` was derived from the revealed secret
    sha_ctx = sha256(ThpPairingMethod.QrCode.to_bytes(1, "big"))
    sha_ctx.update(protocol.handshake_hash)
    sha_ctx.update(secret_msg.secret)
    computed_code = sha_ctx.digest()[:16]
    assert code == computed_code

    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    protocol._has_valid_channel = True


def test_pairing_code_entry(client: Client) -> None:
    protocol = _prepare_protocol_for_pairing(client)

    _handle_pairing_request(client, protocol)

    protocol._send_message(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.CodeEntry)
    )

    commitment_msg = protocol._read_message(ThpCodeEntryCommitment)
    commitment = commitment_msg.commitment

    challenge = random.randbytes(16)
    protocol._send_message(ThpCodeEntryChallenge(challenge=challenge))

    cpace_trezor = protocol._read_message(ThpCodeEntryCpaceTrezor)
    cpace_trezor_public_key = cpace_trezor.cpace_trezor_public_key

    # Code Entry code shown
    protocol._read_message(ButtonRequest)
    protocol._send_message(ButtonAck())

    pairing_info = client.debug.pairing_info(
        thp_channel_id=protocol.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_entry_code

    cpace = Cpace(handshake_hash=protocol.handshake_hash)
    cpace.random_bytes = random.randbytes
    cpace.generate_keys_and_secret(code.to_bytes(6, "big"), cpace_trezor_public_key)
    sha_ctx = sha256(cpace.shared_secret)
    tag = sha_ctx.digest()

    protocol._send_message(
        ThpCodeEntryCpaceHostTag(
            cpace_host_public_key=cpace.host_public_key,
            tag=tag,
        )
    )

    secret_msg = protocol._read_message(ThpCodeEntrySecret)

    # Check `commitment` and `code`
    sha_ctx = sha256(secret_msg.secret)
    computed_commitment = sha_ctx.digest()
    assert commitment == computed_commitment

    sha_ctx = sha256(ThpPairingMethod.CodeEntry.to_bytes(1, "big"))
    sha_ctx.update(protocol.handshake_hash)
    sha_ctx.update(secret_msg.secret)
    sha_ctx.update(challenge)
    code_hash = sha_ctx.digest()
    computed_code = int.from_bytes(code_hash, "big") % 1000000
    assert code == computed_code

    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    protocol._has_valid_channel = True


def test_pairing_nfc(client: Client) -> None:
    protocol = _prepare_protocol_for_pairing(client)

    _nfc_pairing(client, protocol)

    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)
    protocol._has_valid_channel = True


def _nfc_pairing(client: Client, protocol: ProtocolV2Channel):

    _handle_pairing_request(client, protocol)

    protocol._send_message(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.NFC)
    )
    protocol._read_message(ThpPairingPreparationsFinished)

    # NFC screen shown
    protocol._read_message(ButtonRequest)
    protocol._send_message(ButtonAck())

    nfc_secret_host = random.randbytes(16)
    # Read `nfc_secret` and `handshake_hash` from Trezor using debuglink
    pairing_info = client.debug.pairing_info(
        thp_channel_id=protocol.channel_id.to_bytes(2, "big"),
        handshake_hash=protocol.handshake_hash,
        nfc_secret_host=nfc_secret_host,
    )
    handshake_hash_trezor = pairing_info.handshake_hash
    nfc_secret_trezor = pairing_info.nfc_secret_trezor

    assert handshake_hash_trezor[:16] == protocol.handshake_hash[:16]

    # Compute tag for response
    sha_ctx = sha256(ThpPairingMethod.NFC.to_bytes(1, "big"))
    sha_ctx.update(protocol.handshake_hash)
    sha_ctx.update(nfc_secret_trezor)
    tag_host = sha_ctx.digest()

    protocol._send_message(ThpNfcTagHost(tag=tag_host))

    tag_trezor_msg = protocol._read_message(ThpNfcTagTrezor)

    # Check that the `code` was derived from the revealed secret
    sha_ctx = sha256(ThpPairingMethod.NFC.to_bytes(1, "big"))
    sha_ctx.update(protocol.handshake_hash)
    sha_ctx.update(nfc_secret_host)
    computed_tag = sha_ctx.digest()
    assert tag_trezor_msg.tag == computed_tag


def test_credential_phase(client: Client):
    protocol = _prepare_protocol_for_pairing(client)
    _nfc_pairing(client, protocol)

    # Request credential with confirmation after pairing
    host_static_privkey = curve25519.get_private_key(os.urandom(32))
    host_static_pubkey = curve25519.get_public_key(host_static_privkey)
    protocol._send_message(
        ThpCredentialRequest(host_static_pubkey=host_static_pubkey, autoconnect=False)
    )
    credential_response = protocol._read_message(ThpCredentialResponse)

    assert credential_response.credential is not None
    credential = credential_response.credential
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    # Connect using credential with confirmation
    protocol = _prepare_protocol(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential, host_static_privkey)
    protocol._send_message(ThpEndRequest())
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "connection_request"
    protocol._send_message(ButtonAck())
    client.debug.press_yes()
    protocol._read_message(ThpEndResponse)

    # Connect using credential with confirmation and ask for autoconnect credential
    protocol = _prepare_protocol(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential, host_static_privkey)
    protocol._send_message(
        ThpCredentialRequest(host_static_pubkey=host_static_pubkey, autoconnect=True)
    )
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "connection_request"
    protocol._send_message(ButtonAck())
    client.debug.press_yes()
    credential_response_2 = protocol._read_message(ThpCredentialResponse)
    assert credential_response_2.credential is not None
    credential_auto = credential_response_2.credential
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    # Connect using autoconnect credential
    protocol = _prepare_protocol(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential_auto, host_static_privkey)
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)
