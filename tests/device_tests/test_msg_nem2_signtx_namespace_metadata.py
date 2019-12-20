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
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_NAMESPACE_METADATA,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "targetPublicKey": "A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500",
                "scopedMetadataKey": "0000000000000001",
                "valueSizeDelta": 11,
                "targetNamespaceId": "EAA4CB0862DBCB67",
                "valueSize": 11,
                "value": "41206E65772076616C7565"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "BF000000000000005BF264268EF74545D0AE5C13115DD1127CF5E52B44F2738B3A03A67BE2F65B7AD45955CF9E3ABD172C5089A41E595B4CE934447C0DF2837ED25155449DB6E00FA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984443204E000000000000090A1E5E1A000000A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500010000000000000067CBDB6208CBA4EA0B000B0041206E65772076616C7565"
        )

        assert (
            tx.hash.hex().upper()
            == "E3DF13CA372DC74A527F1038EE978BCF686A634AA0481BBB576D8DAD1FF7D653"
        )