import os
import time
import typing as t
from hashlib import sha256

import pytest
import typing_extensions as tx

from tests.common import get_test_address
from trezorlib import exceptions, protobuf
from trezorlib.client import ProtocolV2Channel
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import (
    ButtonAck,
    ButtonRequest,
    Cancel,
    Failure,
    FailureType,
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
    ThpQrCodeSecret,
    ThpQrCodeTag,
    ThpSelectMethod,
)
from trezorlib.transport.thp import curve25519
from trezorlib.transport.thp.cpace import Cpace

from .connect import (
    get_encrypted_transport_protocol,
    handle_pairing_request,
    prepare_protocol_for_handshake,
    prepare_protocol_for_pairing,
)

if t.TYPE_CHECKING:
    P = tx.ParamSpec("P")

MT = t.TypeVar("MT", bound=protobuf.MessageType)

pytestmark = [pytest.mark.protocol("protocol_v2")]


def test_pairing_qr_code(client: Client) -> None:
    protocol = prepare_protocol_for_pairing(client)
    handle_pairing_request(client, protocol, "TestTrezor QrCode")
    protocol._send_message(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.QrCode)
    )
    protocol._read_message(ThpPairingPreparationsFinished)

    # QR Code shown

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
    protocol = prepare_protocol_for_pairing(client)

    handle_pairing_request(client, protocol, "TestTrezor CodeEntry")

    protocol._send_message(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.CodeEntry)
    )

    commitment_msg = protocol._read_message(ThpCodeEntryCommitment)
    commitment = commitment_msg.commitment

    challenge = os.urandom(16)
    protocol._send_message(ThpCodeEntryChallenge(challenge=challenge))

    cpace_trezor = protocol._read_message(ThpCodeEntryCpaceTrezor)
    cpace_trezor_public_key = cpace_trezor.cpace_trezor_public_key

    # Code Entry code shown

    pairing_info = client.debug.pairing_info(
        thp_channel_id=protocol.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_entry_code

    cpace = Cpace(handshake_hash=protocol.handshake_hash)
    cpace.random_bytes = os.urandom
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


def test_pairing_cancel_1(client: Client) -> None:
    protocol = prepare_protocol_for_pairing(client)

    protocol._send_message(ThpPairingRequest(host_name="TestTrezor Cancel 1"))
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "thp_pairing_request"

    protocol._send_message(ButtonAck())
    time.sleep(1)
    protocol._send_message(Cancel())

    resp = protocol._read_message(Failure)
    assert resp.code == FailureType.ActionCancelled


def test_pairing_cancel_2(client: Client) -> None:
    protocol = prepare_protocol_for_pairing(client)

    protocol._send_message(ThpPairingRequest(host_name="TestTrezor Cancel 2"))
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "thp_pairing_request"

    protocol._send_message(ButtonAck())
    client.debug.press_no()
    resp = protocol._read_message(Failure)
    assert resp.code == FailureType.ActionCancelled


def test_pairing_nfc(client: Client) -> None:
    protocol = prepare_protocol_for_pairing(client)

    _nfc_pairing(client, protocol)

    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)
    protocol._has_valid_channel = True


def _nfc_pairing(client: Client, protocol: ProtocolV2Channel) -> None:

    handle_pairing_request(client, protocol, "TestTrezor NfcPairing")

    protocol._send_message(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.NFC)
    )
    protocol._read_message(ThpPairingPreparationsFinished)

    # NFC screen shown

    nfc_secret_host = os.urandom(16)
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


