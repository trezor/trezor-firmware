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

import pytest

from trezorlib import btc, debuglink, device

from .common import TrezorTest


@pytest.mark.skip_t2
class TestDeviceLoad(TrezorTest):
    def test_load_device_1(self):
        self.setup_mnemonic_nopin_nopassphrase()
        state = self.client.debug.state()
        assert state.mnemonic == self.mnemonic12
        assert state.pin is None
        assert state.passphrase_protection is False

        address = btc.get_address(self.client, "Bitcoin", [])
        assert address == "1EfKbQupktEMXf4gujJ9kCFo83k1iMqwqK"

    def test_load_device_2(self):
        self.setup_mnemonic_pin_passphrase()
        self.client.set_passphrase("passphrase")
        state = self.client.debug.state()
        assert state.mnemonic == self.mnemonic12
        assert state.pin == self.pin4
        assert state.passphrase_protection is True

        address = btc.get_address(self.client, "Bitcoin", [])
        assert address == "15fiTDFwZd2kauHYYseifGi9daH2wniDHH"

    def test_load_device_utf(self):
        words_nfkd = u"Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"
        words_nfc = u"P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"
        words_nfkc = u"P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f"
        words_nfd = u"Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a"

        passphrase_nfkd = (
            u"Neuve\u030cr\u030citelne\u030c bezpec\u030cne\u0301 hesli\u0301c\u030cko"
        )
        passphrase_nfc = (
            u"Neuv\u011b\u0159iteln\u011b bezpe\u010dn\xe9 hesl\xed\u010dko"
        )
        passphrase_nfkc = (
            u"Neuv\u011b\u0159iteln\u011b bezpe\u010dn\xe9 hesl\xed\u010dko"
        )
        passphrase_nfd = (
            u"Neuve\u030cr\u030citelne\u030c bezpec\u030cne\u0301 hesli\u0301c\u030cko"
        )

        device.wipe(self.client)
        debuglink.load_device_by_mnemonic(
            self.client,
            mnemonic=words_nfkd,
            pin="",
            passphrase_protection=True,
            label="test",
            language="english",
            skip_checksum=True,
        )
        self.client.set_passphrase(passphrase_nfkd)
        address_nfkd = btc.get_address(self.client, "Bitcoin", [])

        device.wipe(self.client)
        debuglink.load_device_by_mnemonic(
            self.client,
            mnemonic=words_nfc,
            pin="",
            passphrase_protection=True,
            label="test",
            language="english",
            skip_checksum=True,
        )
        self.client.set_passphrase(passphrase_nfc)
        address_nfc = btc.get_address(self.client, "Bitcoin", [])

        device.wipe(self.client)
        debuglink.load_device_by_mnemonic(
            self.client,
            mnemonic=words_nfkc,
            pin="",
            passphrase_protection=True,
            label="test",
            language="english",
            skip_checksum=True,
        )
        self.client.set_passphrase(passphrase_nfkc)
        address_nfkc = btc.get_address(self.client, "Bitcoin", [])

        device.wipe(self.client)
        debuglink.load_device_by_mnemonic(
            self.client,
            mnemonic=words_nfd,
            pin="",
            passphrase_protection=True,
            label="test",
            language="english",
            skip_checksum=True,
        )
        self.client.set_passphrase(passphrase_nfd)
        address_nfd = btc.get_address(self.client, "Bitcoin", [])

        assert address_nfkd == address_nfc
        assert address_nfkd == address_nfkc
        assert address_nfkd == address_nfd
