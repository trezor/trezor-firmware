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
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import MNEMONIC12, WITH_MOCK_URANDOM, get_test_address, is_core
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
    client: Client, pin: bool = True, passphrase: bool = True
) -> None:
    """Make sure PIN and passphrase protection have expected values"""
    with client:
        client.use_pin_sequence([PIN4])
        client.ensure_unlocked()
        client.refresh_features()
        assert client.features.pin_protection is pin
        assert client.features.passphrase_protection is passphrase
    # TODO session.clear_session()


def test_initialize(session: Session):
    _assert_protection(session.client)
    with session:
        session.set_expected_responses([messages.Features])
        raise Exception("INITIALIZE IS DISABLED")
        # TODO session.init_device()


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
    _assert_protection(session.client, pin=True, passphrase=passphrase)

    # after re-locking, the setting should be hidden again
    session.lock()
    assert session.features.unlocked is False
    assert session.features.passphrase_protection is None


def test_apply_settings(session: Session):
    _assert_protection(session.client)
    with session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.ButtonRequest,
                messages.Success,
                messages.Features,
            ]
        )  # TrezorSession reinitializes device
        device.apply_settings(session, label="nazdar")


@pytest.mark.models("legacy")
def test_change_pin_t1(session: Session):
    _assert_protection(session.client)
    with session.client as client:
        client.use_pin_sequence([PIN4, PIN4, PIN4])
        session.set_expected_responses(
            [
                messages.ButtonRequest,
                _pin_request(session),
                _pin_request(session),
                _pin_request(session),
                messages.Success,
                messages.Features,
            ]
        )
        device.change_pin(session)


@pytest.mark.models("core")
def test_change_pin_t2(session: Session):
    _assert_protection(session.client)
    with session.client as client:
        client.use_pin_sequence([PIN4, PIN4, PIN4, PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.ButtonRequest,
                _pin_request(session),
                _pin_request(session),
                (session.client.layout_type is LayoutType.TR, messages.ButtonRequest),
                _pin_request(session),
                messages.ButtonRequest,
                messages.Success,
                messages.Features,
            ]
        )
        device.change_pin(session)


@pytest.mark.setup_client(pin=None, passphrase=False)
def test_ping(session: Session):
    _assert_protection(session.client, pin=False, passphrase=False)
    with session:
        session.set_expected_responses([messages.ButtonRequest, messages.Success])
        session.call(messages.Ping("msg", True))


def test_get_entropy(session: Session):
    _assert_protection(session.client)
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
    _assert_protection(session.client)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.PassphraseRequest,
                messages.PublicKey,
            ]
        )
        btc.get_public_node(session, [])


def test_get_address(session: Session):
    _assert_protection(session.client)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.PassphraseRequest,
                messages.Address,
            ]
        )
        get_test_address(session)


def test_wipe_device(session: Session):
    _assert_protection(session.client)
    with session:
        session.set_expected_responses(
            [messages.ButtonRequest, messages.Success, messages.Features]
        )
        device.wipe(session)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.models("legacy")
def test_reset_device(session: Session):
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    with WITH_MOCK_URANDOM, session:
        session.set_expected_responses(
            [messages.ButtonRequest]
            + [messages.EntropyRequest]
            + [messages.ButtonRequest] * 24
            + [messages.Success, messages.Features]
        )
        device.reset(
            session,
            strength=128,
            passphrase_protection=True,
            pin_protection=False,
            label="label",
        )

    with pytest.raises(TrezorFailure):
        # This must fail, because device is already initialized
        # Using direct call because `device.reset` has its own check
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
            + [messages.Success, messages.Features]
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
    _assert_protection(session.client)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.PassphraseRequest,
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.MessageSignature,
            ]
        )
        btc.sign_message(
            session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"), "testing message"
        )


@pytest.mark.models("legacy")
def test_verify_message_t1(session: Session):
    _assert_protection(session.client)
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
    _assert_protection(session.client)
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

    _assert_protection(session.client)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses(
            [
                _pin_request(session),
                messages.PassphraseRequest,
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
        btc.sign_tx(session, "Bitcoin", [inp1], [out1], prev_txes=TxCache("Bitcoin"))


# def test_firmware_erase():
#    pass

# def test_firmware_upload():
#    pass


@pytest.mark.setup_client(pin=PIN4, passphrase=False)
def test_unlocked(session: Session):
    assert session.features.unlocked is False

    _assert_protection(session.client, passphrase=False)
    with session, session.client as client:
        client.use_pin_sequence([PIN4])
        session.set_expected_responses([_pin_request(session), messages.Address])
        get_test_address(session)

    # TODO session.init_device()
    assert session.features.unlocked is True
    with session:
        session.set_expected_responses([messages.Address])
        get_test_address(session)


@pytest.mark.setup_client(pin=None, passphrase=True)
def test_passphrase_cached(session: Session):
    _assert_protection(session.client, pin=False)
    with session:
        session.set_expected_responses([messages.PassphraseRequest, messages.Address])
        get_test_address(session)

    with session:
        session.set_expected_responses([messages.Address])
        get_test_address(session)
