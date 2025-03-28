# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import pytest

from trezorlib import btc, device, exceptions, messages, misc, models
from trezorlib.client import ProtocolVersion
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import MNEMONIC12, MOCK_GET_ENTROPY, TEST_ADDRESS_N, is_core
from ..tx_cache import TxCache
from .bitcoin.signtx import (
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType

TXHASH_50f6f1 = bytes.fromhex(
    "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
)

PIN4 = "1234"


pytestmark = pytest.mark.setup_client(pin=PIN4, passphrase=True)


def _pin_request(session: Client):
    """Get appropriate PIN request for each model"""
    if session.model is models.T1B1:
        return messages.PinMatrixRequest
    else:
        return messages.ButtonRequest(code=B.PinEntry)


def _assert_protection(client: Client, pin: bool = True, passphrase: bool = True):
    """Make sure PIN and passphrase protection have expected values"""
    with client:
        client.use_pin_sequence([PIN4])
        session = client.get_seedless_session()
        try:
            session.ensure_unlocked()
        except exceptions.InvalidSessionError:
            session.cancel()
            session._read()

        client.refresh_features()
        assert client.features.pin_protection is pin
        assert client.features.passphrase_protection is passphrase
        session.lock()
        session.end()


def _get_test_address(session: Session) -> None:
    resp = session.call_raw(
        messages.GetAddress(address_n=TEST_ADDRESS_N, coin_name="Testnet")
    )
    if isinstance(resp, messages.ButtonRequest):
        resp = session._callback_button(resp)
    if isinstance(resp, messages.PassphraseRequest):
        session.call_raw(messages.PassphraseAck(passphrase=""))


def test_initialize(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        if client.protocol_version == ProtocolVersion.V1:
            client.set_expected_responses([messages.Features])
        client.get_seedless_session()


@pytest.mark.models("core")
@pytest.mark.setup_client(pin=PIN4)
@pytest.mark.parametrize("passphrase", (True, False))
def test_passphrase_reporting(session: Session, passphrase):
    """On TT, passphrase_protection is a private setting, so a locked device should
    report passphrase_protection=None.
    """
    with session.client as client:
        client.use_pin_sequence([PIN4])
        device.apply_settings(session, use_passphrase=passphrase)

    session.lock()

    # on a locked device, passphrase_protection should be None
    assert session.features.unlocked is False
    assert session.features.passphrase_protection is None

    # on an unlocked device, protection should be reported accurately
    _assert_protection(client, pin=True, passphrase=passphrase)

    # after re-locking, the setting should be hidden again
    session.lock()
    assert session.features.unlocked is False
    assert session.features.passphrase_protection is None


def test_apply_settings(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                messages.Features,
                _pin_request(client),
                messages.ButtonRequest,
                messages.Success,
            ]
        )
        session = client.get_seedless_session()
        device.apply_settings(session, label="nazdar")


@pytest.mark.models("legacy")
def test_change_pin_t1(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4, PIN4, PIN4])
        session = client.get_seedless_session()
        client.set_expected_responses(
            [
                messages.ButtonRequest,
                _pin_request(client),
                _pin_request(client),
                _pin_request(client),
                messages.Success,
            ]
        )
        device.change_pin(session)


@pytest.mark.models("core")
def test_change_pin_t2(client: Client):
    _assert_protection(client)
    v1 = client.protocol_version == ProtocolVersion.V1
    with client:
        client.use_pin_sequence([PIN4, PIN4, PIN4, PIN4])
        client.set_expected_responses(
            [
                (v1, messages.Features),
                _pin_request(client),
                messages.ButtonRequest,
                _pin_request(client),
                _pin_request(client),
                (
                    client.layout_type is LayoutType.Caesar,
                    messages.ButtonRequest,
                ),
                _pin_request(client),
                messages.ButtonRequest,
                messages.Success,
            ]
        )
        session = client.get_seedless_session()
        device.change_pin(session)


@pytest.mark.setup_client(pin=None, passphrase=False)
def test_ping(client: Client):
    _assert_protection(client, pin=False, passphrase=False)
    session = client.get_session()
    with client:
        client.set_expected_responses([messages.ButtonRequest, messages.Success])
        session.call(messages.Ping(message="msg", button_protection=True))


def test_get_entropy(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        session = client.get_seedless_session()
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.ButtonRequest(code=B.ProtectCall),
                messages.Entropy,
            ]
        )
        misc.get_entropy(session, 10)


