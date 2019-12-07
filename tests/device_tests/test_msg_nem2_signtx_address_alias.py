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

from trezorlib import messages as proto, nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2SignTxAddressAlias:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_link_address_alias(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ADDRESS_ALIAS,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "aliasAction": nem2.ALIAS_ACTION_TYPE_LINK,
                "namespaceId": "EAA4CB0862DBCB67",
                "address": {
                    "address": "TD7FI2VK7ZRCPDRUII62XL567V72IPO5CBXPM2C3",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                }
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A2000000000000004523D0E6422021A28B5744AF4B278D4F66AA3E357C41FE695DE33EC8C667D54AC8AB7980F60ED78E7A6904682ABA6E5CE6202FC7E2B75E1D1015D5050D980E08252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984E42204E000000000000090A1E5E1A00000067CBDB6208CBA4EA98FE546AAAFE62278E34423DABAFBEFD7FA43DDD106EF6685B01"
        )

        # TODO: fix this
        # assert (
        #     tx.hash.hex().upper()
        #     == "EF0CA99813CA2708BE34F125547E28ADEC60C6BECF37A981E3231425511D147E"
        # )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_unlink_address_alias(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_ADDRESS_ALIAS,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "aliasAction": nem2.ALIAS_ACTION_TYPE_UNLINK,
                "namespaceId": "EAA4CB0862DBCB67",
                "address": {
                    "address": "TD7FI2VK7ZRCPDRUII62XL567V72IPO5CBXPM2C3",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                }
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A20000000000000042B600FC84989E07F637BF8CB98F95EF78D632C2EE8D2DDFED6B199FF4C3B34CE10C99E12A0C42850CE38A37816299F7C6B79D2C7A0F2441A42B548A80B16D09252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984E42204E000000000000090A1E5E1A00000067CBDB6208CBA4EA98FE546AAAFE62278E34423DABAFBEFD7FA43DDD106EF6685B00"
        )

        # TODO: fix this
        # assert (
        #     tx.hash.hex().upper()
        #     == "EF0CA99813CA2708BE34F125547E28ADEC60C6BECF37A981E3231425511D147E"
        # )