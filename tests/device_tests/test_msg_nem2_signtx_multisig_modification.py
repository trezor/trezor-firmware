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
            parse_path("m/44'/43'/0'/0'/0'"),
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
            == "A800000000000000823588D0A60744219BE40E51D1FD35DD2A2EE81E5538CF2F501EE598FD5F348931DC2E69C1ABEFC13EEC2F1DD27D08D3A236FB98963491D40A6A6C5077B79F09A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019855416400000000000000090A1E5E1A0000000101010000000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        assert (
            tx.hash.hex().upper()
            == "F06695EDB5B9BDD2D714DAAF1722519C19FBBC6EBE498E2FED183470A05046CE"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_multisig_modification_remove_public_key(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
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
            == "A800000000000000C976802B440482FF0E085DA280F73B5DEBE0311CA76528E7E6AEB353E655A9DBDC871281A3FD033AC0E8E8B814809E5CEDE5550501CCAB1DAA6464823D0F1308A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019855416400000000000000090A1E5E1A000000FFFF000100000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        assert (
            tx.hash.hex().upper()
            == "B20B96D83AFF09ECAC37FB53DF0D35513E9FD6925ED2BEA3390D07129C84A48F"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_multisig_modification_negative_delta(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MULTISIG_MODIFICATION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113248176649",
                "minApprovalDelta": -120,
                "minRemovalDelta": 115,
                "publicKeyAdditions": [],
                "publicKeyDeletions": [
                    "596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
                ]
            }
        )

        assert (
            tx.payload.hex().upper()
            == "A80000000000000058513D1F17A533F5C547B7783E1624314F42A4936239A7DE1B229C78F12FA09D2F01E59E08BBD490AD18DF454719A44F2BA4ED59F83182741CBFC4263F745A08A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B4127150000000000019855416400000000000000090A1E5E1A0000007388000100000000596FEAB15D98BFD75F1743E9DC8A36474A3D0C06AE78ED134C231336C38A6297"
        )

        assert (
            tx.hash.hex().upper()
            == "1B8F40DE3846801F475EBB173E75038853CC4D45F0F8DC054A1CE629E11E926A"
        )