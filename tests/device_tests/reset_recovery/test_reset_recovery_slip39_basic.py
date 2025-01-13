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

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType
from trezorlib.tools import parse_path

from ...common import WITH_MOCK_URANDOM
from ...input_flows import (
    InputFlowSlip39BasicRecovery,
    InputFlowSlip39BasicResetRecovery,
)
from ...translations import set_language


@pytest.mark.models("core")
@pytest.mark.setup_client(uninitialized=True)
@WITH_MOCK_URANDOM
def test_reset_recovery(client: Client):
    session = client.get_management_session()
    mnemonics = reset(session)
    session = client.get_session()
    address_before = btc.get_address(session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))

    for share_subset in itertools.combinations(mnemonics, 3):
        session = client.get_management_session()
        lang = client.features.language or "en"
        device.wipe(session)
        client = client.get_new_client()
        session = Session(client.get_management_session())
        set_language(session, lang[:2])
        selected_mnemonics = share_subset
        recover(session, selected_mnemonics)
        session = client.get_session()
        address_after = btc.get_address(
            session, "Bitcoin", parse_path("m/44h/0h/0h/0/0")
        )
        assert address_before == address_after


def reset(session: Session, strength: int = 128) -> list[str]:
    with session.client as client:
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

    # Check if device is properly initialized
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is BackupType.Slip39_Basic_Extendable

    return IF.mnemonics


def recover(session: Session, shares: list[str]):
    with session.client as client:
        IF = InputFlowSlip39BasicRecovery(client, shares)
        client.set_input_flow(IF.get())
        ret = device.recover(session, pin_protection=False, label="label")

    # Workflow successfully ended
    assert ret == messages.Success(message="Device recovered")
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
    assert session.features.backup_type is BackupType.Slip39_Basic_Extendable
