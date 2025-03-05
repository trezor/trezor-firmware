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
from mnemonic import Mnemonic

from trezorlib import device, messages
from trezorlib.btc import get_public_node
from trezorlib.debuglink import LayoutType
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure

from ...common import EXTERNAL_ENTROPY, MNEMONIC12, MOCK_GET_ENTROPY, generate_entropy
from ...input_flows import (
    InputFlowBip39ResetBackup,
    InputFlowBip39ResetFailedCheck,
    InputFlowBip39ResetPIN,
)

pytestmark = pytest.mark.models("core")


def reset_device(session: Session, strength: int):
    debug = session.client.debug
    with session.client as client:
        IF = InputFlowBip39ResetBackup(session.client)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate mnemonic locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = session.call_raw(messages.GetFeatures())
    assert resp.initialized is True
    assert resp.backup_availability == messages.BackupAvailability.NotAvailable
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False
    assert resp.backup_type is messages.BackupType.Bip39

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(session)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device(session: Session):
    reset_device(session, 128)  # 12 words


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_192(session: Session):
    reset_device(session, 192)  # 18 words


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_pin(session: Session):
    debug = session.client.debug
    strength = 256  # 24 words

    with session.client as client:
        IF = InputFlowBip39ResetPIN(session.client)
        client.set_input_flow(IF.get())

        # PIN, passphrase, display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=True,
            pin_protection=True,
            label="test",
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate mnemonic locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = session.call_raw(messages.GetFeatures())
    assert resp.initialized is True
    assert resp.backup_availability == messages.BackupAvailability.NotAvailable
    assert resp.pin_protection is True
    assert resp.passphrase_protection is True


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_entropy_check(session: Session):
    strength = 128  # 12 words

    with session.client as client:
        IF = InputFlowBip39ResetBackup(session.client)
        client.set_input_flow(IF.get())

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

    # Generate the mnemonic locally.
    internal_entropy = session.client.debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Check that the device generated the correct mnemonic for the given entropies.
    assert IF.mnemonic == expected_mnemonic

    # Check that the device is properly initialized.
    features = session.refresh_features()

    assert features.initialized is True
    assert features.backup_availability == messages.BackupAvailability.NotAvailable
    assert features.pin_protection is False
    assert features.passphrase_protection is False
    assert features.backup_type is messages.BackupType.Bip39

    # Check that the XPUBs are the same as those from the entropy check.
    session = session.client.get_session()
    for path, xpub in path_xpubs:
        res = get_public_node(session, path)
        assert res.xpub == xpub


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_failed_check(session: Session):
    debug = session.client.debug
    strength = 256  # 24 words

    with session.client as client:
        IF = InputFlowBip39ResetFailedCheck(session.client)
        client.set_input_flow(IF.get())

        # PIN, passphrase, display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate mnemonic locally
    internal_entropy = debug.state().reset_entropy
    assert internal_entropy is not None
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = session.call_raw(messages.GetFeatures())
    assert resp.initialized is True
    assert resp.backup_availability == messages.BackupAvailability.NotAvailable
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False
    assert resp.backup_type is messages.BackupType.Bip39


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_failed_pin(session: Session):
    debug = session.client.debug
    strength = 128
    ret = session.call_raw(
        messages.ResetDevice(strength=strength, pin_protection=True, label="test")
    )

    # Confirm Reset
    assert isinstance(ret, messages.ButtonRequest)

    session._write(messages.ButtonAck())
    debug.press_yes()

    # Enter PIN for first time
    debug.input("654")
    ret = session.call_raw(messages.ButtonAck())  # XXX stuck here

    # Re-enter PIN for TR
    if session.client.layout_type is LayoutType.Caesar:
        assert isinstance(ret, messages.ButtonRequest)
        debug.press_yes()
        ret = session.call_raw(messages.ButtonAck())

    # Enter PIN for second time
    assert isinstance(ret, messages.ButtonRequest)
    debug.input("456")
    ret = session.call_raw(messages.ButtonAck())

    # PIN mismatch
    assert isinstance(ret, messages.ButtonRequest)
    debug.press_yes()
    ret = session.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.ButtonRequest)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_already_initialized(session: Session):
    with pytest.raises(Exception):
        device.setup(
            session,
            strength=128,
            passphrase_protection=True,
            pin_protection=True,
            label="label",
        )


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_entropy_check(session: Session):
    with session.client as client:
        delizia = session.client.debug.layout_type is LayoutType.Delizia
        delizia_eckhart = session.client.debug.layout_type in (
            LayoutType.Delizia,
            LayoutType.Eckhart,
        )
        client.set_expected_responses(
            [
                messages.ButtonRequest(name="setup_device"),
                (delizia, messages.ButtonRequest(name="confirm_setup_device")),
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
                (delizia_eckhart, messages.ButtonRequest(name="backup_device")),
                messages.Success,
            ]
        )
        device.setup(
            session,
            strength=128,
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
        delizia_eckhart = session.client.debug.layout_type in (
            LayoutType.Delizia,
            LayoutType.Eckhart,
        )
        delizia = session.client.debug.layout_type is LayoutType.Delizia
        client.set_expected_responses(
            [
                messages.ButtonRequest(name="setup_device"),
                (delizia, messages.ButtonRequest(name="confirm_setup_device")),
                messages.EntropyRequest,
                (delizia_eckhart, messages.ButtonRequest(name="backup_device")),
                messages.Success,
            ]
        )
        device.setup(
            session,
            strength=128,
            entropy_check_count=0,
            backup_type=messages.BackupType.Bip39,
            skip_backup=True,
            pin_protection=False,
            passphrase_protection=False,
            _get_entropy=MOCK_GET_ENTROPY,
        )
