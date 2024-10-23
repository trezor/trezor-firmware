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

from itertools import combinations

import pytest
from shamir_mnemonic import MnemonicError, shamir

from trezorlib import device
from trezorlib.btc import get_public_node
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import BackupAvailability, BackupType

from ...common import EXTERNAL_ENTROPY, WITH_MOCK_URANDOM, generate_entropy
from ...input_flows import InputFlowSlip39BasicResetRecovery

pytestmark = pytest.mark.models("core")


def reset_device(client: Client, strength: int):
    member_threshold = 3

    with WITH_MOCK_URANDOM, client:
        IF = InputFlowSlip39BasicResetRecovery(client)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            backup_type=BackupType.Slip39_Basic,
        )

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    validate_mnemonics(IF.mnemonics, member_threshold, secret)

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.backup_availability == BackupAvailability.NotAvailable
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is BackupType.Slip39_Basic_Extendable

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(client)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_slip39_basic(client: Client):
    reset_device(client, 128)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_slip39_basic_256(client: Client):
    reset_device(client, 256)


@pytest.mark.setup_client(uninitialized=True)
def test_reset_entropy_check(client: Client):
    member_threshold = 3

    strength = 128  # 20 words

    with WITH_MOCK_URANDOM, client:
        IF = InputFlowSlip39BasicResetRecovery(client)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase.
        _, path_xpubs = device.reset_entropy_check(
            client,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            backup_type=BackupType.Slip39_Basic,
            entropy_check_count=3,
        )

    # Generate the master secret locally.
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

    # Check that all combinations will result in the correct master secret.
    validate_mnemonics(IF.mnemonics, member_threshold, secret)

    # Check that the device is properly initialized.
    assert client.features.initialized is True
    assert client.features.backup_availability == BackupAvailability.NotAvailable
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is BackupType.Slip39_Basic_Extendable

    # Check that the XPUBs are the same as those from the entropy check.
    for path, xpub in path_xpubs:
        res = get_public_node(client, path)
        assert res.xpub == xpub


def validate_mnemonics(mnemonics, threshold, expected_ems):
    # We expect these combinations to recreate the secret properly
    for test_group in combinations(mnemonics, threshold):
        groups = shamir.decode_mnemonics(test_group)
        ems = shamir.recover_ems(groups)
        assert expected_ems == ems.ciphertext
    # We expect these combinations to raise MnemonicError
    for test_group in combinations(mnemonics, threshold - 1):
        with pytest.raises(MnemonicError, match=f".*Expected {threshold} mnemonics.*"):
            shamir.combine_mnemonics(test_group)
