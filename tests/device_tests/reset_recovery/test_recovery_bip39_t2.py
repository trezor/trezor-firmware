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

from trezorlib import device, exceptions, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client

from ...common import MNEMONIC12
from ...input_flows import InputFlowBip39Recovery

pytestmark = pytest.mark.models("core")


@pytest.mark.setup_client(uninitialized=True)
def test_tt_pin_passphrase(client: Client):
    with client:
        IF = InputFlowBip39Recovery(client, MNEMONIC12.split(" "), pin="654")
        client.set_input_flow(IF.get())
        device.recover(
            client,
            pin_protection=True,
            passphrase_protection=True,
            label="hello",
        )

    assert client.debug.state().mnemonic_secret.decode() == MNEMONIC12

    assert client.features.pin_protection is True
    assert client.features.passphrase_protection is True
    assert client.features.backup_type is messages.BackupType.Bip39
    assert client.features.label == "hello"


@pytest.mark.setup_client(uninitialized=True)
def test_tt_nopin_nopassphrase(client: Client):
    with client:
        IF = InputFlowBip39Recovery(client, MNEMONIC12.split(" "))
        client.set_input_flow(IF.get())
        device.recover(
            client,
            pin_protection=False,
            passphrase_protection=False,
            label="hello",
        )

    assert client.debug.state().mnemonic_secret.decode() == MNEMONIC12
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Bip39
    assert client.features.label == "hello"


def test_already_initialized(client: Client):
    with pytest.raises(RuntimeError):
        device.recover(client)

    with pytest.raises(exceptions.TrezorFailure, match="Already initialized"):
        client.call(messages.RecoveryDevice())
