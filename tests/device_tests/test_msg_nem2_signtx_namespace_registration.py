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
            parse_path("m/44'/43'/0'/0'/0'"),
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
            == "9F00000000000000262DDD8D866010F0EC868099C55E0E10EE2B789E7576FD62A372F3CB9F28250F5FCDC1C33F1BCCBD1FA34B43CA0F670F451256BA16225E6645080D3CAC40C60FA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984E41204E000000000000090A1E5E1A00000040420F000000000067CBDB6208CBA4EA000D746573746E616D657370616365"
        )

        assert (
            tx.hash.hex().upper()
            == "F5BF0151E7CBB4FEB0CE7F04E39A48B784422CAF92C8BBA7274875982CA268BD"
        )

    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_sub_namespace_registration(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
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
            == "95000000000000000EA75A804CC7B136DD401904559CEEB8464A5073CEC939A359F851C5B2E8926305D5074F49A402DE23D9B8868823B4313AB52D353218E6C868F0891F1A17CE0CA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984E41204E000000000000090A1E5E1A00000067CBDB6208CBA4EA8C36C151DBFAB6B10103737562"
        )

        assert (
            tx.hash.hex().upper()
            == "5686DB6A7AE705B7141D377B9CFD853D81123FC79771E114C79BACB2221C8103"
        )