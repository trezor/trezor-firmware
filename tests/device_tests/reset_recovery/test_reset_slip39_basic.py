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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import BackupAvailability, BackupType

from ...common import EXTERNAL_ENTROPY, WITH_MOCK_URANDOM, generate_entropy
from ...input_flows import InputFlowSlip39BasicResetRecovery

pytestmark = pytest.mark.models("core")


def reset_device(session: Session, strength: int):
    member_threshold = 3

    with WITH_MOCK_URANDOM, session.client as client:
        IF = InputFlowSlip39BasicResetRecovery(client)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.reset(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            backup_type=BackupType.Slip39_Basic,
        )

    # generate secret locally
    internal_entropy = session.client.debug.state().reset_entropy
    secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    validate_mnemonics(IF.mnemonics, member_threshold, secret)
    session = session.client.get_session()
    # Check if device is properly initialized
    assert session.features.initialized is True
    assert session.features.backup_availability == BackupAvailability.NotAvailable
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is BackupType.Slip39_Basic_Extendable

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(session)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_slip39_basic(session: Session):
    reset_device(session, 128)


@pytest.mark.setup_client(uninitialized=True)
@pytest.mark.uninitialized_session
def test_reset_device_slip39_basic_256(session: Session):
    reset_device(session, 256)


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
