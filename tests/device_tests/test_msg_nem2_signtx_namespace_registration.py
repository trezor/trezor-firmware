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
class TestMsgNEM2SignTxNamespaceRegistration:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_root_namespace_registration(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_NAMESPACE_REGISTRATION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "registrationType": 0,
                "namespaceName": "testnamespace",
                "id": "EAA4CB0862DBCB67",
                "duration": "1000000"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "9F00000000000000642F60B0D3116FB633CC5BEC7FFB563C4B7D53638E129F67CD9E314464729FB9C5589EC16D0D8AC3D9B8600872D246E357F97D87B768E1C63130D3FCFB51F20C252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984E41204E000000000000090A1E5E1A00000040420F000000000067CBDB6208CBA4EA000D746573746E616D657370616365"
        )

        assert (
            tx.hash.hex().upper()
            == "D4C8584338FF67C43E198D994270754B511744A3AB185FF72327EE72140D9A85"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_sub_namespace_registration(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_NAMESPACE_REGISTRATION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "registrationType": 1,
                "namespaceName": "sub",
                "id": "B1B6FADB51C1368C",
                "parentId": "EAA4CB0862DBCB67",
            }
        )

        assert (
            tx.payload.hex().upper()
            == "9500000000000000857CB0FB9DF14674DEA1E782D5EE3803DF72DDD661E7D732B559FE6EC5833239F508D33D69C94BC919387FF72800F1A3C43D7A9CD6EB03DAB7532217F2AA1504252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984E41204E000000000000090A1E5E1A00000067CBDB6208CBA4EA8C36C151DBFAB6B10103737562"
        )

        assert (
            tx.hash.hex().upper()
            == "CBC8CAA989B809F95957BCBEBE18AD1703954B581C52D8C224319EE996399F2D"
        )