def test_get_public_key(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        expected_responses = [messages.Features, _pin_request(client)]

        if client.protocol_version == ProtocolVersion.V1:
            expected_responses.append(messages.PassphraseRequest)
        expected_responses.extend([messages.Address, messages.PublicKey])

        client.set_expected_responses(expected_responses)
        session = client.get_session()

        session.call(messages.GetPublicKey(address_n=[]))


def test_get_address(client: Client):
    _assert_protection(client)

    with client:
        client.use_pin_sequence([PIN4])
        expected_responses = [messages.Features, _pin_request(client)]
        if client.protocol_version == ProtocolVersion.V1:
            expected_responses.extend([messages.PassphraseRequest, messages.Address])
        expected_responses.append(messages.Address)

        client.set_expected_responses(expected_responses)
        session = client.get_session()
        _get_test_address(session)


def test_wipe_device(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        session = client.get_session()
        client.set_expected_responses([messages.ButtonRequest, messages.Success])
        device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    with client:
        client.set_expected_responses([messages.Features])
        session.call(messages.GetFeatures())


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
@pytest.mark.models("legacy")
def test_reset_device(session: Session):
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    with session.client as client:
        client.set_expected_responses(
            [messages.ButtonRequest]
            + [messages.EntropyRequest]
            + [messages.ButtonRequest] * 24
            + [messages.Success, messages.Features]
        )
        device.setup(
            session,
            strength=128,
            passphrase_protection=True,
            pin_protection=False,
            label="label",
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )
        session.call(messages.GetFeatures())

    with pytest.raises(TrezorFailure):
        # This must fail, because device is already initialized
        # Using direct call because `device.setup` has its own check
        session.call(
            messages.ResetDevice(
                strength=128,
                passphrase_protection=True,
                pin_protection=False,
                label="label",
            )
        )


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
@pytest.mark.models("legacy")
def test_recovery_device(session: Session, uninitialized_session=True):
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    session.client.use_mnemonic(MNEMONIC12)
    with session.client as client:
        client.set_expected_responses(
            [messages.ButtonRequest]
            + [messages.WordRequest] * 24
            + [messages.Success]  # , messages.Features]
        )

        device.recover(
            session,
            12,
            False,
            False,
            "label",
            input_callback=client.mnemonic_callback,
        )

    with pytest.raises(TrezorFailure):
        # This must fail, because device is already initialized
        # Using direct call because `device.recover` has its own check
        session.call(
            messages.RecoveryDevice(
                word_count=12,
                passphrase_protection=False,
                pin_protection=False,
                label="label",
            )
        )


@pytest.mark.models(skip=["eckhart"])
def test_sign_message(client: Client):
    _assert_protection(client)
    v1 = client.protocol_version == ProtocolVersion.V1

    with client:
        client.use_pin_sequence([PIN4])

        expected_responses = [
            (v1, messages.Features),
            _pin_request(client),
            (v1, messages.PassphraseRequest),
            (v1, messages.Address),
            messages.ButtonRequest,
            messages.ButtonRequest,
            messages.MessageSignature,
        ]
        client.set_expected_responses(expected_responses)

        session = client.get_session()
        btc.sign_message(
            session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"), "testing message"
        )


def test_sign_message_seedless(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        session = client.get_seedless_session()
        if client.protocol_version == ProtocolVersion.V1:
            with pytest.raises(exceptions.InvalidSessionError):
                btc.sign_message(
                    session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"), "testing message"
                )


@pytest.mark.models("legacy")
def test_verify_message_t1(client: Client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        session = client.get_session()
        client.set_expected_responses(
            [
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.Success,
            ]
        )
        btc.verify_message(
            session,
            "Bitcoin",
            "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e",
            bytes.fromhex(
                "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
            ),
            "This is an example of a signed message.",
        )


@pytest.mark.models("core", skip=["eckhart"])
def test_verify_message_t2(client: Client):
    _assert_protection(client)
    v1 = client.protocol_version == ProtocolVersion.V1
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                (v1, messages.Features),
                _pin_request(client),
                (v1, messages.PassphraseRequest),
                (v1, messages.Address),
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.Success,
            ]
        )
        session = client.get_session()
        btc.verify_message(
            session,
            "Bitcoin",
            "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e",
            bytes.fromhex(
                "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
            ),
            "This is an example of a signed message.",
        )


def test_signtx(client: Client):
    # input tx: 50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/5"),  # 1GA9u9TfCG7SWmKCveBumdA1TZpfom6ZdJ
        amount=50_000,
        prev_hash=TXHASH_50f6f1,
        prev_index=1,
    )

    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=50_000 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    _assert_protection(client)
    v1 = client.protocol_version == ProtocolVersion.V1

    with client:
        session = client.get_seedless_session()
        client.use_pin_sequence([PIN4])
        expected_responses = [
            (v1, messages.Features),
            _pin_request(client),
            (v1, messages.PassphraseRequest),
            (v1, messages.Address),
            request_input(0),
            request_output(0),
            messages.ButtonRequest(code=B.ConfirmOutput),
            (is_core(session), messages.ButtonRequest(code=B.ConfirmOutput)),
            messages.ButtonRequest(code=B.SignTx),
            request_input(0),
            request_meta(TXHASH_50f6f1),
            request_input(0, TXHASH_50f6f1),
            request_output(0, TXHASH_50f6f1),
            request_output(1, TXHASH_50f6f1),
            request_input(0),
            request_output(0),
            request_output(0),
            request_finished(),
        ]
        client.set_expected_responses(expected_responses)
        session = client.get_session()
        btc.sign_tx(session, "Bitcoin", [inp1], [out1], prev_txes=TxCache("Bitcoin"))


# def test_firmware_erase():
#    pass

# def test_firmware_upload():
#    pass


@pytest.mark.setup_client(pin=PIN4, passphrase=False)
def test_unlocked(client: Client):
    assert client.features.unlocked is False
    v1 = client.protocol_version == ProtocolVersion.V1

    _assert_protection(client, passphrase=False)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                (v1, messages.Features),
                _pin_request(client),
                messages.Address,
            ]
        )
        session = client.get_session()
        _get_test_address(session)

    session.refresh_features()
    assert session.features.unlocked is True
    with client:
        client.set_expected_responses([messages.Address])
        _get_test_address(session)
