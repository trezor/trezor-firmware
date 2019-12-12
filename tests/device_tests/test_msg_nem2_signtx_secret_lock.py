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
            parse_path("m/44'/43'/0'"),
            "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
            {
                "type": nem2.TYPE_SECRET_LOCK,
                "network": nem2.NETWORK_TYPE_TEST_NET,
                # TODO: this isn't how it actually comes through from nem2-sdk,
                # need to reverse the network-version bitshift or something similar
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

        # TODO: update assertions with values made from signing transactions with hd path m/44'/43'/0' with TEST_NET network
        assert (
            signed_secret_lock_tx.payload.hex().upper()
            == "D2000000000000005A008FA29C4A0E824A5E0B88EDDD465EC173A5A95CF81A3B5CE440AE5B54510FE483FFE51E020E936268ED4EB73E9177A4AFA555C5C72453EFE5449B98D12400252D2E9F95C4671EEB0C67C6666890567E35976B32666263CD390FC188CCF317000000000198524100000000000000002ADFC07A1A000000D77E46ED5EC0EA4BD08AA77EEA9F17076F40BC2C2843B1BBB46DAA1D98DBF1B7CA103C7A113BDF9A0A00000000000000005A000000000000006012D5C1C3FCC2F47080A1F2D9DD72203883D6133F7979BA95"
        )
        assert (
            signed_secret_lock_tx.hash.hex().upper()
            == "40EB75158F8F36F7BD56C86AEA2ADEC8461F962DE5C0450F0AA48A580454DB76"
        )
