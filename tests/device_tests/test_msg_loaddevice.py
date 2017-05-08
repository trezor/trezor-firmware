# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import common

from trezorlib import messages_pb2 as messages

class TestDeviceLoad(common.TrezorTest):

    def test_load_device_1(self):
        self.setup_mnemonic_nopin_nopassphrase()

        mnemonic = self.client.debug.read_mnemonic()
        self.assertEqual(mnemonic, self.mnemonic12)

        pin = self.client.debug.read_pin()[0]
        self.assertEqual(pin, '')

        passphrase_protection = self.client.debug.read_passphrase_protection()
        self.assertEqual(passphrase_protection, False)

        address = self.client.get_address('Bitcoin', [])
        self.assertEqual(address, '1EfKbQupktEMXf4gujJ9kCFo83k1iMqwqK')

    def test_load_device_2(self):
        self.setup_mnemonic_pin_passphrase()
        self.client.set_passphrase('passphrase')

        mnemonic = self.client.debug.read_mnemonic()
        self.assertEqual(mnemonic, self.mnemonic12)

        pin = self.client.debug.read_pin()[0]
        self.assertEqual(pin, self.pin4)

        passphrase_protection = self.client.debug.read_passphrase_protection()
        self.assertEqual(passphrase_protection, True)

        address = self.client.get_address('Bitcoin', [])
        self.assertEqual(address, '15fiTDFwZd2kauHYYseifGi9daH2wniDHH')

    def test_load_device_utf(self):
        words_nfkd = u'Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a'
        words_nfc = u'P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f'
        words_nfkc = u'P\u0159\xed\u0161ern\u011b \u017elu\u0165ou\u010dk\xfd k\u016f\u0148 \xfap\u011bl \u010f\xe1belsk\xe9 \xf3dy z\xe1ke\u0159n\xfd u\u010de\u0148 b\u011b\u017e\xed pod\xe9l z\xf3ny \xfal\u016f'
        words_nfd = u'Pr\u030ci\u0301s\u030cerne\u030c z\u030clut\u030couc\u030cky\u0301 ku\u030an\u030c u\u0301pe\u030cl d\u030ca\u0301belske\u0301 o\u0301dy za\u0301ker\u030cny\u0301 uc\u030cen\u030c be\u030cz\u030ci\u0301 pode\u0301l zo\u0301ny u\u0301lu\u030a'

        passphrase_nfkd = u'Neuve\u030cr\u030citelne\u030c bezpec\u030cne\u0301 hesli\u0301c\u030cko'
        passphrase_nfc = u'Neuv\u011b\u0159iteln\u011b bezpe\u010dn\xe9 hesl\xed\u010dko'
        passphrase_nfkc = u'Neuv\u011b\u0159iteln\u011b bezpe\u010dn\xe9 hesl\xed\u010dko'
        passphrase_nfd = u'Neuve\u030cr\u030citelne\u030c bezpec\u030cne\u0301 hesli\u0301c\u030cko'

        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=words_nfkd, pin='', passphrase_protection=True, label='test', language='english', skip_checksum=True)
        self.client.set_passphrase(passphrase_nfkd)
        address_nfkd = self.client.get_address('Bitcoin', [])

        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=words_nfc, pin='', passphrase_protection=True, label='test', language='english', skip_checksum=True)
        self.client.set_passphrase(passphrase_nfc)
        address_nfc = self.client.get_address('Bitcoin', [])

        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=words_nfkc, pin='', passphrase_protection=True, label='test', language='english', skip_checksum=True)
        self.client.set_passphrase(passphrase_nfkc)
        address_nfkc = self.client.get_address('Bitcoin', [])

        self.client.wipe_device()
        self.client.load_device_by_mnemonic(mnemonic=words_nfd, pin='', passphrase_protection=True, label='test', language='english', skip_checksum=True)
        self.client.set_passphrase(passphrase_nfd)
        address_nfd = self.client.get_address('Bitcoin', [])

        self.assertEqual(address_nfkd, address_nfc)
        self.assertEqual(address_nfkd, address_nfkc)
        self.assertEqual(address_nfkd, address_nfd)

if __name__ == '__main__':
    unittest.main()
