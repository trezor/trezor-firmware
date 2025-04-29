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
from shamir_mnemonic import shamir

from trezorlib import device
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import BackupAvailability, BackupType

from ...common import EXTERNAL_ENTROPY, MOCK_GET_ENTROPY, generate_entropy
from ...input_flows import InputFlowSlip39AdvancedResetRecovery

pytestmark = pytest.mark.models("core")


# TODO: test with different options
@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_slip39_advanced(client: Client):
    strength = 128
    member_threshold = 3

    session = client.get_seedless_session()
    with session.client as client:
        IF = InputFlowSlip39AdvancedResetRecovery(client, False)
        client.set_input_flow(IF.get())
        # No PIN, no passphrase, don't display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            backup_type=BackupType.Slip39_Advanced,
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    assert internal_entropy is not None
    secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    validate_mnemonics(IF.mnemonics, member_threshold, secret)
    session = client.get_session()
    # Check if device is properly initialized
    assert session.features.initialized is True
    assert session.features.backup_availability == BackupAvailability.NotAvailable
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is BackupType.Slip39_Advanced_Extendable

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(session)


def validate_mnemonics(
    mnemonics: list[str], threshold: int, expected_ems: bytes
) -> None:
    # 3of5 shares 3of5 groups
    # TODO: test all possible group+share combinations?
    test_combination = mnemonics[0:3] + mnemonics[5:8] + mnemonics[10:13]
    groups = shamir.decode_mnemonics(test_combination)
    ems = shamir.recover_ems(groups)
    assert expected_ems == ems.ciphertext
