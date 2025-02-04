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

from trezorlib import btc, device, messages, misc, models
from trezorlib.client import ProtocolVersion
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import MNEMONIC12, MOCK_GET_ENTROPY, get_test_address, is_core
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


def _pin_request(session: Session):
    """Get appropriate PIN request for each model"""
    if session.model is models.T1B1:
        return messages.PinMatrixRequest
    else:
        return messages.ButtonRequest(code=B.PinEntry)


def _assert_protection(
    session: Session, pin: bool = True, passphrase: bool = True
) -> Session:
    """Make sure PIN and passphrase protection have expected values"""
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.ensure_unlocked()
        client.refresh_features()
        assert client.features.pin_protection is pin
        assert client.features.passphrase_protection is passphrase
        if session.protocol_version == ProtocolVersion.PROTOCOL_V2:
            new_session = session.client.get_session()
        session.lock()
        # session.end()
    if session.protocol_version == ProtocolVersion.PROTOCOL_V1:
        new_session = session.client.get_session()
    return new_session


@pytest.mark.protocol("protocol_v1")
def test_initialize(session: Session):
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.ensure_unlocked()
    session = _assert_protection(session)
    with session:
        session.set_expected_responses([messages.Features])
        session.call(messages.Initialize(session_id=session.id))


@pytest.mark.models("core")
@pytest.mark.setup_client(pin=PIN4)
@pytest.mark.parametrize("passphrase", (True, False))
def test_passphrase_reporting(session: Session, passphrase):
    """On TT, passphrase_protection is a private setting, so a locked device should
    report passphrase_protection=None.
    """
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        device.apply_settings(session, use_passphrase=passphrase)

    session.lock()

    # on a locked device, passphrase_protection should be None
    assert session.features.unlocked is False
    assert session.features.passphrase_protection is None

    # on an unlocked device, protection should be reported accurately
    session = _assert_protection(session, pin=True, passphrase=passphrase)

    # after re-locking, the setting should be hidden again
    session.lock()
    assert session.features.unlocked is False
    assert session.features.passphrase_protection is None


def test_apply_settings(session: Session):
    session = _assert_protection(session)

    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.ButtonRequest,
                messages.Success,
                # messages.Features,
            ]
        )
        device.apply_settings(session, label="nazdar")


@pytest.mark.models("legacy")
def test_change_pin_t1(session: Session):
    session = _assert_protection(session)
    with session, session.client as client:
        client.use_pin_sequence([PIN4, PIN4, PIN4])
        session.set_expected_responses(
            [
                messages.ButtonRequest,
                _pin_request(session),
                _pin_request(session),
                _pin_request(session),
                messages.Success,
            ]
        )
        device.change_pin(session)


@pytest.mark.models("core")
def test_change_pin_t2(session: Session):
    session = _assert_protection(session)
    with session, session.client as client:
        client.use_pin_sequence([PIN4, PIN4, PIN4, PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.ButtonRequest,
                _pin_request(session),
                _pin_request(session),
                (
                    session.client.layout_type is LayoutType.Caesar,
                    messages.ButtonRequest,
                ),
                _pin_request(session),
                messages.ButtonRequest,
                messages.Success,
                # messages.Features,
            ]
        )
        device.change_pin(session)


@pytest.mark.setup_client(pin=None, passphrase=False)
def test_ping(session: Session):
    session = _assert_protection(session, pin=False, passphrase=False)
    with session:
        session.set_expected_responses([messages.ButtonRequest, messages.Success])
        session.call(messages.Ping(message="msg", button_protection=True))


def test_get_entropy(session: Session):
    session = _assert_protection(session)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.ButtonRequest(code=B.ProtectCall),
                messages.Entropy,
            ]
        )
        misc.get_entropy(session, 10)


def test_get_public_key(session: Session):
    session = _assert_protection(session)

    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        expected_responses = [_pin_request(session)]

        if session.protocol_version == ProtocolVersion.PROTOCOL_V1:
            expected_responses.append(messages.PassphraseRequest)
        expected_responses.append(messages.PublicKey)

        session.set_expected_responses(expected_responses)
        btc.get_public_node(session, [])


