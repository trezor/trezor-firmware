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

from .common import *

from trezorlib import messages as proto
from trezorlib import nem


# assertion data from T1
@pytest.mark.xfail  # to be removed when nem is merged
class TestMsgNEMSignTx(TrezorTest):

    def test_nem_signtx_simple(self):
        # tx hash: 209368053ac61969b6838ceb7e31badeb622ed6aa42d6c58365c42ad1a11e19d
        signature = unhexlify(
            "9cda2045324d05c791a4fc312ecceb62954e7740482f8df8928560d63cf273dea595023640179f112de755c79717757ef76962175378d6d87360ddb3f3e5f70f"
        )

        self.setup_mnemonic_nopin_nopassphrase()
        with self.client:
            self.client.set_expected_responses([
                # Confirm transfer and network fee
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Unencrypted message
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Confirm recipient
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.NEMSignedTx(),
            ])

            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "amount": 2000000,
                "fee": 2000000,
                "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 74735615,
                "message": {
                    "payload": hexlify(b"test_nem_transaction_transfer"),
                    "type": 1,
                },
                "version": (0x98 << 24),
            })

            assert hexlify(tx.data) == b'01010000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e000000000025000000010000001d000000746573745f6e656d5f7472616e73616374696f6e5f7472616e73666572'
            assert tx.signature == signature

    def test_nem_signtx_encrypted_payload(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                # Confirm transfer and network fee
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Ask for encryption
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Confirm recipient
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.NEMSignedTx(),
            ])

            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "amount": 2000000,
                "fee": 2000000,
                "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 74735615,
                "message": {
                    # plain text is 32B long => cipher text is 48B
                    # as per PKCS#7 another block containing padding is added
                    "payload": hexlify(b"this message should be encrypted"),
                    "publicKey": "5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541",
                    "type": 2,
                },
                "version": (0x98 << 24),
            })

            assert hexlify(tx.data[:124]) == b'01010000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e0000000000680000000200000060000000'
            # after 124th byte comes iv (16B) salt (32B) and encrypted payload (48B)
            assert len(tx.data[124:]) == 16 + 32 + 48
            # because IV and salt are random (therefore the encrypted payload as well) those data can't be asserted
            assert len(tx.signature) == 64

    def test_nem_signtx_xem_as_mosaic(self):
        # tx hash: 9f8741194576a090bc71a3f43a03855950f94278fa121e99203e45967e19a7d0
        signature = unhexlify(
            "1bca7b1b9ffb16d2c2adffa665be072bd2d7a0eafe4a9911dc473500c272905edf3d626274deb52aa490137a276d1fca67ee487079ebf9c09f9faa414f8e7c02"
        )

        self.setup_mnemonic_nopin_nopassphrase()

        tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
            "timeStamp": 76809215,
            "amount": 1000000,
            "fee": 1000000,
            "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
            "type": nem.TYPE_TRANSACTION_TRANSFER,
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

        assert hexlify(tx.data) == b'0101000002000098ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f5595042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a40420f000000000000000000010000001a0000000e000000030000006e656d0300000078656d40420f0000000000'
        assert tx.signature == signature

    def test_nem_signtx_multiple_mosaics(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
            "timeStamp": 76809215,
            "amount": 1000000,
            "fee": 1000000,
            "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
            "type": nem.TYPE_TRANSACTION_TRANSFER,
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
                {
                    "mosaicId": {
                        "namespaceId": "abc",
                        "name": "mosaic",
                    },
                    "quantity": 200,
                },
                {
                    "mosaicId": {
                        "namespaceId": "nem",
                        "name": "xem",
                    },
                    "quantity": 30000,
                },
                {
                    "mosaicId": {
                        "namespaceId": "abc",
                        "name": "mosaic",
                    },
                    "quantity": 2000000,
                },
            ]
        })

        assert hexlify(tx.data) == b'0101000002000098ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f5595042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a40420f000000000000000000020000001d0000001100000003000000616263060000006d6f7361696348851e00000000001a0000000e000000030000006e656d0300000078656d70b70f0000000000'
        assert hexlify(tx.signature) == b'c83dec432a791733a79647a30c4c1bb38b27379768f9164cf5c53473078368f3bd9547049882b41ebb90edd1d4eef618cc0293af85d8166f26f3768a3c0b9802'
