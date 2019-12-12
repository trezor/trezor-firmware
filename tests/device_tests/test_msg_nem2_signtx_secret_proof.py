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
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_SECRET_PROOF,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                # TODO: this isn't how it actually comes through from nem2-sdk,
                # need to reverse the network-version bitshift or something similar
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
            == "C6000000000000006020EC6E8E8B47E023BAC840A402CC6D3EC58779EC58466835257077DC2FB497D4BC7940B6B79AFA255301A877764FEAEC6076A095917D819E586EA7CF108802252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317000000000198524200000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B70A00009802B558A1ECAC821D21CB5C748B6DF760ED163AB6FDC87677A25FDE258F078DDCE870"
        )
        assert (
            signed_secret_lock_tx.hash.hex().upper()
            == "41D18BC77EEBD2761FF7EE4C71A4632FC0CCBACC8A4F81BF4FD393DAA655DEE7"
        )
