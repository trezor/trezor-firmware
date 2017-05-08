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

class TestDeviceLoadXprv(common.TrezorTest):

    def test_load_device_xprv_1(self):
        self.client.load_device_by_xprv(xprv='xprv9s21ZrQH143K2JF8RafpqtKiTbsbaxEeUaMnNHsm5o6wCW3z8ySyH4UxFVSfZ8n7ESu7fgir8imbZKLYVBxFPND1pniTZ81vKfd45EHKX73', pin='', passphrase_protection=False, label='test', language='english')

        passphrase_protection = self.client.debug.read_passphrase_protection()
        self.assertEqual(passphrase_protection, False)

        address = self.client.get_address('Bitcoin', [])
        self.assertEqual(address, '128RdrAkJDmqasgvfRf6MC5VcX4HKqH4mR')

    def test_load_device_xprv_2(self):
        self.client.load_device_by_xprv(xprv='xprv9s21ZrQH143K2JF8RafpqtKiTbsbaxEeUaMnNHsm5o6wCW3z8ySyH4UxFVSfZ8n7ESu7fgir8imbZKLYVBxFPND1pniTZ81vKfd45EHKX73', pin='', passphrase_protection=True, label='test', language='english')

        self.client.set_passphrase('passphrase')

        passphrase_protection = self.client.debug.read_passphrase_protection()
        self.assertEqual(passphrase_protection, True)

        address = self.client.get_address('Bitcoin', [])
        self.assertEqual(address, '1CHUbFa4wTTPYgkYaw2LHSd5D4qJjMU8ri')

if __name__ == '__main__':
    unittest.main()
