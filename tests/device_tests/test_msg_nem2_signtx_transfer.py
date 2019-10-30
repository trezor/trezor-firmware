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
                    # Unencrypted message
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Confirm recipient
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.NEM2SignedTx(),
                ]
            )

            print("TRANSFER TYPE", nem2.TYPE_TRANSACTION_TRANSFER)
            tx = nem2.sign_tx(
                client,
                parse_path("m/44'/43'/0'"),
                {
                    "amount": 2000000,
                    "fee": 2000000,
                    "size": 2212312,
                    "recipient_address": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "entityType": nem2.TYPE_TRANSACTION_TRANSFER,
                    "deadline": 74735615,
                    "message": {
                        "payload": b"test_nem2_transaction_transfer".hex(),
                        "type": 1,
                    },
                },
            )

            assert (
                tx.data.hex()
                == "01010000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e000000000025000000010000001d000000746573745f6e656d5f7472616e73616374696f6e5f7472616e73666572"
            )
            assert (
                tx.signature.hex()
                == "9cda2045324d05c791a4fc312ecceb62954e7740482f8df8928560d63cf273dea595023640179f112de755c79717757ef76962175378d6d87360ddb3f3e5f70f"
            )
