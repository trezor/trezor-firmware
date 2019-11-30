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
class TestMsgNEM2SignTxTransfer:
    @pytest.mark.setup_client(mnemonic=MNEMONIC12)
    def test_nem2_signtx_simple(self, client):
        with client:
            client.set_expected_responses(
                [
                    # Confirm transfer and network fee
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Confirm mosaic
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Confirm recipient
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.NEM2SignedTx(),
                ]
            )

            tx = nem2.sign_tx(
                client,
                parse_path("m/44'/43'/0'"),
                {
                    "type": nem2.TYPE_TRANSACTION_TRANSFER,
                    "network_type": nem2.NETWORK_TYPE_TEST_NET,
                    "generation_hash": "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
                    "version": 38913,
                    "max_fee": "20000",
                    "deadline": "113248176649",
                    "recipient_address": {
                        "address": "TAO6QEUC3APBTMDAETMG6IZJI7YOXWHLGC5T4HA4",
                        "network_type": nem2.NETWORK_TYPE_TEST_NET
                    },
                    "mosaics": [
                        {
                            "amount": "1000000000",
                            "id": "308F144790CD7BC4"
                        }
                    ],
                    "message": {
                        "type": 0,
                        "payload": "Test Transfer"
                    }
                }
            )

            assert (
                tx.payload.hex().upper()
                == "BE000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001985441204E000000000000090A1E5E1A000000981DE81282D81E19B06024D86F232947F0EBD8EB30BB3E1C1C010E0000000000C47BCD9047148F3000CA9A3B000000000054657374205472616E73666572"
            )
            # assert (
            #     tx.hash.hex()
            #     == "76287219944D387336C27626CB0902B141B66032B99893E687837C85B160E56A"
            # )