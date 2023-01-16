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

import itertools
from unittest import mock

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType, ButtonRequestType as B
from trezorlib.tools import parse_path

from ...input_flows import (
    InputFlowSlip39BasicRecovery,
    InputFlowSlip39BasicResetRecovery,
)

EXTERNAL_ENTROPY = b"zlutoucky kun upel divoke ody" * 2
MOCK_OS_URANDOM = mock.Mock(return_value=EXTERNAL_ENTROPY)


@pytest.mark.skip_t1
@pytest.mark.setup_client(uninitialized=True)
@mock.patch("os.urandom", MOCK_OS_URANDOM)
def test_reset_recovery(client: Client):
    mnemonics = reset(client)
    address_before = btc.get_address(client, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))

    for share_subset in itertools.combinations(mnemonics, 3):
        device.wipe(client)
        selected_mnemonics = share_subset
        recover(client, selected_mnemonics)
        address_after = btc.get_address(
            client, "Bitcoin", parse_path("m/44h/0h/0h/0/0")
        )
        assert address_before == address_after


def reset(client: Client, strength: int = 128) -> list[str]:
    with client:
        IF = InputFlowSlip39BasicResetRecovery(client)
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
            ]
            + [
                # individual mnemonic
                messages.ButtonRequest(code=B.ResetDevice),
                messages.ButtonRequest(code=B.Success),
            ]
            * 5  # number of shares
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
            backup_type=BackupType.Slip39_Basic,
            show_tutorial=False,
        )

    # Check if device is properly initialized
    assert client.features.initialized is True
    assert client.features.needs_backup is False
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False

    return IF.mnemonics


def recover(client: Client, shares: list[str]):
    with client:
        IF = InputFlowSlip39BasicRecovery(client, shares)
        client.set_input_flow(IF.get())
        ret = device.recover(
            client, pin_protection=False, label="label", show_tutorial=False
        )

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
