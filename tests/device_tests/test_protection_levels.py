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

from trezorlib import btc, device, messages, misc
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..common import MNEMONIC12, get_test_address
from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)

PIN4 = "1234"


pytestmark = pytest.mark.setup_client(pin=PIN4, passphrase=True)


def _pin_request(client):
    """Get appropriate PIN request for each model"""
    if client.features.model == "1":
        return messages.PinMatrixRequest
    else:
        return messages.ButtonRequest(code=B.PinEntry)


def _assert_protection(client, pin: bool = True, passphrase: bool = True) -> None:
    """Make sure PIN and passphrase protection have expected values"""
    with client:
        client.use_pin_sequence([PIN4])
        client.ensure_unlocked()
        assert client.features.pin_protection is pin
        assert client.features.passphrase_protection is passphrase
    client.clear_session()


def test_initialize(client):
    _assert_protection(client)
    with client:
        client.set_expected_responses([messages.Features])
        client.init_device()


@pytest.mark.skip_t1
@pytest.mark.setup_client(pin=PIN4)
@pytest.mark.parametrize("passphrase", (True, False))
def test_passphrase_reporting(client, passphrase):
    """On TT, passphrase_protection is a private setting, so a locked device should
    report passphrase_protection=None.
    """
    with client:
        client.use_pin_sequence([PIN4])
        device.apply_settings(client, use_passphrase=passphrase)

    client.lock()

    # on a locked device, passphrase_protection should be None
    assert client.features.unlocked is False
    assert client.features.passphrase_protection is None

    # on an unlocked device, protection should be reported accurately
    _assert_protection(client, pin=True, passphrase=passphrase)

    # after re-locking, the setting should be hidden again
    client.lock()
    assert client.features.unlocked is False
    assert client.features.passphrase_protection is None


def test_apply_settings(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.ButtonRequest,
                messages.Success,
                messages.Features,
            ]
        )  # TrezorClient reinitializes device
        device.apply_settings(client, label="nazdar")


@pytest.mark.skip_t2
def test_change_pin_t1(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4, PIN4, PIN4])
        client.set_expected_responses(
            [
                messages.ButtonRequest,
                _pin_request(client),
                _pin_request(client),
                _pin_request(client),
                messages.Success,
                messages.Features,
            ]
        )
        device.change_pin(client)


@pytest.mark.skip_t1
def test_change_pin_t2(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4, PIN4, PIN4, PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.ButtonRequest,
                _pin_request(client),
                _pin_request(client),
                _pin_request(client),
                messages.ButtonRequest,
                messages.Success,
                messages.Features,
            ]
        )
        device.change_pin(client)


@pytest.mark.setup_client(pin=None, passphrase=False)
def test_ping(client):
    _assert_protection(client, pin=False, passphrase=False)
    with client:
        client.set_expected_responses([messages.ButtonRequest, messages.Success])
        client.ping("msg", True)


@pytest.mark.skip_t2
def test_get_entropy_t1(client):
    _assert_protection(client)
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ProtectCall),
                messages.Entropy,
            ]
        )
        misc.get_entropy(client, 10)


@pytest.mark.skip_t1
def test_get_entropy_t2(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.ButtonRequest(code=B.ProtectCall),
                messages.Entropy,
            ]
        )
        misc.get_entropy(client, 10)


def test_get_public_key(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.PassphraseRequest,
                messages.PublicKey,
            ]
        )
        btc.get_public_node(client, [])


def test_get_address(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.PassphraseRequest,
                messages.Address,
            ]
        )
        get_test_address(client)


def test_wipe_device(client):
    _assert_protection(client)
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest, messages.Success, messages.Features]
        )
        device.wipe(client)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.skip_t2
def test_reset_device(client):
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest]
            + [messages.EntropyRequest]
            + [messages.ButtonRequest] * 24
            + [messages.Success, messages.Features]
        )
        device.reset(client, False, 128, True, False, "label", "en-US")

    with pytest.raises(TrezorFailure):
        # This must fail, because device is already initialized
        # Using direct call because `device.reset` has its own check
        client.call(
            messages.ResetDevice(
                display_random=False,
                strength=128,
                passphrase_protection=True,
                pin_protection=False,
                label="label",
                language="en-US",
            )
        )


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.skip_t2
def test_recovery_device(client):
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    client.use_mnemonic(MNEMONIC12)
    with client:
        client.set_expected_responses(
            [messages.ButtonRequest]
            + [messages.WordRequest] * 24
            + [messages.Success, messages.Features]
        )

        device.recover(
            client, 12, False, False, "label", "en-US", client.mnemonic_callback
        )

    with pytest.raises(TrezorFailure):
        # This must fail, because device is already initialized
        # Using direct call because `device.recover` has its own check
        client.call(
            messages.RecoveryDevice(
                word_count=12,
                passphrase_protection=False,
                pin_protection=False,
                label="label",
                language="en-US",
            )
        )


def test_sign_message(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.PassphraseRequest,
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.MessageSignature,
            ]
        )
        btc.sign_message(
            client, "Bitcoin", parse_path("44h/0h/0h/0/0"), "testing message"
        )


@pytest.mark.skip_t2
def test_verify_message_t1(client):
    _assert_protection(client)
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.Success,
            ]
        )
        btc.verify_message(
            client,
            "Bitcoin",
            "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e",
            bytes.fromhex(
                "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
            ),
            "This is an example of a signed message.",
        )


@pytest.mark.skip_t1
def test_verify_message_t2(client):
    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.ButtonRequest,
                messages.ButtonRequest,
                messages.Success,
            ]
        )
        btc.verify_message(
            client,
            "Bitcoin",
            "14LmW5k4ssUrtbAB4255zdqv3b4w1TuX9e",
            bytes.fromhex(
                "209e23edf0e4e47ff1dec27f32cd78c50e74ef018ee8a6adf35ae17c7a9b0dd96f48b493fd7dbab03efb6f439c6383c9523b3bbc5f1a7d158a6af90ab154e9be80"
            ),
            "This is an example of a signed message.",
        )


def test_signtx(client):
    # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
    # input 0: 0.0039 BTC

    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/0"),
        amount=390000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    _assert_protection(client)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses(
            [
                _pin_request(client),
                messages.PassphraseRequest,
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_d5f65e),
                request_input(0, TXHASH_d5f65e),
                request_input(1, TXHASH_d5f65e),
                request_output(0, TXHASH_d5f65e),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )
        btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TxCache("Bitcoin"))


# def test_firmware_erase():
#    pass

# def test_firmware_upload():
#    pass


@pytest.mark.setup_client(pin=PIN4, passphrase=False)
def test_unlocked(client):
    assert client.features.unlocked is False

    _assert_protection(client, passphrase=False)
    with client:
        client.use_pin_sequence([PIN4])
        client.set_expected_responses([_pin_request(client), messages.Address])
        get_test_address(client)

    client.init_device()
    assert client.features.unlocked is True
    with client:
        client.set_expected_responses([messages.Address])
        get_test_address(client)


@pytest.mark.setup_client(pin=None, passphrase=True)
def test_passphrase_cached(client):
    _assert_protection(client, pin=False)
    with client:
        client.set_expected_responses([messages.PassphraseRequest, messages.Address])
        get_test_address(client)

    with client:
        client.set_expected_responses([messages.Address])
        get_test_address(client)
