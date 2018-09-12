# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

from trezorlib import messages as proto, nem
from trezorlib.tools import parse_path

from .common import TrezorTest


# assertion data from T1
@pytest.mark.nem
class TestMsgNEMSignTx(TrezorTest):
    def test_nem_signtx_simple(self):
        # tx hash: 209368053ac61969b6838ceb7e31badeb622ed6aa42d6c58365c42ad1a11e19d
        self.setup_mnemonic_nopin_nopassphrase()
        with self.client:
            self.client.set_expected_responses(
                [
                    # Confirm transfer and network fee
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Unencrypted message
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Confirm recipient
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.NEMSignedTx(),
                ]
            )

            tx = nem.sign_tx(
                self.client,
                parse_path("m/44'/1'/0'/0'/0'"),
                {
                    "timeStamp": 74649215,
                    "amount": 2000000,
                    "fee": 2000000,
                    "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "type": nem.TYPE_TRANSACTION_TRANSFER,
                    "deadline": 74735615,
                    "message": {
                        "payload": b"test_nem_transaction_transfer".hex(),
                        "type": 1,
                    },
                    "version": (0x98 << 24),
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

    def test_nem_signtx_encrypted_payload(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses(
                [
                    # Confirm transfer and network fee
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Ask for encryption
                    proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                    # Confirm recipient
                    proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                    proto.NEMSignedTx(),
                ]
            )

            tx = nem.sign_tx(
                self.client,
                parse_path("m/44'/1'/0'/0'/0'"),
                {
                    "timeStamp": 74649215,
                    "amount": 2000000,
                    "fee": 2000000,
                    "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "type": nem.TYPE_TRANSACTION_TRANSFER,
                    "deadline": 74735615,
                    "message": {
                        # plain text is 32B long => cipher text is 48B
                        # as per PKCS#7 another block containing padding is added
                        "payload": b"this message should be encrypted".hex(),
                        "publicKey": "5a5e14c633d7d269302849d739d80344ff14db51d7bcda86045723f05c4e4541",
                        "type": 2,
                    },
                    "version": (0x98 << 24),
                },
            )

            assert (
                tx.data[:124].hex()
                == "01010000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e0000000000680000000200000060000000"
            )
            # after 124th byte comes iv (16B) salt (32B) and encrypted payload (48B)
            assert len(tx.data[124:]) == 16 + 32 + 48
            # because IV and salt are random (therefore the encrypted payload as well) those data can't be asserted
            assert len(tx.signature) == 64

    def test_nem_signtx_xem_as_mosaic(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 76809215,
                "amount": 5000000,
                "fee": 1000000,
                "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 76895615,
                "version": (0x98 << 24),
                "message": {},
                "mosaics": [
                    {
                        "mosaicId": {"namespaceId": "nem", "name": "xem"},
                        "quantity": 9000000,
                    }
                ],
            },
        )

        # trezor should display 45 XEM (multiplied by amount)
        assert (
            tx.data.hex()
            == "0101000002000098ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f5595042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a404b4c000000000000000000010000001a0000000e000000030000006e656d0300000078656d4054890000000000"
        )
        assert (
            tx.signature.hex()
            == "7b25a84b65adb489ea55739f1ca2d83a0ae069c3c58d0ea075fc30bfe8f649519199ad2324ca229c6c3214191469f95326e99712124592cae7cd3a092c93ac0c"
        )

    def test_nem_signtx_unknown_mosaic(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 76809215,
                "amount": 2000000,
                "fee": 1000000,
                "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 76895615,
                "version": (0x98 << 24),
                "message": {},
                "mosaics": [
                    {
                        "mosaicId": {"namespaceId": "xxx", "name": "aa"},
                        "quantity": 3500000,
                    }
                ],
            },
        )

        # trezor should display warning about unknown mosaic and then dialog for 7000000 raw units of xxx.aa and 0 XEM
        assert (
            tx.data.hex()
            == "0101000002000098ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f5595042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e00000000000000000001000000190000000d00000003000000787878020000006161e067350000000000"
        )
        assert (
            tx.signature.hex()
            == "2f0280420eceb41ef9e5d94fa44ddda9cdc70b8f423ae18af577f6d85df64bb4aaf40cf24fc6eef47c63b0963611f8682348cecdc49a9b64eafcbe7afcb49102"
        )

    def test_nem_signtx_known_mosaic(self):

        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 76809215,
                "amount": 3000000,
                "fee": 1000000,
                "recipient": "NDMYSLXI4L3FYUQWO4MJOVL6BSTJJXKDSZRMT4LT",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 76895615,
                "version": (0x68 << 24),
                "message": {},
                "mosaics": [
                    {
                        "mosaicId": {"namespaceId": "dim", "name": "token"},
                        "quantity": 111000,
                    }
                ],
            },
        )

        # trezor should display 0 XEM and 0.333 DIMTOK
        assert (
            tx.data.hex()
            == "0101000002000068ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f559504280000004e444d59534c5849344c3346595551574f344d4a4f564c364253544a4a584b44535a524d54344c54c0c62d000000000000000000010000001c000000100000000300000064696d05000000746f6b656e98b1010000000000"
        )
        assert (
            tx.signature.hex()
            == "e7f14ef8c39727bfd257e109cd5acac31542f2e41f2e5deb258fc1db602b690eb1cabca41a627fe2adc51f3193db85c76b41c80bb60161eb8738ebf20b507104"
        )

    def test_nem_signtx_known_mosaic_with_levy(self):

        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 76809215,
                "amount": 2000000,
                "fee": 1000000,
                "recipient": "NDMYSLXI4L3FYUQWO4MJOVL6BSTJJXKDSZRMT4LT",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 76895615,
                "version": (0x68 << 24),
                "message": {},
                "mosaics": [
                    {
                        "mosaicId": {"namespaceId": "dim", "name": "coin"},
                        "quantity": 222000,
                    }
                ],
            },
        )

        # trezor should display 0 XEM and 0.444 DIM and levy of 0.000444 DIM
        assert (
            tx.data.hex()
            == "0101000002000068ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f559504280000004e444d59534c5849344c3346595551574f344d4a4f564c364253544a4a584b44535a524d54344c5480841e000000000000000000010000001b0000000f0000000300000064696d04000000636f696e3063030000000000"
        )
        assert (
            tx.signature.hex()
            == "d3222dd7b83d66bda0539827ac6f909d06e40350b5e5e893d6fa762f954e9bf7da61022ef04950e7b6dfa88a2278f2f8a1b21df2bc3af22b388cb3a90bf76f07"
        )

    def test_nem_signtx_multiple_mosaics(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 76809215,
                "amount": 2000000,
                "fee": 1000000,
                "recipient": "NDMYSLXI4L3FYUQWO4MJOVL6BSTJJXKDSZRMT4LT",
                "type": nem.TYPE_TRANSACTION_TRANSFER,
                "deadline": 76895615,
                "version": (0x68 << 24),
                "message": {},
                "mosaics": [
                    {
                        "mosaicId": {"namespaceId": "nem", "name": "xem"},
                        "quantity": 3000000,
                    },
                    {
                        "mosaicId": {"namespaceId": "abc", "name": "mosaic"},
                        "quantity": 200,
                    },
                    {
                        "mosaicId": {"namespaceId": "nem", "name": "xem"},
                        "quantity": 30000,
                    },
                    {
                        "mosaicId": {"namespaceId": "abc", "name": "mosaic"},
                        "quantity": 2000000,
                    },
                    {
                        "mosaicId": {"namespaceId": "breeze", "name": "breeze-token"},
                        "quantity": 111000,
                    },
                ],
            },
        )

        # trezor should display warning, 6.06 XEM, 4000400 raw units of abc.mosaic (mosaics are merged)
        # and 222000 BREEZE
        assert (
            tx.data.hex()
            == "0101000002000068ff03940420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208440420f00000000007f559504280000004e444d59534c5849344c3346595551574f344d4a4f564c364253544a4a584b44535a524d54344c5480841e000000000000000000030000001d0000001100000003000000616263060000006d6f7361696348851e0000000000260000001a00000006000000627265657a650c000000627265657a652d746f6b656e98b10100000000001a0000000e000000030000006e656d0300000078656df03b2e0000000000"
        )
        assert (
            tx.signature.hex()
            == "b2b9319fca87a05bee17108edd9a8f78aeffef74bf6b4badc6da5d46e8ff4fe82e24bf69d8e6c4097d072adf39d0c753e7580f8afb21e3288ebfb7c4d84e470d"
        )
