import secrets
import time
import typing as t
from hashlib import sha256
from unittest.mock import patch

import pytest
import typing_extensions as tx

from tests.common import get_test_address
from trezorlib import exceptions, protobuf
from trezorlib.debuglink import TrezorTestContext as Client
from trezorlib.messages import (
    ButtonAck,
    ButtonRequest,
    Cancel,
    Failure,
    FailureType,
    ThpCodeEntryChallenge,
    ThpCodeEntryCommitment,
    ThpCodeEntryCpaceTrezor,
    ThpCredentialRequest,
    ThpCredentialResponse,
    ThpEndRequest,
    ThpEndResponse,
    ThpPairingMethod,
    ThpPairingRequest,
    ThpSelectMethod,
)
from trezorlib.models import T2T1
from trezorlib.thp import channel, curve25519, pairing
from trezorlib.thp.credentials import StaticCredential

from .connect import (
    break_channel,
    nfc_pairing,
    prepare_channel_for_handshake,
    prepare_channel_for_pairing,
)

if t.TYPE_CHECKING:
    P = tx.ParamSpec("P")

MT = t.TypeVar("MT", bound=protobuf.MessageType)

pytestmark = [pytest.mark.protocol("thp")]


@pytest.fixture
def deterministic_urandom() -> t.Generator[None, None, None]:
    def mock_urandom(n: int) -> bytes:
        return bytes((i % 256 for i in range(n)))

    with patch("os.urandom", side_effect=mock_urandom):
        yield


