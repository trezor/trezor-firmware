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


class TestMsgGetaddressSegwitNative(TrezorTest):
    def test_show_segwit(self):
        self.setup_mnemonic_allallall()
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("49'/1'/0'/0/0"),
                True,
                None,
                script_type=proto.InputScriptType.SPENDWITNESS,
            )
            == "tb1qqzv60m9ajw8drqulta4ld4gfx0rdh82un5s65s"
        )
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("49'/1'/0'/1/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDWITNESS,
            )
            == "tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu"
        )
        assert (
            btc.get_address(
                self.client,
                "Testnet",
                parse_path("44'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDWITNESS,
            )
            == "tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc"
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
        nodes = [
            btc.get_public_node(self.client, parse_path("999'/1'/%d'" % index))
            for index in range(1, 4)
        ]
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
        multisig2 = proto.MultisigRedeemScriptType(
            pubkeys=list(
                map(
                    lambda n: proto.HDNodePathType(
                        node=bip32.deserialize(n.xpub), address_n=[2, 1]
                    ),
                    nodes,
                )
            ),
            signatures=[b"", b"", b""],
            m=2,
        )
        for i in [1, 2, 3]:
            assert (
                btc.get_address(
                    self.client,
                    "Testnet",
                    parse_path("999'/1'/%d'/2/1" % i),
                    False,
                    multisig2,
                    script_type=proto.InputScriptType.SPENDWITNESS,
                )
                == "tb1qch62pf820spe9mlq49ns5uexfnl6jzcezp7d328fw58lj0rhlhasge9hzy"
            )
            assert (
                btc.get_address(
                    self.client,
                    "Testnet",
                    parse_path("999'/1'/%d'/2/0" % i),
                    False,
                    multisig1,
                    script_type=proto.InputScriptType.SPENDWITNESS,
                )
                == "tb1qr6xa5v60zyt3ry9nmfew2fk5g9y3gerkjeu6xxdz7qga5kknz2ssld9z2z"
            )
