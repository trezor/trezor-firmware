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

import time

import pytest

from trezorlib import btc, device, messages as proto
from trezorlib.messages.PassphraseSourceType import HOST as PASSPHRASE_ON_HOST

from .common import TrezorTest


@pytest.mark.skip_t1
class TestMsgRecoveryDeviceShamir(TrezorTest):
    def test_3of6_nopin_nopassphrase(self):
        # 128 bits security, 3 of 6
        mnemonics = [
            "extra extend academic bishop cricket bundle tofu goat apart victim enlarge program behavior permit course armed jerky faint language modern",
            "extra extend academic acne away best indicate impact square oasis prospect painting voting guest either argue username racism enemy eclipse",
            "extra extend academic arcade born dive legal hush gross briefing talent drug much home firefly toxic analysis idea umbrella slice",
        ]
        word_count = len(mnemonics[0].split(" "))

        ret = self.client.call_raw(
            proto.RecoveryDevice(
                passphrase_protection=False, pin_protection=False, label="label"
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
        self.client.debug.input(str(word_count))
        ret = self.client.call_raw(proto.ButtonAck())

        # Confirm T9 keyboard
        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter shares
        for mnemonic in mnemonics:
            # Enter mnemonic words
            assert ret == proto.ButtonRequest(
                code=proto.ButtonRequestType.MnemonicInput
            )
            self.client.transport.write(proto.ButtonAck())
            for word in mnemonic.split(" "):
                time.sleep(1)
                self.client.debug.input(word)
            ret = self.client.transport.read()

            if mnemonic != mnemonics[-1]:
                # Confirm status
                assert isinstance(ret, proto.ButtonRequest)
                self.client.debug.press_yes()
                ret = self.client.call_raw(proto.ButtonAck())

        # Confirm success
        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Workflow succesfully ended
        assert ret == proto.Success(message="Device recovered")

        assert self.client.features.pin_protection is False
        assert self.client.features.passphrase_protection is False

        # Check mnemonic
        assert (
            self.client.debug.read_mnemonic_secret().hex()
            == "491b795b80fc21ccdf466c0fbc98c8fc"
        )

        # BIP32 Root Key for empty passphrase
        # provided by Andrew, address calculated using T1
        # xprv9s21ZrQH143K3reExTJbGTHPu6mGuUx6yN1H1KkqoiAcw6j1t6hBiwwnXYxNQXxU8T7pANSv1rJYQPXn1LMQk1gbWes5BjSz3rJ5ZfH1cc3
        address = btc.get_address(self.client, "Bitcoin", [])
        assert address == "1G1MwH5sLVxKQ7yKYasfE5pxWaABLo7VK7"

        # TODO: test passphrase in load_device
        # # BIP32 Root Key for passphrase TREZOR
        # # provided by Andrew, address calculated using T1
        # # xprv9s21ZrQH143K2pMWi8jrTawHaj16uKk4CSbvo4Zt61tcrmuUDMx2o1Byzcr3saXNGNvHP8zZgXVdJHsXVdzYFPavxvCyaGyGr1WkAYG83ce
        # self.client.set_passphrase("TREZOR")
        # address = btc.get_address(self.client, "Bitcoin", [])
        # assert address == "18oZEMRWurCZW1FeK8sWYyXuWx2bFqEKyX"

    def test_2of5_pin_passphrase(self):
        # 256 bits security, 2 of 5
        mnemonics = [
            "hobo romp academic axis august founder knife legal recover alien expect emphasis loan kitchen involve teacher capture rebuild trial numb spider forward ladle lying voter typical security quantity hawk legs idle leaves gasoline",
            "hobo romp academic agency ancestor industry argue sister scene midst graduate profile numb paid headset airport daisy flame express scene usual welcome quick silent downtown oral critical step remove says rhythm venture aunt",
        ]
        word_count = len(mnemonics[0].split(" "))

        ret = self.client.call_raw(
            proto.RecoveryDevice(
                passphrase_protection=True, pin_protection=True, label="label"
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
        self.client.debug.input(str(word_count))
        ret = self.client.call_raw(proto.ButtonAck())

        # Confirm T9 keyboard
        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter shares
        for mnemonic in mnemonics:
            # Enter mnemonic words
            assert ret == proto.ButtonRequest(
                code=proto.ButtonRequestType.MnemonicInput
            )
            self.client.transport.write(proto.ButtonAck())
            for word in mnemonic.split(" "):
                time.sleep(1)
                self.client.debug.input(word)
            ret = self.client.transport.read()

            if mnemonic != mnemonics[-1]:
                # Confirm status
                assert isinstance(ret, proto.ButtonRequest)
                self.client.debug.press_yes()
                ret = self.client.call_raw(proto.ButtonAck())

        # Enter PIN for first time
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.Other)
        self.client.debug.input("654")
        ret = self.client.call_raw(proto.ButtonAck())

        # Enter PIN for second time
        assert ret == proto.ButtonRequest(code=proto.ButtonRequestType.Other)
        self.client.debug.input("654")
        ret = self.client.call_raw(proto.ButtonAck())

        # Confirm success
        assert isinstance(ret, proto.ButtonRequest)
        self.client.debug.press_yes()
        ret = self.client.call_raw(proto.ButtonAck())

        # Workflow succesfully ended
        assert ret == proto.Success(message="Device recovered")

        # Check mnemonic
        self.client.init_device()
        assert (
            self.client.debug.read_mnemonic_secret().hex()
            == "b770e0da1363247652de97a39bdbf2463be087848d709ecbf28e84508e31202a"
        )

        assert self.client.features.pin_protection is True
        assert self.client.features.passphrase_protection is True

        device.apply_settings(self.client, passphrase_source=PASSPHRASE_ON_HOST)

        # BIP32 Root Key for empty passphrase
        # provided by Andrew, address calculated using T1
        # xprv9s21ZrQH143K2kP9RYJE5AFggTHLs8PbDaaTYtvh238THxDyXqyqQV6H1QpFr3aaQ7CFusFMYyGZ6VcK7aLADyCaCJrszovxtzVZmnRfca4
        address = btc.get_address(self.client, "Bitcoin", [])
        assert address == "1BmqXKM8M1gWA4bgkbPeCtJruRnrY2qYKP"

        # hackish way to clear passphrase
        # TODO: move this to another test file and test using load_device on a new session
        self.client.state = None
        self.client.init_device()
        self.client.set_passphrase("TREZOR")

        # BIP32 Root Key for passphrase TREZOR
        # provided by Andrew, address calculated using T1
        # xprv9s21ZrQH143K2o6EXEHpVy8TCYoMmkBnDCCESLdR2ieKwmcNG48ck2XJQY4waS7RUQcXqR9N7HnQbUVEDMWYyREdF1idQqxFHuCfK7fqFni

        address = btc.get_address(self.client, "Bitcoin", [])
        assert address == "19Fjs9AvT13Y2Nx8GtoVfADmFWnccsPinQ"
