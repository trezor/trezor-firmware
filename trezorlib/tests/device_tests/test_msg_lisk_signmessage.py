# This file is part of the TREZOR project.
#
# Copyright (C) 2016-2017 Pavol Rusnak <stick@satoshilabs.com>
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

from binascii import hexlify
import pytest

from .common import TrezorTest


@pytest.mark.lisk
@pytest.mark.skip_t1
class TestMsgLiskSignmessage(TrezorTest):

    def test_sign(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = self.client.lisk_sign_message([2147483692, 2147483782, 2147483648, 2147483648], 'This is an example of a signed message.')
        assert hexlify(sig.public_key) == b'eb56d7bbb5e8ea9269405f7a8527fe126023d1db2c973cfac6f760b60ae27294'
        assert hexlify(sig.signature) == b'7858ae7cd52ea6d4b17e800ca60144423db5560bfd618b663ffbf26ab66758563df45cbffae8463db22dc285dd94309083b8c807776085b97d05374d79867d05'

    def test_sign_long(self):
        self.setup_mnemonic_nopin_nopassphrase()
        sig = self.client.lisk_sign_message([2147483692, 2147483782, 2147483648], 'VeryLongMessage!' * 64)
        assert hexlify(sig.public_key) == b'8bca6b65a1a877767b746ea0b3c4310d404aa113df99c1b554e1802d70185ab5'
        assert hexlify(sig.signature) == b'458ca5896d0934866992268f7509b5e954d568b1251e20c19bd3149ee3c86ffb5a44d1c2a0abbb99a3ab4767272dbb0e419b4579e890a24919ebbbe6cc0f970f'
