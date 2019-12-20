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
                "network": nem2.NETWORK_TYPE_TEST_NET,
                "version": 38913,
                "maxFee": "0",
                "deadline": "113728610090",
                "recipientAddress": {
                    "address": "TABLKWFB5SWIEHJBZNOHJC3N65QO2FR2W364Q5TX",
                    "networkType": nem2.NETWORK_TYPE_TEST_NET
                },
                "hashType": nem2.SECRET_LOCK_SHA3_256,
                "proof": "a25fde258f078ddce870",
                "secret":"D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7"
            },
        )

        assert (
            signed_secret_lock_tx.payload.hex().upper()
            == "C6000000000000003E33942ADED4B0C6CAB2A5ACC5568F742251D38B4B5C2DC8DD43DB8394DBAC30882DAAF1B41CEF932CA6448E57B09566FDD9F60D8824E50B47C20A349CED410DA8F70E4D5C357273968B12417AE8B742E35E530623C2488D0A73306B41271500000000000198524200000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B70A00009802B558A1ECAC821D21CB5C748B6DF760ED163AB6FDC87677A25FDE258F078DDCE870"
        )
        assert (
            signed_secret_lock_tx.hash.hex().upper()
            == "2AB0614A62F532AC106A92C5CBB55122A72EBFE0FB3075F79B80D32C2C5BF90A"
        )
