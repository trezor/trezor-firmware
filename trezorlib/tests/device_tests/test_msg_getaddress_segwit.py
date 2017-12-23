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
import trezorlib.ckd_public as bip32
from trezorlib import messages as proto


class TestMsgGetaddressSegwit(TrezorTest):

    def test_show_segwit(self):
        self.setup_mnemonic_allallall()
        assert self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/1/0"), True, None, script_type=proto.InputScriptType.SPENDP2SHWITNESS) == '2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX'
        assert self.client.get_address("Testnet", self.client.expand_path("49'/1'/0'/0/0"), False, None, script_type=proto.InputScriptType.SPENDP2SHWITNESS) == '2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp'
        assert self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"), False, None, script_type=proto.InputScriptType.SPENDP2SHWITNESS) == '2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc'
        assert self.client.get_address("Testnet", self.client.expand_path("44'/1'/0'/0/0"), False, None, script_type=proto.InputScriptType.SPENDADDRESS) == 'mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q'

    def test_show_multisig_3(self):
        self.setup_mnemonic_allallall()
        nodes = map(lambda index: self.client.get_public_node(self.client.expand_path("999'/1'/%d'" % index)), range(1, 4))
        multisig1 = proto.MultisigRedeemScriptType(
            pubkeys=list(map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 0]), nodes)),
            signatures=[b'', b'', b''],
            m=2,
        )
        # multisig2 = proto.MultisigRedeemScriptType(
        #     pubkeys=map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 1]), nodes),
        #     signatures=[b'', b'', b''],
        #     m=2,
        # )
        for i in [1, 2, 3]:
            assert self.client.get_address("Testnet", self.client.expand_path("999'/1'/%d'/2/0" % i), False, multisig1, script_type=proto.InputScriptType.SPENDP2SHWITNESS) == '2N2MxyAfifVhb3AMagisxaj3uij8bfXqf4Y'
