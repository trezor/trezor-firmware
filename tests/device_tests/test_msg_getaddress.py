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

from trezorlib import btc, ckd_public as bip32, messages as proto
from trezorlib.tools import H_, CallException, parse_path

from ..common import MNEMONIC12


def getmultisig(chain, nr, xpubs, signatures=[b"", b"", b""]):
    return proto.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in xpubs],
        address_n=[chain, nr],
        signatures=signatures,
        m=2,
    )


class TestMsgGetaddress:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_btc(self, client):
        assert (
            btc.get_address(client, "Bitcoin", [])
            == "1EfKbQupktEMXf4gujJ9kCFo83k1iMqwqK"
        )
        assert (
            btc.get_address(client, "Bitcoin", [1])
            == "1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb"
        )
        assert (
            btc.get_address(client, "Bitcoin", [0, H_(1)])
            == "1JVq66pzRBvqaBRFeU9SPVvg3er4ZDgoMs"
        )
        assert (
            btc.get_address(client, "Bitcoin", [H_(9), 0])
            == "1F4YdQdL9ZQwvcNTuy5mjyQxXkyCfMcP2P"
        )
        assert (
            btc.get_address(client, "Bitcoin", [0, 9999999])
            == "1GS8X3yc7ntzwGw9vXwj9wqmBWZkTFewBV"
        )

    @pytest.mark.altcoin
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_ltc(self, client):
        assert (
            btc.get_address(client, "Litecoin", [])
            == "LYtGrdDeqYUQnTkr5sHT2DKZLG7Hqg7HTK"
        )
        assert (
            btc.get_address(client, "Litecoin", [1])
            == "LKRGNecThFP3Q6c5fosLVA53Z2hUDb1qnE"
        )
        assert (
            btc.get_address(client, "Litecoin", [0, H_(1)])
            == "LcinMK8pVrAtpz7Qpc8jfWzSFsDLgLYfG6"
        )
        assert (
            btc.get_address(client, "Litecoin", [H_(9), 0])
            == "LZHVtcwAEDf1BR4d67551zUijyLUpDF9EX"
        )
        assert (
            btc.get_address(client, "Litecoin", [0, 9999999])
            == "Laf5nGHSCT94C5dK6fw2RxuXPiw2ZuRR9S"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_tbtc(self, client):
        assert (
            btc.get_address(client, "Testnet", [111, 42])
            == "moN6aN6NP1KWgnPSqzrrRPvx2x1UtZJssa"
        )

    @pytest.mark.altcoin
    def test_bch(self, client):
        assert (
            btc.get_address(client, "Bcash", parse_path("44'/145'/0'/0/0"))
            == "bitcoincash:qr08q88p9etk89wgv05nwlrkm4l0urz4cyl36hh9sv"
        )
        assert (
            btc.get_address(client, "Bcash", parse_path("44'/145'/0'/0/1"))
            == "bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4"
        )
        assert (
            btc.get_address(client, "Bcash", parse_path("44'/145'/0'/1/0"))
            == "bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw"
        )

    @pytest.mark.altcoin
    def test_grs(self, client):
        assert (
            btc.get_address(client, "Groestlcoin", parse_path("44'/17'/0'/0/0"))
            == "Fj62rBJi8LvbmWu2jzkaUX1NFXLEqDLoZM"
        )
        assert (
            btc.get_address(client, "Groestlcoin", parse_path("44'/17'/0'/1/0"))
            == "FmRaqvVBRrAp2Umfqx9V1ectZy8gw54QDN"
        )
        assert (
            btc.get_address(client, "Groestlcoin", parse_path("44'/17'/0'/1/1"))
            == "Fmhtxeh7YdCBkyQF7AQG4QnY8y3rJg89di"
        )

    @pytest.mark.altcoin
    def test_elements(self, client):
        assert (
            btc.get_address(client, "Elements", parse_path("m/44'/1'/0'/0/0"))
            == "2dpWh6jbhAowNsQ5agtFzi7j6nKscj6UnEr"
        )

    def test_multisig(self, client):
        xpubs = []
        for n in range(1, 4):
            node = btc.get_public_node(client, parse_path("44'/0'/%d'" % n))
            xpubs.append(node.xpub)

        for nr in range(1, 4):
            assert (
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("44'/0'/%d'/0/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(0, 0, xpubs=xpubs),
                )
                == "3Pdz86KtfJBuHLcSv4DysJo4aQfanTqCzG"
            )
            assert (
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("44'/0'/%d'/1/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(1, 0, xpubs=xpubs),
                )
                == "36gP3KVx1ooStZ9quZDXbAF3GCr42b2zzd"
            )

    def test_multisig_missing(self, client):
        xpubs = []
        for n in range(1, 4):
            # shift account numbers by 10 to create valid multisig,
            # but not containing the keys used below
            n = n + 10
            node = btc.get_public_node(client, parse_path("44'/0'/%d'" % n))
            xpubs.append(node.xpub)
        for nr in range(1, 4):
            with pytest.raises(CallException):
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("44'/0'/%d'/0/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(0, 0, xpubs=xpubs),
                )
            with pytest.raises(CallException):
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("44'/0'/%d'/1/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(1, 0, xpubs=xpubs),
                )

    @pytest.mark.altcoin
    def test_bch_multisig(self, client):
        xpubs = []
        for n in range(1, 4):
            node = btc.get_public_node(client, parse_path("44'/145'/%d'" % n))
            xpubs.append(node.xpub)

        for nr in range(1, 4):
            assert (
                btc.get_address(
                    client,
                    "Bcash",
                    parse_path("44'/145'/%d'/0/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(0, 0, xpubs=xpubs),
                )
                == "bitcoincash:pqguz4nqq64jhr5v3kvpq4dsjrkda75hwy86gq0qzw"
            )
            assert (
                btc.get_address(
                    client,
                    "Bcash",
                    parse_path("44'/145'/%d'/1/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(1, 0, xpubs=xpubs),
                )
                == "bitcoincash:pp6kcpkhua7789g2vyj0qfkcux3yvje7euhyhltn0a"
            )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_public_ckd(self, client):
        node = btc.get_public_node(client, []).node
        node_sub1 = btc.get_public_node(client, [1]).node
        node_sub2 = bip32.public_ckd(node, [1])

        assert node_sub1.chain_code == node_sub2.chain_code
        assert node_sub1.public_key == node_sub2.public_key

        address1 = btc.get_address(client, "Bitcoin", [1])
        address2 = bip32.get_address(node_sub2, 0)

        assert address2 == "1CK7SJdcb8z9HuvVft3D91HLpLC6KSsGb"
        assert address1 == address2
