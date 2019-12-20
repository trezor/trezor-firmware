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
class TestMsgNEM2SignTxSecretLock:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_secret_lock(self, client):
        signed_secret_lock_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_SECRET_LOCK,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113728610090",
                "mosaic": {
                    "amount": "10",
                    "id": "9adf3b117a3c10ca"
                },
                "recipientAddress": {
                    "address": "MAJNLQOD7TBPI4EAUHZNTXLSEA4IHVQTH54XTOUV",
                    "networkType": nem2.NETWORK_TYPE_MIJIN
                },
                "hashType": nem2.SECRET_LOCK_SHA3_256,
                "duration": "23040",
                "secret":"D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7",
            },
        )

        assert (
            signed_secret_lock_tx.payload.hex().upper()
            == "D200000000000000ACD69DDB3E53ED6F90A80CB26D15BE9E2D2AFCAA9CCA9E47BD2554D5C848F46B6AF9BEF53AB14DD5987EEC92E4FE6CCBBC65B8DA72409F730DC96A56C5488502A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000198524100000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7CA103C7A113BDF9A0A00000000000000005A000000000000006012D5C1C3FCC2F47080A1F2D9DD72203883D6133F7979BA95"
        )
        assert (
            signed_secret_lock_tx.hash.hex().upper()
            == "79BEF8C176EE73334A0207928C0636EF906314EF7327F578E63F5E6418517636"
        )
