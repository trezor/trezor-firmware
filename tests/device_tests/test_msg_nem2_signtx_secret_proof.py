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
class TestMsgNEM2SignTxSecretProof:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_secret_proof(self, client):
        signed_secret_lock_tx = nem2.sign_tx(
            client,
            parse_path("m/44'/43'/0'/0'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_SECRET_PROOF,
                "network": nem2.NETWORK_TYPE_MAIN_NET,
                "version": 26625,
                "maxFee": "0",
                "deadline": "113728610090",
                "recipientAddress": {
                    "address": "NABLKWFB5SWIEHJBZNOHJC3N65QO2FR2WZSW6DKZ",
                    "networkType": nem2.NETWORK_TYPE_MAIN_NET
                },
                "hashType": nem2.SECRET_LOCK_SHA3_256,
                "proof": "a25fde258f078ddce870",
                "secret":"D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7"
            },
        )

        assert (
            signed_secret_lock_tx.payload.hex().upper()
            == "C600000000000000881ED3B761F6EF7FA0F518981F85BEE3CF26CBEDE8EB7E049A91F13B18D28A78EF02A1C21C3D4E73D8CFD1F2BC3ED888E78D27845A6869C974E60403670AED07A8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000168524200000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B70A00006802B558A1ECAC821D21CB5C748B6DF760ED163AB6656F0D59A25FDE258F078DDCE870"
        )
        assert (
            signed_secret_lock_tx.hash.hex().upper()
            == "3C34120E44A501A09C0EC2D18071119ABAA261848758CDCA7D0866D096CF5984"
        )
