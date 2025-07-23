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

from typing import Generator

import pytest
from mnemonic import Mnemonic
from slip10 import SLIP10

from trezorlib import device, messages
from trezorlib.btc import get_public_node
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import (
    EXTERNAL_ENTROPY,
    MOCK_GET_ENTROPY,
    BRGeneratorType,
    generate_entropy,
)

pytestmark = pytest.mark.models("legacy")


def reset_device(session: Session, strength: int):
    debug = session.client.debug
    # No PIN, no passphrase
    ret = session.call_raw(
        messages.ResetDevice(
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
        )
    )

    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    # Provide entropy
    assert isinstance(ret, messages.EntropyRequest)
    internal_entropy = debug.state().reset_entropy
    ret = session.call_raw(messages.EntropyAck(entropy=EXTERNAL_ENTROPY))

    # Generate mnemonic locally
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    mnemonic = []
    for _ in range(strength // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(session.client.debug.read_reset_word())
        session.client.debug.press_yes()
        session.call_raw(messages.ButtonAck())

    mnemonic = " ".join(mnemonic)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    mnemonic = []
    for _ in range(strength // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(session.client.debug.read_reset_word())
        debug.press_yes()
        resp = session.call_raw(messages.ButtonAck())

    assert isinstance(resp, messages.Success)

    mnemonic = " ".join(mnemonic)

    # Compare that second pass printed out the same mnemonic once again
    assert mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = session.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.backup_availability == messages.BackupAvailability.NotAvailable
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False

    # Do pin & passphrase-protected action, PassphraseRequest should NOT be raised
    resp = session.call_raw(
        messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0"))
    )
    assert isinstance(resp, messages.Address)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_128(session: Session):
    reset_device(session, 128)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_192(session: Session):
    reset_device(session, 192)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_256_pin(session: Session):
    debug = session.client.debug
    strength = 256

    ret = session.call_raw(
        messages.ResetDevice(
            strength=strength,
            passphrase_protection=True,
            pin_protection=True,
            label="test",
        )
    )

    # Do you want ... ?
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for first time
    pin_encoded = debug.encode_pin("654")
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for second time
    pin_encoded = debug.encode_pin("654")
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    # Provide entropy
    assert isinstance(ret, messages.EntropyRequest)
    internal_entropy = debug.state().reset_entropy
    ret = session.call_raw(messages.EntropyAck(entropy=EXTERNAL_ENTROPY))

    # Generate mnemonic locally
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    mnemonic = []
    for _ in range(strength // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(debug.read_reset_word())
        debug.press_yes()
        session.call_raw(messages.ButtonAck())

    mnemonic = " ".join(mnemonic)

    # Compare that device generated proper mnemonic for given entropies
    assert mnemonic == expected_mnemonic

    mnemonic = []
    for _ in range(strength // 32 * 3):
        assert isinstance(ret, messages.ButtonRequest)
        mnemonic.append(debug.read_reset_word())
        debug.press_yes()
        resp = session.call_raw(messages.ButtonAck())

    assert isinstance(resp, messages.Success)

    mnemonic = " ".join(mnemonic)

    # Compare that second pass printed out the same mnemonic once again
    assert mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = session.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.backup_availability == messages.BackupAvailability.NotAvailable
    assert resp.pin_protection is True
    assert resp.passphrase_protection is True

    # Do passphrase-protected action, PassphraseRequest should be raised
    resp = session.call_raw(
        messages.GetAddress(address_n=parse_path("m/44'/0'/0'/0/0"))
    )
    assert isinstance(resp, messages.PassphraseRequest)
    session.call_raw(messages.Cancel())


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_failed_pin(session: Session):
    debug = session.client.debug
    strength = 128

    ret = session.call_raw(
        messages.ResetDevice(
            strength=strength,
            passphrase_protection=True,
            pin_protection=True,
            label="test",
        )
    )

    # Do you want ... ?
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for first time
    pin_encoded = debug.encode_pin("1234")
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))
    assert isinstance(ret, messages.PinMatrixRequest)

    # Enter PIN for second time
    pin_encoded = debug.encode_pin("6789")
    ret = session.call_raw(messages.PinMatrixAck(pin=pin_encoded))

    assert isinstance(ret, messages.Failure)


def test_already_initialized(session: Session):
    with pytest.raises(Exception):
        device.setup(
            session,
            strength=128,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
        )


class Bip39InputFlow:
    def __init__(self, client: Client):
        self.client = client
        self.mnemonic = None

    def _get_mnemonic(
        self, strength: int
    ) -> Generator[None, messages.ButtonRequest, list[str]]:
        mnemonic: list[str] = []
        for _ in range(strength // 32 * 3):
            br = yield
            assert br.code == messages.ButtonRequestType.ConfirmWord
            mnemonic.append(self.client.debug.read_reset_word())
            self.client.debug.press_yes()
        return mnemonic

    def input_flow_bip39_reset_backup(self, strength: int) -> BRGeneratorType:
        # 1. Confirm Reset
        br = yield
        assert br.code == messages.ButtonRequestType.ProtectCall
        self.client.debug.press_yes()

        mnemonic_write = yield from self._get_mnemonic(strength)
        mnemonic_check = yield from self._get_mnemonic(strength)
        assert mnemonic_write == mnemonic_check

        self.mnemonic = " ".join(mnemonic_write)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_entropy_check(session: Session):
    strength = 256  # 24 words

    with session.client as client:
        IF = Bip39InputFlow(client)
        client.set_input_flow(IF.input_flow_bip39_reset_backup(strength))
        # No PIN, no passphrase
        path_xpubs = device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=2,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # Check that the displayed mnemonic is identical to the stored one.
    assert IF.mnemonic.encode("utf-8") == client.debug.state().mnemonic_secret

    # Check that the device is properly initialized.
    assert client.features.initialized is True
    assert (
        client.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    seed = Mnemonic.to_seed(IF.mnemonic, passphrase="")
    slip10 = SLIP10.from_seed(seed)

    session = session.client.get_session()
    for path, xpub in path_xpubs:
        # Check that the device returns the same XPUBs as those from the entropy check.
        res = get_public_node(session, path)
        assert res.xpub == xpub
        # Check that the XPUBs derived from the displayed mnemonic are the same as those
        # from the entropy check.
        assert slip10.get_xpub_from_path(path) == xpub


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_entropy_check(session: Session):
    with session.client as client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.EntropyRequest,
                messages.EntropyCheckReady,
                messages.PublicKey,
                messages.PublicKey,
                messages.EntropyRequest,
                messages.EntropyCheckReady,
                messages.PublicKey,
                messages.PublicKey,
                messages.EntropyRequest,
                messages.EntropyCheckReady,
                messages.PublicKey,
                messages.PublicKey,
                messages.Success,
            ]
        )
        device.setup(
            session,
            strength=256,
            entropy_check_count=2,
            backup_type=messages.BackupType.Bip39,
            skip_backup=True,
            pin_protection=False,
            passphrase_protection=False,
            _get_entropy=MOCK_GET_ENTROPY,
        )


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_no_entropy_check(session: Session):
    with session.client as client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=messages.ButtonRequestType.ProtectCall),
                messages.EntropyRequest,
                messages.Success,
            ]
        )
        device.setup(
            session,
            strength=256,
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            skip_backup=True,
            pin_protection=False,
            passphrase_protection=False,
            _get_entropy=MOCK_GET_ENTROPY,
        )
