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

from trezorlib import btc, device, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.messages import BackupType
from trezorlib.tools import parse_path

from ...common import MOCK_GET_ENTROPY
from ...input_flows import InputFlowBip39Recovery, InputFlowBip39ResetBackup
from ...translations import set_language


@pytest.mark.models("core")
@pytest.mark.setup_client(uninitialized=True)
def test_reset_recovery(client: Client):
    session = client.get_seedless_session()
    mnemonic = reset(session)
    session = client.get_session()
    address_before = btc.get_address(session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))

    lang = client.features.language or "en"
    device.wipe(session)
    client = client.get_new_client()
    session = client.get_seedless_session()
    set_language(session, lang[:2])
    recover(session, mnemonic)
    session = client.get_session()
    address_after = btc.get_address(session, "Bitcoin", parse_path("m/44h/0h/0h/0/0"))
    assert address_before == address_after


def reset(session: Session, strength: int = 128, skip_backup: bool = False) -> str:
    with session.client as client:
        IF = InputFlowBip39ResetBackup(client)
        client.set_input_flow(IF.get())

        # No PIN, no passphrase, don't display random
        device.setup(
            session,
            strength=strength,
            passphrase_protection=False,
            pin_protection=False,
            label="test",
            backup_type=BackupType.Bip39,
            entropy_check_count=0,
            _get_entropy=MOCK_GET_ENTROPY,
        )

    # Check if device is properly initialized
    assert session.features.initialized is True
    assert (
        session.features.backup_availability == messages.BackupAvailability.NotAvailable
    )
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False

    assert IF.mnemonic is not None
    return IF.mnemonic


def recover(session: Session, mnemonic: str):
    words = mnemonic.split(" ")
    with session.client as client:
        IF = InputFlowBip39Recovery(client, words)
        client.set_input_flow(IF.get())
        client.watch_layout()
        device.recover(session, pin_protection=False, label="label")

    # Workflow successfully ended
    assert session.features.pin_protection is False
    assert session.features.passphrase_protection is False