def test_credential_phase(client: Client) -> None:
    protocol = prepare_protocol_for_pairing(client)
    _nfc_pairing(client, protocol)

    # Request credential with confirmation after pairing
    randomness_static = os.urandom(32)
    host_static_privkey = curve25519.get_private_key(randomness_static)
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
    protocol = prepare_protocol_for_handshake(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential, randomness_static)
    protocol._send_message(ThpEndRequest())
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "thp_connection_request"
    protocol._send_message(ButtonAck())
    client.debug.press_yes()
    protocol._read_message(ThpEndResponse)

    # Delete channel from the device by sending badly encrypted message
    # This is done to prevent channel replacement and trigerring of autoconnect false -> true
    protocol._noise.noise_protocol.cipher_state_encrypt.n = 250

    protocol._send_message(ButtonAck())
    with pytest.raises(Exception) as e:
        protocol.read(1)
    assert e.value.args[0] == "Received ThpError: DECRYPTION FAILED"

    # Connect using credential with confirmation and ask for autoconnect credential.
    protocol = prepare_protocol_for_handshake(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential, randomness_static)
    protocol._send_message(
        ThpCredentialRequest(host_static_pubkey=host_static_pubkey, autoconnect=True)
    )
    # Connection confirmation dialog is shown. (Channel replacement is not triggered.)
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "thp_connection_request"
    protocol._send_message(ButtonAck())
    client.debug.press_yes()
    # Autoconnect issuance confirmation dialog is shown.
    button_req = protocol._read_message(ButtonRequest)
    assert button_req.name == "autoconnect_credential_request"
    protocol._send_message(ButtonAck())
    client.debug.press_yes()
    # Autoconnect credential is received
    credential_response_2 = protocol._read_message(ThpCredentialResponse)
    assert credential_response_2.credential is not None
    credential_auto = credential_response_2.credential
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    # Connect using credential with confirmation
    protocol = prepare_protocol_for_handshake(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential, randomness_static)
    # Confirmation dialog is not shown as channel in ENCRYPTED TRANSPORT state with the same
    # host static public key is still available in Trezor's cache. (Channel replacement is triggered.)
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    # Connect using autoconnect credential
    protocol = prepare_protocol_for_handshake(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential_auto, randomness_static)
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)

    # Delete channel from the device by sending badly encrypted message
    # This is done to prevent channel replacement and trigerring of autoconnect false -> true
    protocol._noise.noise_protocol.cipher_state_encrypt.n = 100

    protocol._send_message(ButtonAck())
    with pytest.raises(Exception) as e:
        protocol.read(1)
    assert e.value.args[0] == "Received ThpError: DECRYPTION FAILED"

    # Connect using autoconnect credential - should work the same as above
    protocol = prepare_protocol_for_handshake(client)
    protocol._do_channel_allocation()
    protocol._do_handshake(credential_auto, randomness_static)
    protocol._send_message(ThpEndRequest())
    protocol._read_message(ThpEndResponse)


@pytest.mark.setup_client(passphrase=True)
def test_channel_replacement(client: Client) -> None:
    assert client.features.passphrase_protection is True

    host_static_randomness = os.urandom(32)
    host_static_randomness_2 = os.urandom(32)
    host_static_privkey = curve25519.get_private_key(host_static_randomness)
    host_static_privkey_2 = curve25519.get_private_key(host_static_randomness_2)

    assert host_static_privkey != host_static_privkey_2

    client.protocol = get_encrypted_transport_protocol(client, host_static_randomness)

    session = client.get_session(passphrase="TREZOR")
    address = get_test_address(session)

    session_2 = client.get_session(passphrase="ROZERT")
    address_2 = get_test_address(session_2)
    assert address != address_2

    # create new channel using the same host_static_privkey
    client.protocol = get_encrypted_transport_protocol(client, host_static_randomness)
    session_3 = client.get_session(passphrase="OKIDOKI")
    address_3 = get_test_address(session_3)
    assert address_3 != address_2

    # test address on regenerated channel
    new_address = get_test_address(session)
    assert address == new_address
    new_address_3 = get_test_address(session_3)
    assert address_3 == new_address_3

    # create new channel using different host_static_privkey
    client.protocol = get_encrypted_transport_protocol(client, host_static_randomness_2)
    with pytest.raises(exceptions.TrezorFailure) as e_1:
        _ = get_test_address(session)
    assert str(e_1.value.message) == "Invalid session"

    with pytest.raises(exceptions.TrezorFailure) as e_2:
        _ = get_test_address(session_3)
    assert str(e_2.value.message) == "Invalid session"

    session_4 = client.get_session(passphrase="TREZOR")
    super_new_address = get_test_address(session_4)
    assert address == super_new_address
