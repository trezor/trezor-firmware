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

from trezorlib import device, messages as proto

from ..common import MNEMONIC12


@pytest.mark.skip_t1
class TestMsgRecoverydeviceT2:
    @pytest.mark.setup_client(uninitialized=True)
    def test_pin_passphrase(self, client):
        mnemonic = MNEMONIC12.split(" ")
        ret = client.call_raw(
            proto.RecoveryDevice(
                passphrase_protection=True,
                pin_protection=True,
                label="label",
                enforce_wordlist=True,
            )
        )

        # Confirm Recovery
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Enter PIN for first time
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.Other)
        client.debug.input("654")
        ret = client.call_raw(proto.ButtonAck())

        # Enter PIN for second time
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.Other)
        client.debug.input("654")
        ret = client.call_raw(proto.ButtonAck())

        # Homescreen
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Enter word count
        assert ret == proto.ButtonRequest(
            code=proto.ButtonRequestType.MnemonicWordCount
        )
        client.debug.input(str(len(mnemonic)))
        ret = client.call_raw(proto.ButtonAck())

        # Homescreen
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Enter mnemonic words
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.MnemonicInput)
        client.transport.write(proto.ButtonAck())
        for word in mnemonic:
            client.debug.input(word)
        ret = client.transport.read()

        # Confirm success
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Workflow succesfully ended
        assert ret == proto.Success(message="Device recovered")

        # Mnemonic is the same
        client.init_device()
        assert client.debug.read_mnemonic_secret() == MNEMONIC12.encode()

        assert client.features.pin_protection is True
        assert client.features.passphrase_protection is True

    @pytest.mark.setup_client(uninitialized=True)
    def test_nopin_nopassphrase(self, client):
        mnemonic = MNEMONIC12.split(" ")
        ret = client.call_raw(
            proto.RecoveryDevice(
                passphrase_protection=False,
                pin_protection=False,
                label="label",
                enforce_wordlist=True,
            )
        )

        # Confirm Recovery
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Homescreen
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Enter word count
        assert ret == proto.ButtonRequest(
            code=proto.ButtonRequestType.MnemonicWordCount
        )
        client.debug.input(str(len(mnemonic)))
        ret = client.call_raw(proto.ButtonAck())

        # Homescreen
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Enter mnemonic words
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.MnemonicInput)
        client.transport.write(proto.ButtonAck())
        for word in mnemonic:
            client.debug.input(word)
        ret = client.transport.read()

        # Confirm success
        assert isinstance(ret, proto.ButtonRequest)
        client.debug.press_yes()
        ret = client.call_raw(proto.ButtonAck())

        # Workflow succesfully ended
        assert ret == proto.Success(message="Device recovered")

        # Mnemonic is the same
        client.init_device()
        assert client.debug.read_mnemonic_secret() == MNEMONIC12.encode()

        assert client.features.pin_protection is False
        assert client.features.passphrase_protection is False
        assert client.features.backup_type is proto.BackupType.Bip39

    def test_already_initialized(self, client):
        with pytest.raises(RuntimeError):
            device.recover(
                client, 12, False, False, "label", "english", client.mnemonic_callback
            )
