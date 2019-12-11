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
class TestMsgNEM2SignTxMosaics:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_mosaic_definition(self, client):
        tx = nem2.sign_tx(
            client,
            # TODO: update to use m/44'/43'/0' and re-enable check in core/src/apps/nem2/validators
            # this will change the sign_tx payload
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_MOSAIC_DEFINITION,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "100",
                "deadline": "113728610090",
                "nonce": 3095715558,
                "mosaicId": "0B65C4B29A80C619",
                "flags": 7,
                "divisibility": 100,
                "duration": "123"
            },
        )

        print(tx)

        assert (
            tx.payload.hex().upper()
            == "9600000000000000FD1497976AFA3155798512F9EF0E8B534DEFCFEF6A00700CC5CF08363B77DA737ADC5E9BC4999A864A6830E9C54BD1FC0A4330206EDCFD153C999199341D9C0CA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B412715000000000001984D4164000000000000002ADFC07A1A00000019C6809AB2C4650B7B00000000000000E6DE84B80764"
        )
        assert (
            tx.hash.hex().upper()
            == "3F5E26802ABA3D0598A1930BD80BD711D6797887135D318B15EB1EC223733959"
        )