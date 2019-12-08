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
class TestMsgNEM2SignTxNamespaceMetadata:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_namespace_metadata(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_NAMESPACE_METADATA,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "targetPublicKey": "252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317",
                "scopedMetadataKey": "0000000000000001",
                "valueSizeDelta": 9,
                "targetNamespaceId": "EAA4CB0862DBCB67",
                "valueSize": 9,
                "value": "4E65772056616C7565"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "BD00000000000000081138C4B9BC4485470E182E906290BCEF6F8F28367ACD74E4BF972C439FC60AC7DF35CAD0D56463B73284B73E6E913309782517E1453E7F0AF382CB4D244D0E252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984443204E000000000000090A1E5E1A000000252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317010000000000000067CBDB6208CBA4EA090009004E65772056616C7565"
        )

        # TODO: fix this
        # assert (
        #     tx.hash.hex().upper()
        #     == "035F1BF3EBDF6C95238C64E3286D5C2BEBDAD85C5F92C3333E9DF94C82710759"
        # )