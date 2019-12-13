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
class TestMsgNEM2SignTxMosaicMetadata:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_metadata(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_METADATA,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "20000",
                "deadline": "113248176649",
                "targetPublicKey": "252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317",
                "scopedMetadataKey": "0000000000000001",
                "valueSizeDelta": 11,
                "targetMosaicId": "9adf3b117a3c10ca",
                "valueSize": 11,
                "value": "41206E65772076616C7565"
            }
        )

        assert (
            tx.payload.hex().upper()
            == "BF0000000000000001F34F9A776C8A8B0DE13F52696FCF853008F4E89AFE0994CD3758C8FF6F30A64A7F6B1A0250E8BF42A0DE85C3E5C0C362AFAAEF29C89EB7CBC36B4C645F6804252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170000000001984442204E000000000000090A1E5E1A000000252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF3170100000000000000CA103C7A113BDF9A0B000B0041206E65772076616C7565"
        )

        assert (
            tx.hash.hex().upper()
            == "41EE441C830DF8BB16317D7C2CA5A81163D049F64333ADE27C301EB11855C75C"
        )