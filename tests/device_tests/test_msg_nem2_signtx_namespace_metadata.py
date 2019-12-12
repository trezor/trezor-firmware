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
                "valueSizeDelta": 11,
                "targetNamespaceId": "EAA4CB0862DBCB67",
                "valueSize": 11,
                "value": "41206E65772076616C7565"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "BF000000000000001FB86A899BCF247008292C305A2031AC8B75A5F5C6041C9D2B582808BC4D11E73E407007F856C0A7FC86D054BF1E069A8D6AD929806CA48EF0342071E9E34A03252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984443204E000000000000090A1E5E1A000000252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317010000000000000067CBDB6208CBA4EA0B000B0041206E65772076616C7565"
        )

        assert (
            tx.hash.hex().upper()
            == "68F949BC1D3F0ACA8651F70039BFCAC88DFA959C6640A40855128B64D508DEA3"
        )