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

from unittest import mock

import pytest
from shamir_mnemonic import shamir

from trezorlib import device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.messages import BackupType, ButtonRequestType as B

from ...common import generate_entropy
from ...input_flows import InputFlowSlip39AdvancedResetRecovery

pytestmark = [pytest.mark.skip_t1]

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2


# TODO: test with different options
@pytest.mark.setup_client(uninitialized=True)
def test_reset_device_slip39_advanced(client: Client):
    strength = 128
    member_threshold = 3

    os_urandom = mock.Mock(return_value=EXTERNAL_ENTROPY)
    with mock.patch("os.urandom", os_urandom), client:
        IF = InputFlowSlip39AdvancedResetRecovery(client, False)
        client.set_input_flow(IF.get())
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.ResetDevice),
                messages.EntropyRequest(),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #1 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #2 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #3 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #4 counts
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.ResetDevice),  # group #5 counts
                messages.ButtonRequest(code=B.ResetDevice),
            ]
            + [
                # individual mnemonic
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
            ]
            * (5 * 5)  # groups * shares
            + [
                messages.ButtonRequest(code=B.Success),
                messages.Success,
                messages.Features,
            ]
        )

        # No PIN, no passphrase, don't display random
        device.reset(
            client,
            display_random=False,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            language="en-US",
            backup_type=BackupType.Slip39_Advanced,
        )

    # generate secret locally
    internal_entropy = client.debug.state().reset_entropy
    secret = generate_entropy(strength, internal_entropy, EXTERNAL_ENTROPY)

    # validate that all combinations will result in the correct master secret
    validate_mnemonics(IF.mnemonics, member_threshold, secret)

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is BackupType.Slip39_Advanced

    # backup attempt fails because backup was done in reset
    with pytest.raises(TrezorFailure, match="ProcessError: Seed already backed up"):
        device.backup(client)


def validate_mnemonics(mnemonics, threshold, expected_ems):
    # 3of5 shares 3of5 groups
    # TODO: test all possible group+share combinations?
    test_combination = mnemonics[0:3] + mnemonics[5:8] + mnemonics[10:13]
    groups = shamir.decode_mnemonics(test_combination)
    ems = shamir.recover_ems(groups)
    assert expected_ems == ems.ciphertext
