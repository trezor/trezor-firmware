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

from ...common import MNEMONIC12

pytestmark = pytest.mark.skip_t1


@pytest.mark.setup_client(uninitialized=True)
def test_tt_pin_passphrase(client):
    layout = client.debug.wait_layout
    mnemonic = MNEMONIC12.split(" ")

    def input_flow():
        yield
        assert "Do you really want to recover a wallet?" in layout().text
        client.debug.press_yes()

        yield
        assert layout().text == "PinDialog"
        client.debug.input("654")

        yield
        assert layout().text == "PinDialog"
        client.debug.input("654")

        yield
        assert "Select number of words" in layout().text
        client.debug.press_yes()

        yield
        assert "WordSelector" in layout().text
        client.debug.input(str(len(mnemonic)))

        yield
        assert "Enter recovery seed" in layout().text
        client.debug.press_yes()

        yield
        for word in mnemonic:
            assert layout().text == "Bip39Keyboard"
            client.debug.input(word)

        yield
        assert "You have successfully recovered your wallet." in layout().text
        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.watch_layout()
        device.recover(
            client, pin_protection=True, passphrase_protection=True, label="hello"
        )

    assert client.debug.state().mnemonic_secret.decode() == MNEMONIC12

    assert client.features.pin_protection is True
    assert client.features.passphrase_protection is True
    assert client.features.backup_type is messages.BackupType.Bip39
    assert client.features.label == "hello"


@pytest.mark.setup_client(uninitialized=True)
def test_tt_nopin_nopassphrase(client):
    layout = client.debug.wait_layout
    mnemonic = MNEMONIC12.split(" ")

    def input_flow():
        yield
        assert "Do you really want to recover a wallet?" in layout().text
        client.debug.press_yes()

        yield
        assert "Select number of words" in layout().text
        client.debug.press_yes()

        yield
        assert "WordSelector" in layout().text
        client.debug.input(str(len(mnemonic)))

        yield
        assert "Enter recovery seed" in layout().text
        client.debug.press_yes()

        yield
        for word in mnemonic:
            assert layout().text == "Bip39Keyboard"
            client.debug.input(word)

        yield
        assert "You have successfully recovered your wallet." in layout().text
        client.debug.press_yes()

    with client:
        client.set_input_flow(input_flow)
        client.watch_layout()
        device.recover(
            client, pin_protection=False, passphrase_protection=False, label="hello"
        )

    assert client.debug.state().mnemonic_secret.decode() == MNEMONIC12
    assert client.features.pin_protection is False
    assert client.features.passphrase_protection is False
    assert client.features.backup_type is messages.BackupType.Bip39
    assert client.features.label == "hello"


def test_already_initialized(client):
    with pytest.raises(RuntimeError):
        device.recover(client)

    with pytest.raises(exceptions.TrezorFailure, match="Already initialized"):
        client.call(messages.RecoveryDevice())
