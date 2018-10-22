# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import time

import pytest

from trezorlib import device, messages as proto

from .common import TrezorTest


@pytest.mark.skip_t1
class TestMsgRecoverydeviceT2(TrezorTest):
    def test_pin_passphrase(self):
        mnemonic = self.mnemonic12.split(" ")
        ret = self.client.call_raw(
            proto.RecoveryDevice(
                passphrase_protection=True,
                pin_protection=True,
                label="label",
                enforce_wordlist=True,
            )
        )

        # Confirm Recovery
        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter word count
        assert ret == proto.ButtonRequest(
            code=proto.ButtonRequestType.MnemonicWordCount
        )
        self.client.debug.input(str(len(mnemonic)))
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter mnemonic words
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.MnemonicInput)
        self.client.transport.write(proto.ButtonAck())
        for word in mnemonic:
            time.sleep(1)
            self.client.debug.input(word)
        ret = self.client.transport.read()

        # Enter PIN for first time
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.Other)
        self.client.debug.input("654")
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter PIN for second time
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.Other)
        self.client.debug.input("654")
        ret = self.client.call_raw(proto.ButtonAck())

        # Workflow succesfully ended
        assert ret == proto.Success(message="Device recovered")

        # Mnemonic is the same
        self.client.init_device()
        assert self.client.debug.read_mnemonic() == self.mnemonic12

        assert self.client.features.pin_protection is True
        assert self.client.features.passphrase_protection is True

    def test_nopin_nopassphrase(self):
        mnemonic = self.mnemonic12.split(" ")
        ret = self.client.call_raw(
            proto.RecoveryDevice(
                passphrase_protection=False,
                pin_protection=False,
                label="label",
                enforce_wordlist=True,
            )
        )

        # Confirm Recovery
        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter word count
        assert ret == proto.ButtonRequest(
            code=proto.ButtonRequestType.MnemonicWordCount
        )
        self.client.debug.input(str(len(mnemonic)))
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter mnemonic words
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.MnemonicInput)
        self.client.transport.write(proto.ButtonAck())
        for word in mnemonic:
            time.sleep(1)
            self.client.debug.input(word)
        ret = self.client.transport.read()

        # Workflow succesfully ended
        assert ret == proto.Success(message="Device recovered")

        # Mnemonic is the same
        self.client.init_device()
        assert self.client.debug.read_mnemonic() == self.mnemonic12

        assert self.client.features.pin_protection is False
        assert self.client.features.passphrase_protection is False

    def test_already_initialized(self):
        self.setup_mnemonic_nopin_nopassphrase()
        with pytest.raises(RuntimeError):
            device.recover(
                self.client,
                12,
                False,
                False,
                "label",
                "english",
                self.client.mnemonic_callback,
            )
