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

from .common import *


@pytest.mark.ethereum
class TestMsgEthereumVerifymessage(TrezorTest):

    ADDRESS = b'cb3864960e8db1a751212c580af27ee8867d688f'
    VECTORS = [
        ('This is an example of a signed message.', b'b7837058907192dbc9427bf57d93a0acca3816c92927a08be573b785f2d72dab65dad9c92fbe03a358acdb455eab2107b869945d11f4e353d9cc6ea957d08a871b'),
        ('VeryLongMessage!' * 64, b'da2b73b0170479c2bfba3dd4839bf0d67732a44df8c873f3f3a2aca8a57d7bdc0b5d534f54c649e2d44135717001998b176d3cd1212366464db51f5838430fb31c'),
    ]

    def test_verify(self):
        self.setup_mnemonic_nopin_nopassphrase()
        for msg, sig in self.VECTORS:
            res = self.client.ethereum_verify_message(
                unhexlify(self.ADDRESS),
                unhexlify(sig),
                msg
            )
            assert res is True
