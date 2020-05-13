# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

import pytest

from trezorlib import btc, messages as proto
from trezorlib.tools import parse_path


class TestMsgGetaddressSegwitNative:
    def test_show_segwit(self, client):
        assert (
            btc.get_address(
                client,
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
                client,
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
                client,
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
                client,
                "Testnet",
                parse_path("44'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDADDRESS,
            )
            == "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"
        )

    @pytest.mark.altcoin
    def test_show_segwit_altcoin(self, client):
        assert (
            btc.get_address(
                client,
                "Groestlcoin",
                parse_path("84'/17'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDWITNESS,
            )
            == "grs1qw4teyraux2s77nhjdwh9ar8rl9dt7zww8r6lne"
        )
        assert (
            btc.get_address(
                client,
                "Elements",
                parse_path("84'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDWITNESS,
            )
            == "ert1qkvwu9g3k2pdxewfqr7syz89r3gj557l3xp9k2v"
        )

    @pytest.mark.multisig
    def test_show_multisig_3(self, client):
        nodes = [
            btc.get_public_node(
                client, parse_path("84'/1'/%d'" % index), coin_name="Testnet"
            ).node
            for index in range(1, 4)
        ]
        multisig1 = proto.MultisigRedeemScriptType(
            nodes=nodes, address_n=[2, 0], signatures=[b"", b"", b""], m=2
        )
        multisig2 = proto.MultisigRedeemScriptType(
            nodes=nodes, address_n=[2, 1], signatures=[b"", b"", b""], m=2
        )
        for i in [1, 2, 3]:
            assert (
                btc.get_address(
                    client,
                    "Testnet",
                    parse_path("84'/1'/%d'/2/1" % i),
                    False,
                    multisig2,
                    script_type=proto.InputScriptType.SPENDWITNESS,
                )
                == "tb1qnqlw0gwzpcdken0sarskrgxf7l36pprlfy4uk7yf98jz9rfd36ss2tc6ja"
            )
            assert (
                btc.get_address(
                    client,
                    "Testnet",
                    parse_path("84'/1'/%d'/2/0" % i),
                    False,
                    multisig1,
                    script_type=proto.InputScriptType.SPENDWITNESS,
                )
                == "tb1qaqrlzu8unz58p77d30ej85n3gv5574alkqw0qcjsyd2hs9frp2vstew67z"
            )
