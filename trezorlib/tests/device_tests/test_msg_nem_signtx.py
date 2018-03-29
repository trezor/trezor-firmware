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
@pytest.mark.skip_t2
class TestMsgNEMSigntx(TrezorTest):

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
                proto.NEMSignedTx(signature=signature),
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

        with self.client:
            self.client.set_expected_responses([
                # Confirm transfer and network fee
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Confirm recipient
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.NEMSignedTx(signature=signature),
            ])

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

    def test_nem_signtx_provision_namespace(self):

        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            self.client.set_expected_responses([
                # Confirm provision namespace
                proto.ButtonRequest(code=proto.ButtonRequestType.ConfirmOutput),
                # Confirm fee
                proto.ButtonRequest(code=proto.ButtonRequestType.SignTx),
                proto.NEMSignedTx(),
            ])

            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_PROVISION_NAMESPACE,
                "deadline": 74735615,
                "message": {
                },
                "newPart": "ABCDE",
                "rentalFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "rentalFee": 1500,
                "parent": None,
                "version": (0x98 << 24),
            })

            assert hexlify(tx.data) == b'01200000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324adc05000000000000050000004142434445ffffffff'
            assert hexlify(tx.signature) == b'f047ae7987cd3a60c0d5ad123aba211185cb6266a7469dfb0491a0df6b5cd9c92b2e2b9f396cc2a3146ee185ba02df4f9e7fb238fe479917b3d274d97336640d'

    def test_nem_signtx_mosaic_creation(self):
        # todo test levy
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            # todo assert responses, swipe down

            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_MOSAIC_CREATION,
                "deadline": 74735615,
                "message": {
                },
                "mosaicDefinition": {
                    "id": {
                        "namespaceId": "hellom",
                        "name": "Hello mosaic"
                    },
                    "levy": {},
                    "properties": {},
                    "description": "lorem"
                },
                "version": (0x98 << 24),
                "creationFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "creationFee": 1500,
            })

            assert hexlify(tx.data) == b'01400000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f7404c100000020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b40620841a0000000600000068656c6c6f6d0c00000048656c6c6f206d6f73616963050000006c6f72656d04000000150000000c00000064697669736962696c6974790100000030160000000d000000696e697469616c537570706c7901000000301a0000000d000000737570706c794d757461626c650500000066616c7365190000000c0000007472616e7366657261626c650500000066616c7365000000002800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324adc05000000000000'
            assert hexlify(tx.signature) == b'537adf4fd9bd5b46e204b2db0a435257a951ed26008305e0aa9e1201dafa4c306d7601a8dbacabf36b5137724386124958d53202015ab31fb3d0849dfed2df0e'

    def test_nem_signtx_mosaic_creation_properties(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            # todo assert responses, swipe down
            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_MOSAIC_CREATION,
                "deadline": 74735615,
                "message": {
                },
                "mosaicDefinition": {
                    "id": {
                        "namespaceId": "hellom",
                        "name": "Hello mosaic"
                    },
                    "levy": {},
                    "properties": [
                        {
                            "name": "divisibility",
                            "value": "4"
                        },
                        {
                            "name": "initialSupply",
                            "value": "200"
                        },
                        {
                            "name": "supplyMutable",
                            "value": "false"
                        },
                        {
                            "name": "transferable",
                            "value": "true"
                        }
                    ],
                    "description": "lorem"
                },
                "version": (0x98 << 24),
                "creationFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "creationFee": 1500,
            })

            assert hexlify(tx.data) == b'01400000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f7404c200000020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b40620841a0000000600000068656c6c6f6d0c00000048656c6c6f206d6f73616963050000006c6f72656d04000000150000000c00000064697669736962696c6974790100000034180000000d000000696e697469616c537570706c79030000003230301a0000000d000000737570706c794d757461626c650500000066616c7365180000000c0000007472616e7366657261626c650400000074727565000000002800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324adc05000000000000'
            assert hexlify(tx.signature) == b'f17c859710060f2ea9a0ab740ef427431cf36bdc7d263570ca282bd66032e9f5737a921be9839429732e663be2bb74ccc16f34f5157ff2ef00a65796b54e800e'

    def test_nem_signtx_mosaic_creation_levy(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            # todo assert responses, swipe down
            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_MOSAIC_CREATION,
                "deadline": 74735615,
                "message": {
                },
                "mosaicDefinition": {
                    "id": {
                        "namespaceId": "hellom",
                        "name": "Hello mosaic"
                    },
                    "properties": [
                        {
                            "name": "divisibility",
                            "value": "4"
                        },
                        {
                            "name": "initialSupply",
                            "value": "200"
                        },
                        {
                            "name": "supplyMutable",
                            "value": "false"
                        },
                        {
                            "name": "transferable",
                            "value": "true"
                        }
                    ],
                    "levy": {
                        "type": 1,
                        "fee": 2,
                        "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                        "mosaicId": {
                            "namespaceId": "hellom",
                            "name": "Hello mosaic"
                        },
                    },
                    "description": "lorem"
                },
                "version": (0x98 << 24),
                "creationFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "creationFee": 1500,
            })

            assert hexlify(tx.data) == b'01400000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74041801000020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b40620841a0000000600000068656c6c6f6d0c00000048656c6c6f206d6f73616963050000006c6f72656d04000000150000000c00000064697669736962696c6974790100000034180000000d000000696e697469616c537570706c79030000003230301a0000000d000000737570706c794d757461626c650500000066616c7365180000000c0000007472616e7366657261626c65040000007472756556000000010000002800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a1a0000000600000068656c6c6f6d0c00000048656c6c6f206d6f7361696302000000000000002800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324adc05000000000000'
            assert hexlify(tx.signature) == b'b87aac1ddf146d35e6a7f3451f57e2fe504ac559031e010a51261257c37bd50fcfa7b2939dd7a3203b54c4807d458475182f5d3dc135ec0d1d4a9cd42159fd0a'

    def test_nem_signtx_mosaic_supply_change(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_MOSAIC_SUPPLY_CHANGE,
                "deadline": 74735615,
                "message": {
                },
                "mosaicId": {
                    "namespaceId": "hellom",
                    "name": "Hello mosaic"
                },
                "supplyType": 1,
                "delta": 1,
                "version": (0x98 << 24),
                "creationFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                "creationFee": 1500,
            })

            assert hexlify(tx.data) == b'02400000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74041a0000000600000068656c6c6f6d0c00000048656c6c6f206d6f73616963010000000100000000000000'
            assert hexlify(tx.signature) == b'928b03c4a69fff35ecf0912066ea705895b3028fad141197d7ea2b56f1eef2a2516455e6f35d318f6fa39e2bb40492ac4ae603260790f7ebc7ea69feb4ca4c0a'

    def test_nem_signtx_aggregate_modification(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_AGGREGATE_MODIFICATION,
                "deadline": 74735615,
                "message": {
                },
                "modifications": [
                    {
                        "modificationType": 1,  # Add
                        "cosignatoryAccount": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844"
                    },
                ],
                "version": (0x98 << 24),
            })

            assert hexlify(tx.data) == b'01100000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f740401000000280000000100000020000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844'
            assert hexlify(tx.signature) == b'ed074a4b877e575786785e6e499e428edea28498a06bdaed6557ccdfbfe69087acd6f4b63e9faa6a849e49d405374c12762df2f27d55e4b35c1901850f83650f'

    def test_nem_signtx_importance_transfer(self):
        self.setup_mnemonic_nopin_nopassphrase()

        with self.client:
            tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
                "timeStamp": 12349215,
                "fee": 9900,
                "type": nem.TYPE_IMPORTANCE_TRANSFER,
                "deadline": 99,
                "message": {
                },
                "importanceTransfer": {
                    "mode": 1,
                    "publicKey": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844",
                },
                "version": (0x98 << 24),
            })

            assert hexlify(tx.data) == b'01080000010000981f6fbc0020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b4062084ac26000000000000630000000100000020000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844'
            assert hexlify(tx.signature) == b'b6d9434ec5df80e65e6e45d7f0f3c579b4adfe8567c42d981b06e8ac368b1aad2b24eebecd5efd41f4497051fca8ea8a5e77636a79afc46ee1a8e0fe9e3ba90b'
