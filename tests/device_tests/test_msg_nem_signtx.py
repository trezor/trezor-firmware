# This file is part of the TREZOR project.
#
# Copyright (C) 2017 Saleem Rashid <trezor@saleemrashid.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import unittest
import common
import binascii

from trezorlib import messages as proto

# tx hash: 209368053ac61969b6838ceb7e31badeb622ed6aa42d6c58365c42ad1a11e19d
SIGNATURE_TESTNET_SIMPLE = binascii.unhexlify(
    "9cda2045324d05c791a4fc312ecceb62954e7740482f8df8928560d63cf273dea595023640179f112de755c79717757ef76962175378d6d87360ddb3f3e5f70f"
)

# tx hash: 9f8741194576a090bc71a3f43a03855950f94278fa121e99203e45967e19a7d0
SIGNATURE_TESTNET_XEM_AS_MOSAIC = binascii.unhexlify(
    "1bca7b1b9ffb16d2c2adffa665be072bd2d7a0eafe4a9911dc473500c272905edf3d626274deb52aa490137a276d1fca67ee487079ebf9c09f9faa414f8e7c02"
)


class TestMsgNEMSigntx(common.TrezorTest):

    def test_nem_signtx_simple(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                # Confirm transfer and network fee
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Unencrypted message
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Confirm recipient
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.NEMSignedTx(signature=SIGNATURE_TESTNET_SIMPLE),
            ])

            self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "amount": 2000000,
                "fee": 2000000,
                "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "type": 257,
                "deadline": 74735615,
                "message": {
                    "payload": binascii.hexlify(b"test_nem_transaction_transfer"),
                    "type": 1,
                },
                "version": (0x98 << 24),
            })

    def test_nem_signtx_xem_as_mosaic(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                # Confirm transfer and network fee
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Confirm recipient
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.NEMSignedTx(signature=SIGNATURE_TESTNET_XEM_AS_MOSAIC),
            ])

            self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 76809215,
                "amount": 1000000,
                "fee": 1000000,
                "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "type": 257,
                "deadline": 76895615,
                "version": (0x98 << 24),
                "message": {
                },
                "mosaics": [
                    {
                        "mosaicId": {
                            "namespaceId": "nem",
                            "name": "xem",
                        },
                        "quantity": 1000000,
                    },
                ],
            })
