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

from trezorlib import btc, messages as proto
from trezorlib.tools import parse_path

from ..support import ckd_public as bip32
from .common import TrezorTest


class TestMsgGetaddressSegwit(TrezorTest):
    def test_show_segwit(self):
        self.setup_mnemonic_allallall()
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("49'/1'/0'/1/0"),
                True,
                None,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            )
            == "2N1LGaGg836mqSQqiuUBLfcyGBhyZbremDX"
        )
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("49'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            )
            == "2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp"
        )
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("44'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            )
            == "2N6UeBoqYEEnybg4cReFYDammpsyDw8R2Mc"
        )
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("44'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDADDRESS,
            )
            == "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"
        )

    def test_show_multisig_3(self):
        self.setup_mnemonic_allallall()
        nodes = map(
            lambda index: btc.get_public_node(
                self.client, parse_path("999'/1'/%d'" % index)
            ),
            range(1, 4),
        )
        multisig1 = proto.MultisigRedeemScriptType(
            pubkeys=list(
                map(
                    lambda n: proto.HDNodePathType(
                        node=bip32.deserialize(n.xpub), address_n=[2, 0]
                    ),
                    nodes,
                )
            ),
            signatures=[b"", b"", b""],
            m=2,
        )
        # multisig2 = proto.MultisigRedeemScriptType(
        #     pubkeys=map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 1]), nodes),
        #     signatures=[b'', b'', b''],
        #     m=2,
        # )
        for i in [1, 2, 3]:
            assert (
                btc.get_address(
                    self.client,
                    "Testnet",
                    parse_path("999'/1'/%d'/2/0" % i),
                    False,
                    multisig1,
                    script_type=proto.InputScriptType.SPENDP2SHWITNESS,
                )
                == "2N2MxyAfifVhb3AMagisxaj3uij8bfXqf4Y"
            )
