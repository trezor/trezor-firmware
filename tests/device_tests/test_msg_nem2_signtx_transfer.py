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
                    "network_type": nem2.NETWORK_TYPE_MIJIN_TEST,
                    "generation_hash": "9F1979BEBA29C47E59B40393ABB516801A353CFC0C18BC241FEDE41939C907E7",
                    "version": 36865,
                    "max_fee": "20000",
                    "deadline": "113248176649",
                    "recipient_address": "SAIKV5OOWCQ3EHIBMJH7HR2GGKPXUG2VT4OE3FU7",
                    "mosaics": [{ "amount": "1000000000", "id": "308F144790CD7BC4" }],
                    "message": {
                        "payload": "This is a message",
                        "type": 0,
                    },
                },
            )

            assert (
                tx.payload.hex().upper()
                == "B6000000946BFD936C0FD410F997268141EAAACD48182E5C5198C313737EF0AAFFD1097DB8B43201CCFBFEC67B5D85F0446DC04DB48C66A1408E334EDA8655BDE73C090F8AF53BB8F3A167C68F264C33237DB309DBC88F64D7A1088B8BEEA5A34DBBBEC201905441204E000000000000090A1E5E1A0000009010AAF5CEB0A1B21D01624FF3C746329F7A1B559F1C4D969F12000100546869732069732061206D657373616765C47BCD9047148F3000CA9A3B00000000"
            )
            # assert (
            #     tx.hash.hex()
            #     == "76287219944D387336C27626CB0902B141B66032B99893E687837C85B160E56A"
            # )