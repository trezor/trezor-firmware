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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure

from ...common import EXTERNAL_ENTROPY, MNEMONIC12, WITH_MOCK_URANDOM, generate_entropy
from ...input_flows import (
    InputFlowBip39ResetBackup,
    InputFlowBip39ResetFailedCheck,
    InputFlowBip39ResetPIN,
)

pytestmark = [pytest.mark.skip_t1]


def reset_device(client: Client, strength: int):
    with WITH_MOCK_URANDOM, client:
        IF = InputFlowBip39ResetBackup(client)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
        )

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False
    assert resp.backup_type is messages.BackupType.Bip39

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device(client: Client):
    reset_device(client, 128)  # 12 words


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_192(client: Client):
    reset_device(client, 192)  # 18 words


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_pin(client: Client):
    strength = 256  # 24 words

    with WITH_MOCK_URANDOM, client:
        IF = InputFlowBip39ResetPIN(client)
        client.set_input_flow(IF.get())

        # PIN, passphrase, display random
        device.reset(
            client,
            display_random=True,
            strength=strength,
            passphrase_protection=True,
            pin_protection=True,
            label="test",
        )

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is True
    assert resp.passphrase_protection is True


@pytest.mark.setup_client(uninitialized=True)
def test_reset_failed_check(client: Client):
    strength = 256  # 24 words

    with WITH_MOCK_URANDOM, client:
        IF = InputFlowBip39ResetFailedCheck(client)
        client.set_input_flow(IF.get())

        # PIN, passphrase, display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
        )

    # generate mnemonic locally
    internal_entropy = client.debug.state().reset_entropy
    entropy = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)
    expected_mnemonic = Mnemonic("english").to_mnemonic(entropy)

    # Compare that device generated proper mnemonic for given entropies
    assert IF.mnemonic == expected_mnemonic

    # Check if device is properly initialized
    resp = client.call_raw(messages.Initialize())
    assert resp.initialized is True
    assert resp.needs_backup is False
    assert resp.pin_protection is False
    assert resp.passphrase_protection is False
    assert resp.backup_type is messages.BackupType.Bip39


@pytest.mark.setup_client(uninitialized=True)
def test_failed_pin(client: Client):
    strength = 128
    ret = client.call_raw(
        messages.ResetDevice(strength=strength, pin_protection=True, label="test")
    )

    # Confirm Reset
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    # Enter PIN for first time
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.input("654")
    ret = client.call_raw(messages.ButtonAck())

    # Re-enter PIN for TR
    if client.debug.model == "Safe 3":
        assert isinstance(ret, messages.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(messages.ButtonAck())

    # Enter PIN for second time
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.input("456")
    ret = client.call_raw(messages.ButtonAck())

    # PIN mismatch
    assert isinstance(ret, messages.ButtonRequest)
    client.debug.press_yes()
    ret = client.call_raw(messages.ButtonAck())

    assert isinstance(ret, messages.ButtonRequest)


@pytest.mark.setup_client(mnemonic=MNEMONIC12)
def test_already_initialized(client: Client):
    with pytest.raises(Exception):
        device.reset(client, False, 128, True, True, "label")
