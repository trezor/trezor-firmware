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
from trezorlib import messages as proto
import trezorlib.ckd_public as bip32


class TestMsgGetaddress(TrezorTest):

    def test_btc(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert self.client.get_address('Bitcoin', []) == '1EfKbQupktEMXf4gujJ9kCFo83k1iMqwqK'
        assert self.client.get_address('Bitcoin', [1]) == '1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb'
        assert self.client.get_address('Bitcoin', [0, -1]) == '1JVq66pzRBvqaBRFeU9SPVvg3er4ZDgoMs'
        assert self.client.get_address('Bitcoin', [-9, 0]) == '1F4YdQdL9ZQwvcNTuy5mjyQxXkyCfMcP2P'
        assert self.client.get_address('Bitcoin', [0, 9999999]) == '1GS8X3yc7ntzwGw9vXwj9wqmBWZkTFewBV'

    def test_ltc(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert self.client.get_address('Litecoin', []) == 'LYtGrdDeqYUQnTkr5sHT2DKZLG7Hqg7HTK'
        assert self.client.get_address('Litecoin', [1]) == 'LKRGNecThFP3Q6c5fosLVA53Z2hUDb1qnE'
        assert self.client.get_address('Litecoin', [0, -1]) == 'LcinMK8pVrAtpz7Qpc8jfWzSFsDLgLYfG6'
        assert self.client.get_address('Litecoin', [-9, 0]) == 'LZHVtcwAEDf1BR4d67551zUijyLUpDF9EX'
        assert self.client.get_address('Litecoin', [0, 9999999]) == 'Laf5nGHSCT94C5dK6fw2RxuXPiw2ZuRR9S'

    def test_tbtc(self):
        self.setup_mnemonic_nopin_nopassphrase()
        assert self.client.get_address('Testnet', [111, 42]) == 'moN6aN6NP1KWgnPSqzrrRPvx2x1UtZJssa'

    def test_bch(self):
        self.setup_mnemonic_allallall()
        assert self.client.get_address('Bcash', self.client.expand_path("44'/145'/0'/0/0")) == '1MH9KKcvdCTY44xVDC2k3fjBbX5Cz29N1q'
        assert self.client.get_address('Bcash', self.client.expand_path("44'/145'/0'/0/1")) == '1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3'
        assert self.client.get_address('Bcash', self.client.expand_path("44'/145'/0'/1/0")) == '1HADRPJpgqBzThepERpVXNi6qRgiLQRNoE'

    def test_bch_multisig(self):
        self.setup_mnemonic_allallall()
        xpubs = []
        for n in map(lambda index: self.client.get_public_node(self.client.expand_path("44'/145'/" + str(index) + "'")), range(1, 4)):
            xpubs.append(n.xpub)

        def getmultisig(chain, nr, signatures=[b'', b'', b''], xpubs=xpubs):
            return proto.MultisigRedeemScriptType(
                pubkeys=list(map(lambda xpub: proto.HDNodePathType(node=bip32.deserialize(xpub), address_n=[chain, nr]), xpubs)),
                signatures=signatures,
                m=2,
            )
        for nr in range(1, 4):
            assert self.client.get_address('Bcash', self.client.expand_path("44'/145'/" + str(nr) + "'/0/0"), show_display=(nr == 1), multisig=getmultisig(0, 0)) == '33Ju286QvonBz5N1V754ZekQv4GLJqcc5R'
            assert self.client.get_address('Bcash', self.client.expand_path("44'/145'/" + str(nr) + "'/1/0"), show_display=(nr == 1), multisig=getmultisig(1, 0)) == '3CPtPpL5mGAPdxUeUDfm2RNdWoSN9dKpXE'

    def test_public_ckd(self):
        self.setup_mnemonic_nopin_nopassphrase()

        node = self.client.get_public_node([]).node
        node_sub1 = self.client.get_public_node([1]).node
        node_sub2 = bip32.public_ckd(node, [1])

        assert node_sub1.chain_code == node_sub2.chain_code
        assert node_sub1.public_key == node_sub2.public_key

        address1 = self.client.get_address('Bitcoin', [1])
        address2 = bip32.get_address(node_sub2, 0)

        assert address2 == '1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb'
        assert address1 == address2
