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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path


class TestMsgGetaddressSegwit:
    def test_show_segwit(self, client):
        assert (
            btc.get_address(
                client,
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
                client,
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
                client,
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
                "Groestlcoin Testnet",
                parse_path("49'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            )
            == "2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e"
        )
        assert (
            btc.get_address(
                client,
                "Elements",
                parse_path("m/49'/1'/0'/0/0"),
                False,
                None,
                script_type=proto.InputScriptType.SPENDP2SHWITNESS,
            )
            == "XNW67ZQA9K3AuXPBWvJH4zN2y5QBDTwy2Z"
        )

    @pytest.mark.multisig
    def test_show_multisig_3(self, client):
        nodes = [
            btc.get_public_node(
                client, parse_path("49'/1'/%d'" % i), coin_name="Testnet"
            ).node
            for i in range(1, 4)
        ]

        multisig1 = proto.MultisigRedeemScriptType(
            nodes=nodes, address_n=[0, 7], signatures=[b"", b"", b""], m=2
        )
        # multisig2 = proto.MultisigRedeemScriptType(
        #     pubkeys=map(lambda n: proto.HDNodePathType(node=bip32.deserialize(n.xpub), address_n=[2, 1]), nodes),
        #     signatures=[b'', b'', b''],
        #     m=2,
        # )
        for i in [1, 2, 3]:
            assert (
                btc.get_address(
                    client,
                    "Testnet",
                    parse_path(f"49'/1'/{i}'/0/7"),
                    False,
                    multisig1,
                    script_type=proto.InputScriptType.SPENDP2SHWITNESS,
                )
                == "2MwuUwUzPG17wiKQpfXmzfxJEoe7RXZDRad"
            )

    @pytest.mark.multisig
    @pytest.mark.parametrize("show_display", (True, False))
    def test_multisig_missing(self, client, show_display):
        # Multisig with global suffix specification.
        # Use account numbers 1, 2 and 3 to create a valid multisig,
        # but not containing the keys from account 0 used below.
        nodes = [
            btc.get_public_node(client, parse_path("49'/0'/%d'" % i)).node
            for i in range(1, 4)
        ]
        multisig1 = proto.MultisigRedeemScriptType(
            nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
        )

        # Multisig with per-node suffix specification.
        node = btc.get_public_node(
            client, parse_path("49h/0h/0h/0"), coin_name="Bitcoin"
        ).node
        multisig2 = proto.MultisigRedeemScriptType(
            pubkeys=[
                proto.HDNodePathType(node=node, address_n=[1]),
                proto.HDNodePathType(node=node, address_n=[2]),
                proto.HDNodePathType(node=node, address_n=[3]),
            ],
            signatures=[b"", b"", b""],
            m=2,
        )

        for multisig in (multisig1, multisig2):
            with pytest.raises(TrezorFailure):
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("49'/0'/0'/0/0"),
                    show_display=show_display,
                    multisig=multisig,
                    script_type=proto.InputScriptType.SPENDP2SHWITNESS,
                )
