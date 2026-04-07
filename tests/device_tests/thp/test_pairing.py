import secrets
import time
import typing as t
from contextlib import contextmanager
from hashlib import sha256
from unittest.mock import patch

import pytest
import typing_extensions as tx

from tests.common import get_test_address
from trezorlib import exceptions, protobuf
from trezorlib.debuglink import TrezorTestContext
from trezorlib.messages import (
    ButtonAck,
    ButtonRequest,
    Cancel,
    Failure,
    FailureType,
    ThpCredentialRequest,
    ThpCredentialResponse,
    ThpEndRequest,
    ThpEndResponse,
    ThpPairingRequest,
)
from trezorlib.models import T2T1
from trezorlib.thp import channel, curve25519
from trezorlib.thp.credentials import StaticCredential
from trezorlib.thp.pairing import CodeEntry, ControllerLifecycle, QrCode

from .connect import break_channel, prepare_channel_for_pairing

if t.TYPE_CHECKING:
    P = tx.ParamSpec("P")

MT = t.TypeVar("MT", bound=protobuf.MessageType)

pytestmark = [pytest.mark.protocol("thp")]


@contextmanager
def deterministic_secrets() -> t.Generator[None, None, None]:
    def mock_urandom(n: int) -> bytes:
        return bytes((i % 256 for i in range(n)))

    with patch("secrets.token_bytes", side_effect=mock_urandom):
        yield


def test_pairing_qr_code(test_ctx: TrezorTestContext) -> None:
    if test_ctx.model != T2T1:
        pytest.xfail(reason="UI is implemented only for T2T1")

    pairing = prepare_channel_for_pairing(test_ctx)
    method = QrCode(pairing)

    # QR Code shown

    # Read code from "Trezor's display" using debuglink

    pairing_info = test_ctx.debug.pairing_info(
        thp_channel_id=pairing.channel.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_qr_code

    # Compute tag for response
    sha_ctx = sha256(pairing.channel.handshake_hash)
    assert code is not None
    sha_ctx.update(code)
    tag = sha_ctx.digest()

    method.send_qr_code(tag)
    pairing.finish()


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
@deterministic_secrets()
def test_pairing_code_entry(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, fixed_entropy=True)
    method = CodeEntry(pairing)

    # Code Entry code shown
    pairing_info = test_ctx.debug.pairing_info(
        thp_channel_id=pairing.channel.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_entry_code
    assert code is not None
    method.send_code(f"{code:06}")

    pairing.finish()


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
@deterministic_secrets()
def test_pairing_code_entry_invalid_cpace_key(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, fixed_entropy=True)
    method = CodeEntry(pairing)

    # Code Entry code shown
    pairing_info = test_ctx.debug.pairing_info(
        thp_channel_id=pairing.channel.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_entry_code
    assert code is not None
    code_str = f"{code:06}"

    invalid_msg = method._perform_cpace(code_str)
    invalid_msg.cpace_host_public_key = b"\x00" * 32
    method._perform_cpace = lambda code: invalid_msg
    with pytest.raises(
        exceptions.TrezorFailure, match="DataError: Unexpected Code Entry Tag"
    ):
        method.send_code(code_str)


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
@deterministic_secrets()
def test_pairing_code_entry_invalid_cpace_key_length(
    test_ctx: TrezorTestContext,
) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, fixed_entropy=True)
    method = CodeEntry(pairing)

    # Code Entry code shown
    pairing_info = test_ctx.debug.pairing_info(
        thp_channel_id=pairing.channel.channel_id.to_bytes(2, "big")
    )
    code = pairing_info.code_entry_code
    assert code is not None
    code_str = f"{code:06}"

    invalid_msg = method._perform_cpace(code_str)
    invalid_msg.cpace_host_public_key = invalid_msg.cpace_host_public_key[:16]
    method._perform_cpace = lambda code: invalid_msg
    with pytest.raises(
        exceptions.TrezorFailure,
        match="DataError: CPACE host public key must be 32 bytes long",
    ):
        method.send_code(code_str)


@pytest.mark.filterwarnings(
    "ignore:One of ephemeral keypairs is already set. This is OK for testing, but should NEVER happen in production!"
)
@deterministic_secrets()
def test_pairing_code_entry_cancel(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, fixed_entropy=True)
    CodeEntry(pairing)
    # Code Entry code shown

    # Press Cancel button
    test_ctx.debug.press_yes()
    failure = Failure.ensure_isinstance(pairing.session.read())
    assert failure.code is FailureType.ActionCancelled


def test_pairing_cancel_1(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx)

    session = pairing.session
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


def test_pairing_cancel_2(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx)

    session = pairing.session
    session.write(
        ThpPairingRequest(host_name="localhost", app_name="TestTrezor Cancel 2")
    )
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_pairing_request"
    session.write(ButtonAck())
    test_ctx.debug.press_no()
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled


def test_pairing_nfc(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, nfc_pairing=True)
    pairing.finish()


def test_connection_confirmation_cancel(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, nfc_pairing=True)

    # Request credential with confirmation after pairing
    credential = pairing.request_credential()
    pairing.finish()

    break_channel(pairing.client)

    # Connect using credential with confirmation
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)

    session = pairing.session
    session.write(ThpEndRequest())
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_connection_request"
    session.write(Cancel())
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled

    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)
    assert pairing.is_paired()
    pairing.finish()


