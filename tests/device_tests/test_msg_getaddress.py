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

from trezorlib import btc, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from .. import bip32


def getmultisig(chain, nr, xpubs, signatures=[b"", b"", b""]):
    return messages.MultisigRedeemScriptType(
        nodes=[bip32.deserialize(xpub) for xpub in xpubs],
        address_n=[chain, nr],
        signatures=signatures,
        m=2,
    )


@pytest.mark.skip_ui
class TestMsgGetaddress:
    def test_btc(self, client):
        assert (
            btc.get_address(client, "Bitcoin", parse_path("m/44'/0'/0'/0/0"))
            == "1JAd7XCBzGudGpJQSDSfpmJhiygtLQWaGL"
        )
        assert (
            btc.get_address(client, "Bitcoin", parse_path("m/44'/0'/0'/0/1"))
            == "1GWFxtwWmNVqotUPXLcKVL2mUKpshuJYo"
        )
        assert (
            btc.get_address(client, "Bitcoin", parse_path("m/44'/0'/0'/1/0"))
            == "1DyHzbQUoQEsLxJn6M7fMD8Xdt1XvNiwNE"
        )

    @pytest.mark.altcoin
    def test_ltc(self, client):
        assert (
            btc.get_address(client, "Litecoin", parse_path("m/44'/2'/0'/0/0"))
            == "LcubERmHD31PWup1fbozpKuiqjHZ4anxcL"
        )
        assert (
            btc.get_address(client, "Litecoin", parse_path("m/44'/2'/0'/0/1"))
            == "LVWBmHBkCGNjSPHucvL2PmnuRAJnucmRE6"
        )
        assert (
            btc.get_address(client, "Litecoin", parse_path("m/44'/2'/0'/1/0"))
            == "LWj6ApswZxay4cJEJES2sGe7fLMLRvvv8h"
        )

    def test_tbtc(self, client):
        assert (
            btc.get_address(client, "Testnet", parse_path("m/44'/1'/0'/0/0"))
            == "mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q"
        )
        assert (
            btc.get_address(client, "Testnet", parse_path("m/44'/1'/0'/0/1"))
            == "mopZWqZZyQc3F2Sy33cvDtJchSAMsnLi7b"
        )
        assert (
            btc.get_address(client, "Testnet", parse_path("m/44'/1'/0'/1/0"))
            == "mm6kLYbGEL1tGe4ZA8xacfgRPdW1NLjCbZ"
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

    @pytest.mark.multisig
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

    @pytest.mark.multisig
    def test_multisig_missing(self, client):
        xpubs = []
        for n in range(1, 4):
            # shift account numbers by 10 to create valid multisig,
            # but not containing the keys used below
            n = n + 10
            node = btc.get_public_node(client, parse_path("44'/0'/%d'" % n))
            xpubs.append(node.xpub)
        for nr in range(1, 4):
            with pytest.raises(TrezorFailure):
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("44'/0'/%d'/0/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(0, 0, xpubs=xpubs),
                )
            with pytest.raises(TrezorFailure):
                btc.get_address(
                    client,
                    "Bitcoin",
                    parse_path("44'/0'/%d'/1/0" % nr),
                    show_display=(nr == 1),
                    multisig=getmultisig(1, 0, xpubs=xpubs),
                )

    @pytest.mark.altcoin
    @pytest.mark.multisig
    def test_bch_multisig(self, client):
        xpubs = []
        for n in range(1, 4):
            node = btc.get_public_node(
                client, parse_path("44'/145'/%d'" % n), coin_name="Bcash"
            )
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

    def test_public_ckd(self, client):
        node = btc.get_public_node(client, parse_path("m/44'/0'/0'")).node
        node_sub1 = btc.get_public_node(client, parse_path("m/44'/0'/0'/1/0")).node
        node_sub2 = bip32.public_ckd(node, [1, 0])

        assert node_sub1.chain_code == node_sub2.chain_code
        assert node_sub1.public_key == node_sub2.public_key

        address1 = btc.get_address(client, "Bitcoin", parse_path("m/44'/0'/0'/1/0"))
        address2 = bip32.get_address(node_sub2, 0)

        assert address2 == "1DyHzbQUoQEsLxJn6M7fMD8Xdt1XvNiwNE"
        assert address1 == address2


@pytest.mark.skip_t1
@pytest.mark.skip_ui
def test_invalid_path(client):
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        # slip44 id mismatch
        btc.get_address(client, "Bitcoin", parse_path("m/44'/111'/0'/0/0"))


@pytest.mark.skip_t1
def test_unknown_path(client):
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(
                    code=messages.ButtonRequestType.UnknownDerivationPath
                ),
                messages.Address(),
            ]
        )
        # account number is too high
        btc.get_address(client, "Bitcoin", parse_path("m/44'/0'/21'/0/0"))


@pytest.mark.altcoin
@pytest.mark.skip_ui
def test_crw(client):
    assert (
        btc.get_address(client, "Crown", parse_path("44'/72'/0'/0/0"))
        == "CRWYdvZM1yXMKQxeN3hRsAbwa7drfvTwys48"
    )