def test_pairing_qr_code(client: Client) -> None:
    if client.model != T2T1:
        pytest.xfail(reason="UI is implemented only for T2T1")

    prepare_channel_for_pairing(client)
    method = pairing.QrCode(client.pairing)

    # QR Code shown

    # Read code from "Trezor's display" using debuglink

    pairing_info = client.debug.pairing_info(
        thp_channel_id=client.channel.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_qr_code

    # Compute tag for response
    sha_ctx = sha256(client.channel.handshake_hash)
    assert code is not None
    sha_ctx.update(code)
    tag = sha_ctx.digest()

    method.send_qr_code(tag)
    client.pairing.finish()


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
def test_pairing_code_entry(client: Client) -> None:
    prepare_channel_for_pairing(client)
    method = pairing.CodeEntry(client.pairing)

    # Code Entry code shown
    pairing_info = client.debug.pairing_info(
        thp_channel_id=client.channel.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_entry_code
    assert code is not None
    method.send_code(f"{code:06}")

    client.pairing.finish()


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
def test_pairing_code_entry_cancel(client: Client) -> None:
    prepare_channel_for_pairing(client)
    client.pairing.start()
    session = client.pairing.session
    session.call(
        ThpSelectMethod(selected_pairing_method=ThpPairingMethod.CodeEntry),
        expect=ThpCodeEntryCommitment,
    )
    session.call(
        ThpCodeEntryChallenge(challenge=secrets.token_bytes(16)),
        expect=ThpCodeEntryCpaceTrezor,
    )

    # Code Entry code shown

    # Press Cancel button
    client.debug.press_yes()
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code is FailureType.ActionCancelled


def test_pairing_cancel_1(client: Client) -> None:
    prepare_channel_for_pairing(client)

    session = client.pairing.session
    session.write(
        ThpPairingRequest(host_name="localhost", app_name="TestTrezor Cancel 1")
    )
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_pairing_request"
    session.write(ButtonAck())
    time.sleep(1)
    session.write(Cancel())
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled


def test_pairing_cancel_2(client: Client) -> None:
    prepare_channel_for_pairing(client)

    session = client.pairing.session
    session.write(
        ThpPairingRequest(host_name="localhost", app_name="TestTrezor Cancel 2")
    )
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_pairing_request"
    session.write(ButtonAck())
    client.debug.press_no()
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled


def test_pairing_nfc(client: Client) -> None:
    prepare_channel_for_pairing(client)
    nfc_pairing(client)
    client.pairing.finish()


def test_connection_confirmation_cancel(client: Client) -> None:
    prepare_channel_for_pairing(client)
    nfc_pairing(client)

    # Request credential with confirmation after pairing
    credential = client.pairing.request_credential()
    client.pairing.finish()

    break_channel(client)

    # Connect using credential with confirmation
    prepare_channel_for_handshake(client)
    client.channel.open([credential])

    session = client.pairing.session
    session.write(ThpEndRequest())
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_connection_request"
    session.write(Cancel())
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled

    time.sleep(0.2)  # TODO fix this behavior
    prepare_channel_for_handshake(client)
    client.channel.open([credential])
    assert client.pairing.is_paired()
    client.pairing.finish()


def test_autoconnect_credential_request_cancel(client: Client) -> None:
    prepare_channel_for_pairing(client)
    nfc_pairing(client)

    # Request credential with confirmation after pairing
    credential = client.pairing.request_credential()
    client.pairing.finish()
    break_channel(client)
    # Connect using credential with confirmation and request autoconnect
    prepare_channel_for_pairing(client, credential=credential)
    session = client.pairing.session
    session.write(
        ThpCredentialRequest(
            host_static_public_key=client.channel.get_host_static_pubkey(),
            autoconnect=True,
        )
    )
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_connection_request"
    session.write(ButtonAck())
    client.debug.press_yes()
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_autoconnect_credential_request"
    session.write(Cancel())
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled


def test_credential_phase(client: Client) -> None:
    prepare_channel_for_pairing(client)
    nfc_pairing(client)

    # Request credential with confirmation after pairing
    credential = client.pairing.request_credential(autoconnect=False)
    client.pairing.finish()

    break_channel(client)

    # Connect using credential with confirmation
    prepare_channel_for_handshake(client)
    client.channel.open([credential])
    assert client.pairing.is_paired()
    with client:
        client.set_expected_responses(
            [ButtonRequest(name="thp_connection_request"), ThpEndResponse]
        )
        client.pairing.finish()

    # Delete channel from the device by sending badly encrypted message
    # This is done to prevent channel replacement and trigerring of autoconnect false -> true
    break_channel(client)

    # Connect using credential with confirmation and ask for autoconnect credential.
    prepare_channel_for_pairing(client, credential=credential)
    with client:
        client.set_expected_responses(
            [
                ButtonRequest(name="thp_connection_request"),
                ButtonRequest(name="thp_autoconnect_credential_request"),
                ThpCredentialResponse,
                ThpEndResponse,
            ]
        )
        credential_auto = client.pairing.request_credential(autoconnect=True)
        client.pairing.finish()

    # Connect using credential with confirmation
    prepare_channel_for_pairing(client, credential=credential)
    with client:
        # Confirmation dialog is not shown as channel in ENCRYPTED TRANSPORT state with the same
        # host static public key is still available in Trezor's cache. (Channel replacement is triggered.)
        client.set_expected_responses([ThpEndResponse])
        client.pairing.finish()

    # Connect using autoconnect credential
    prepare_channel_for_pairing(client, credential=credential_auto)
    with client:
        client.set_expected_responses([ThpEndResponse])
        client.pairing.finish()

    # Delete channel from the device by sending badly encrypted message
    # This is done to prevent channel replacement and trigerring of autoconnect false -> true
    break_channel(client)

    # Connect using autoconnect credential - should work the same as above
    prepare_channel_for_pairing(client, credential=credential_auto)
    with client:
        client.set_expected_responses([ThpEndResponse])
        client.pairing.finish()


def test_credential_request_in_encrypted_transport_phase(client: Client) -> None:
    prepare_channel_for_pairing(client)
    nfc_pairing(client)

    # Request credential with confirmation after pairing
    credential = client.pairing.request_credential()
    client.pairing.finish()

    session = client.get_seedless_session()
    session.call(
        ThpCredentialRequest(
            host_static_public_key=client.channel.get_host_static_pubkey(),
            autoconnect=True,
            credential=credential.credential,
        ),
        expect=ThpCredentialResponse,
    )


@pytest.mark.setup_client(passphrase=True)
def test_channel_replacement(client: Client) -> None:
    assert client.features.passphrase_protection is True

    session = client.get_session(passphrase="TREZOR")
    address = get_test_address(session)

    session_2 = client.get_session(passphrase="ROZERT")
    address_2 = get_test_address(session_2)
    assert address != address_2

    # create new channel using the same host_static_private_key
    prepare_channel_for_pairing(
        client, host_static_privkey=client.channel.host_static_privkey
    )
    client.pairing.skip()

    session_3 = client.get_session(passphrase="OKIDOKI")
    address_3 = get_test_address(session_3)
    assert address_3 != address_2

    # test address on regenerated channel
    new_address = get_test_address(session)
    assert address == new_address
    new_address_3 = get_test_address(session_3)
    assert address_3 == new_address_3

    host_static_privkey_orig = client.channel.host_static_privkey
    # create new channel using different host_static_private_key
    prepare_channel_for_pairing(client)
    assert client.channel.host_static_privkey != host_static_privkey_orig
    client.pairing.skip()

    with pytest.raises(exceptions.InvalidSessionError):
        _ = get_test_address(session)

    with pytest.raises(exceptions.InvalidSessionError):
        _ = get_test_address(session_3)

    session_4 = client.get_session(passphrase="TREZOR")
    super_new_address = get_test_address(session_4)
    assert address == super_new_address


def test_credential_for_different_key(client: Client) -> None:
    prepare_channel_for_pairing(client)
    nfc_pairing(client)

    assert client.pairing.state is pairing.ControllerLifecycle.PAIRING_COMPLETED
    assert client.channel.state is channel.ChannelState.CREDENTIAL_PHASE

    host_secret = secrets.token_bytes(32)
    host_privkey = curve25519.get_private_key(host_secret)
    host_pubkey = curve25519.get_public_key(host_privkey)

    assert host_privkey != client.channel.host_static_privkey

    credential_response = client.pairing._call(
        ThpCredentialRequest(
            host_static_public_key=host_pubkey,
            autoconnect=False,
        ),
        expect=ThpCredentialResponse,
    )
    client.pairing.finish()

    credential = StaticCredential(
        trezor_pubkey=credential_response.trezor_static_public_key,
        host_privkey=host_privkey,
        credential=credential_response.credential,
    )

    # try to connect using the new credential
    prepare_channel_for_pairing(client, credential=credential)
    assert client.channel.state is channel.ChannelState.CREDENTIAL_PHASE
    client.pairing.finish()
