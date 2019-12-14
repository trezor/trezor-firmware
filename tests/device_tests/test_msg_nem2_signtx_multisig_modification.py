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
    def test_nem2_signtx_multisig_modification_add_public_key(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MULTISIG_MODIFICATION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113248176649",
                "minApprovalDelta": 1,
                "minRemovalDelta": 1,
                "publicKeyAdditions": [
                "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
                ],
                "publicKeyDeletions": []
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A800000000000000B194BB46CDBC48A25000E4DFE23B210B91EE99336F98AFBB8AAF9B07ABD7307F5CEA4090136853C6682EB870138356B3BB2C0183B62BF6E8ECA86A29EBA9D00C252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF31700000000019855416400000000000000090A1E5E1A0000000101010000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        assert (
            tx.hash.hex().upper()
            == "09CBE8F5AE0447A203843B4ED437314AE476BDB890613391818DEFE620530255"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_multisig_modification_remove_public_key(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MULTISIG_MODIFICATION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113248176649",
                "minApprovalDelta": -1,
                "minRemovalDelta": -1,
                "publicKeyAdditions": [],
                "publicKeyDeletions": [
                    "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
                ]
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A80000000000000017B8D64621527730A377D1291820B30690ED46EF8A53A91534E204F38F1606713D10AA23C4E20CC64864A900A237F934DAFFF7D2E9BB7213CD0BB73D2104EE02252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF31700000000019855416400000000000000090A1E5E1A000000FFFF000100000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        assert (
            tx.hash.hex().upper()
            == "0472E9468043BDA687C6370C004659D42C3C4110FD585BA11B9333AE27DC138F"
        )