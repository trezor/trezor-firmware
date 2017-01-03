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
import trezorlib.ckd_public as bip32
import binascii

class TestMsgEthereumGetaddress(common.TrezorTest):

    def test_ethereum_getaddress(self):
        self.setup_mnemonic_nopin_nopassphrase()
        self.assertEqual(binascii.hexlify(self.client.ethereum_get_address([])), '1d1c328764a41bda0492b66baa30c4a339ff85ef')
        self.assertEqual(binascii.hexlify(self.client.ethereum_get_address([1])), '437207ca3cf43bf2e47dea0756d736c5df4f597a')
        self.assertEqual(binascii.hexlify(self.client.ethereum_get_address([0, -1])), 'e5d96dfa07bcf1a3ae43677840c31394258861bf')
        self.assertEqual(binascii.hexlify(self.client.ethereum_get_address([-9, 0])), 'f68804ac9eca9483ab4241d3e4751590d2c05102')
        self.assertEqual(binascii.hexlify(self.client.ethereum_get_address([0, 9999999])), '7a6366ecfcaf0d5dcc1539c171696c6cdd1eb8ed')

if __name__ == '__main__':
    unittest.main()