def test_autoconnect_credential_request_cancel(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, nfc_pairing=True)

    # Request credential with confirmation after pairing
    credential = pairing.request_credential()
    pairing.finish()
    break_channel(pairing.client)

    # Connect using credential with confirmation and request autoconnect
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)
    session = pairing.session
    session.write(
        ThpCredentialRequest(
            host_static_public_key=pairing.channel.get_host_static_pubkey(),
            autoconnect=True,
        )
    )
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_connection_request"
    session.write(ButtonAck())
    test_ctx.debug.press_yes()
    button_req = ButtonRequest.ensure_isinstance(session.read())
    assert button_req.name == "thp_autoconnect_credential_request"
    session.write(Cancel())
    failure = Failure.ensure_isinstance(session.read())
    assert failure.code == FailureType.ActionCancelled


def test_credential_phase(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, nfc_pairing=True)

    # Request credential with confirmation after pairing
    credential = pairing.request_credential(autoconnect=False)
    pairing.finish()

    break_channel(pairing.client)

    # Connect using credential with confirmation
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)
    assert pairing.is_paired()
    with test_ctx:
        test_ctx.set_expected_responses(
            [ButtonRequest(name="thp_connection_request"), ThpEndResponse]
        )
        pairing.finish()

    # Delete channel from the device by sending badly encrypted message
    # This is done to prevent channel replacement and trigerring of autoconnect false -> true
    break_channel(pairing.client)

    # Connect using credential with confirmation and ask for autoconnect credential.
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)
    assert pairing.is_paired()
    with test_ctx:
        test_ctx.set_expected_responses(
            [
                ButtonRequest(name="thp_connection_request"),
                ButtonRequest(name="thp_autoconnect_credential_request"),
                ThpCredentialResponse,
                ThpEndResponse,
            ]
        )
        credential_auto = pairing.request_credential(autoconnect=True)
        pairing.finish()

    # Connect using credential with confirmation
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)
    assert pairing.is_paired()
    with test_ctx:
        # Confirmation dialog is not shown as channel in ENCRYPTED TRANSPORT state with the same
        # host static public key is still available in Trezor's cache. (Channel replacement is triggered.)
        test_ctx.set_expected_responses([ThpEndResponse])
        pairing.finish()

    # Connect using autoconnect credential
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential_auto)
    assert pairing.is_paired()
    with test_ctx:
        test_ctx.set_expected_responses([ThpEndResponse])
        pairing.finish()

    # Delete channel from the device by sending badly encrypted message
    # This is done to prevent channel replacement and trigerring of autoconnect false -> true
    break_channel(pairing.client)

    # Connect using autoconnect credential - should work the same as above
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential_auto)
    assert pairing.is_paired()
    with test_ctx:
        test_ctx.set_expected_responses([ThpEndResponse])
        pairing.finish()


def test_credential_request_in_encrypted_transport_phase(
    test_ctx: TrezorTestContext,
) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, nfc_pairing=True)

    # Request credential with confirmation after pairing
    credential = pairing.request_credential()
    pairing.finish()

    seedless_session = test_ctx.client.get_session(None)
    seedless_session.call(
        ThpCredentialRequest(
            host_static_public_key=pairing.channel.get_host_static_pubkey(),
            autoconnect=True,
            credential=credential.credential,
        ),
        expect=ThpCredentialResponse,
    )


@pytest.mark.setup_client(passphrase=True)
def test_channel_replacement(test_ctx: TrezorTestContext) -> None:
    assert test_ctx.features.passphrase_protection is True

    session_1 = test_ctx.get_session(passphrase="TREZOR")
    address_1 = get_test_address(session_1)

    session_2 = test_ctx.get_session(passphrase="ROZERT")
    address_2 = get_test_address(session_2)
    assert address_1 != address_2

    # create new channel using the same host_static_private_key
    pairing = prepare_channel_for_pairing(
        test_ctx,
        host_static_privkey=test_ctx.channel.host_static_privkey,
    )
    pairing.skip()

    session_3 = test_ctx.get_session(passphrase="OKIDOKI")
    address_3 = get_test_address(session_3)
    assert address_3 != address_2

    # test address on regenerated channel
    assert address_1 == get_test_address(session_1)
    assert address_3 == get_test_address(session_3)

    host_static_privkey_orig = pairing.channel.host_static_privkey
    # create new channel using different host_static_private_key
    pairing = prepare_channel_for_pairing(test_ctx)
    assert pairing.channel.host_static_privkey != host_static_privkey_orig
    pairing.skip()

    with pytest.raises(exceptions.InvalidSessionError):
        _ = get_test_address(session_1)

    with pytest.raises(exceptions.InvalidSessionError):
        _ = get_test_address(session_3)

    assert address_1 == get_test_address(test_ctx.get_session(passphrase="TREZOR"))


def test_credential_for_different_key(test_ctx: TrezorTestContext) -> None:
    pairing = prepare_channel_for_pairing(test_ctx, nfc_pairing=True)

    assert pairing.state is ControllerLifecycle.PAIRING_COMPLETED
    assert pairing.channel.state is channel.ChannelState.CREDENTIAL_PHASE

    host_secret = secrets.token_bytes(32)
    host_privkey = curve25519.get_private_key(host_secret)
    host_pubkey = curve25519.get_public_key(host_privkey)

    assert host_privkey != pairing.channel.host_static_privkey

    credential_response = pairing._call(
        ThpCredentialRequest(
            host_static_public_key=host_pubkey,
            autoconnect=False,
        ),
        expect=ThpCredentialResponse,
    )
    pairing.finish()

    credential = StaticCredential(
        trezor_pubkey=credential_response.trezor_static_public_key,
        host_privkey=host_privkey,
        credential=credential_response.credential,
    )

    # try to connect using the new credential
    pairing = prepare_channel_for_pairing(test_ctx, credential=credential)
    assert pairing.channel.state is channel.ChannelState.CREDENTIAL_PHASE
    pairing.finish()
