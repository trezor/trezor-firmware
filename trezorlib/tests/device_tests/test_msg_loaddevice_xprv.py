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

from .common import *


@pytest.mark.skip_t2
class TestDeviceLoadXprv(TrezorTest):

    def test_load_device_xprv_1(self):
        self.client.load_device_by_xprv(xprv='xprv9s21ZrQH143K2JF8RafpqtKiTbsbaxEeUaMnNHsm5o6wCW3z8ySyH4UxFVSfZ8n7ESu7fgir8imbZKLYVBxFPND1pniTZ81vKfd45EHKX73', pin='', passphrase_protection=False, label='test', language='english')

        passphrase_protection = self.client.debug.read_passphrase_protection()
        assert passphrase_protection is False

        address = self.client.get_address('Bitcoin', [])
        assert address == '128RdrAkJDmqasgvfRf6MC5VcX4HKqH4mR'

    def test_load_device_xprv_2(self):
        self.client.load_device_by_xprv(xprv='xprv9s21ZrQH143K2JF8RafpqtKiTbsbaxEeUaMnNHsm5o6wCW3z8ySyH4UxFVSfZ8n7ESu7fgir8imbZKLYVBxFPND1pniTZ81vKfd45EHKX73', pin='', passphrase_protection=True, label='test', language='english')

        self.client.set_passphrase('passphrase')

        passphrase_protection = self.client.debug.read_passphrase_protection()
        assert passphrase_protection is True

        address = self.client.get_address('Bitcoin', [])
        assert address == '1CHUbFa4wTTPYgkYaw2LHSd5D4qJjMU8ri'
