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

from trezorlib import nem2
from trezorlib.tools import parse_path

from ..common import MNEMONIC12

@pytest.mark.altcoin
@pytest.mark.nem2
class TestMsgNEM2SignTxMosaicSupply:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_supply(self, client):
        tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_SUPPLY_CHANGE,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113728610090",
                "mosaicId": "0B65C4B29A80C619",
                "action": 1,
                "delta": "1000000"
            },
        )

        assert (
            tx.payload.hex().upper()
            == "9100000000000000691CB4316D2DC992A7160FF6A1FB4B738C534FC31383A5F368FEAE797DFE335E42194599BF335D33A9A2EE08A6CC711A75F0E9C5C9BB357F5DDDE385921ED50DA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984D4264000000000000002ADFC07A1A00000019C6809AB2C4650B40420F000000000001"
        )
        assert (
            tx.hash.hex().upper()
            == "EEDDFBCBE0FF235ABB7A5618C42FF61E1FEDAC015BF1009BD6FA27A84CA2340D"
        )