def test_get_address(session: Session):
    session = _assert_protection(session)

    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        expected_responses = [_pin_request(session)]
        if session.protocol_version == ProtocolVersion.PROTOCOL_V1:
            expected_responses.append(messages.PassphraseRequest)
        expected_responses.append(messages.Address)

        session.set_expected_responses(expected_responses)

        get_test_address(session)


def test_wipe_device(session: Session):
    # TODO
    # Precise cause of crash is not determined, it happens with some order of
    # tests, but not with all. The following leads to crash:
    # pytest --random-order-seed=675848 tests/device_tests/test_protection_levels.py
    #
    # Traceback (most recent call last):
    #   File "trezor/wire/__init__.py", line 70, in handle_session
    #   File "trezor/wire/thp_main.py", line 79, in thp_main_loop
    #   File "trezor/wire/thp_main.py", line 145, in _handle_allocated
    #   File "trezor/wire/thp/received_message_handler.py", line 123, in handle_received_message
    #   File "trezor/wire/thp/received_message_handler.py", line 231, in _handle_state_TH1
    #   File "trezor/wire/thp/crypto.py", line 93, in handle_th1_crypto
    #   File "trezor/wire/thp/crypto.py", line 178, in _derive_static_key_pair
    #   File "storage/device.py", line 364, in get_device_secret
    #   File "storage/common.py", line 21, in set
    # RuntimeError: Could not save value

    session = _assert_protection(session)
    with session:
        session.set_expected_responses([messages.ButtonRequest, messages.Success])
        device.wipe(session)
    client = session.client.get_new_client()
    session = client.get_seedless_session()
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses([messages.Features])
        session.call(messages.GetFeatures())


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.models("legacy")
def test_reset_device(session: Session):
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    with session:
        session.set_expected_responses(
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
@pytest.mark.models("legacy")
def test_recovery_device(session: Session):
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    session.client.use_mnemonic(MNEMONIC12)
    with session:
        session.set_expected_responses(
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
            input_callback=session.client.mnemonic_callback,
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


def test_sign_message(session: Session):
    session = _assert_protection(session)

    with session, session.client as client:
        client.use_pin_sequence([PIN4])

        expected_responses = [_pin_request(session)]

        if session.protocol_version == ProtocolVersion.PROTOCOL_V1:
            expected_responses.append(messages.PassphraseRequest)

        expected_responses.extend(
            [
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.MessageSignature,
            ]
        )

        session.set_expected_responses(expected_responses)

        btc.sign_message(
            session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"), "testing message"
        )


@pytest.mark.models("legacy")
def test_verify_message_t1(session: Session):
    session = _assert_protection(session)
    with session:
        session.set_expected_responses(
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


@pytest.mark.models("core")
def test_verify_message_t2(session: Session):
    session = _assert_protection(session)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
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


def test_signtx(session: Session):
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

    session = _assert_protection(session)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        expected_responses = [_pin_request(session)]
        if session.protocol_version == ProtocolVersion.PROTOCOL_V1:
            expected_responses.append(messages.PassphraseRequest)
        expected_responses.extend(
            [
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
        )
        session.set_expected_responses(expected_responses)

        btc.sign_tx(session, "Bitcoin", [inp1], [out1], prev_txes=TxCache("Bitcoin"))


# def test_firmware_erase():
#    pass

# def test_firmware_upload():
#    pass


@pytest.mark.setup_client(pin=PIN4, passphrase=False)
def test_unlocked(session: Session):
    assert session.features.unlocked is False

    session = _assert_protection(session, passphrase=False)

    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses([_pin_request(session), messages.Address])
        get_test_address(session)

    session.refresh_features()
    assert session.features.unlocked is True
    with session:
        session.set_expected_responses([messages.Address])
        get_test_address(session)


@pytest.mark.setup_client(pin=None, passphrase=True)
def test_passphrase_cached(session: Session):
    session = _assert_protection(session, pin=False)
    with session:
        if session.protocol_version == 1:
            session.set_expected_responses(
                [messages.PassphraseRequest, messages.Address]
            )
        elif session.protocol_version == 2:
            session.set_expected_responses([messages.Address])
        else:
            raise Exception("Unknown session type")
        get_test_address(session)

    with session:
        session.set_expected_responses([messages.Address])
        get_test_address(session)
