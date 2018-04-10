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

from trezorlib import nem


# assertion data from T1
@pytest.mark.xfail  # to be removed when nem is merged
class TestMsgNEMSignTxMultisig(TrezorTest):

    def test_nem_signtx_aggregate_modification(self):
        self.setup_mnemonic_nopin_nopassphrase()

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
            "minCosignatories": {
                "relativeChange": 3
            },
            "version": (0x98 << 24),
        })
        assert hexlify(tx.data) == b'01100000020000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f740401000000280000000100000020000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f878440400000003000000'
        assert hexlify(tx.signature) == b'1200e552d8732ce3eae96719731194abfc5a09d98f61bb35684f4eeaeff15b1bdf326ee7b1bbbe89d3f68c8e07ad3daf72e4c7f031094ad2236b97918ad98601'

    def test_nem_signtx_multisig(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
            "timeStamp": 74649215,
            "fee": 2000000,
            "type": nem.TYPE_MULTISIG,
            "deadline": 74735615,
            "otherTrans": {  # simple transaction transfer
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
                "signer": 'c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844',
            },
            "version": (0x98 << 24),
        })

        assert hexlify(tx.data) == b'04100000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74049900000001010000010000987f0e730420000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f8784480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e000000000025000000010000001d000000746573745f6e656d5f7472616e73616374696f6e5f7472616e73666572'
        assert hexlify(tx.signature) == b'c42e828ec1686ef8f6ee6af0f28bd8468bd5861a61e440889b07b359ccdf61b369295a54102634c9ccab0a577e100183740395031e835c22855dcdeebd328008'

        tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
            "timeStamp": 74649215,
            "fee": 2000000,
            "type": nem.TYPE_MULTISIG,
            "deadline": 74735615,
            "otherTrans": {
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
                "signer": 'c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844',
            },
            "version": (0x98 << 24),
        })

        assert hexlify(tx.data) == b'04100000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74047d00000001200000010000987f0e730420000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f8784480841e0000000000ff5f74042800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324adc05000000000000050000004142434445ffffffff'
        assert hexlify(tx.signature) == b'1b67c2c91240ab55bc2762a673d43745bd1e08206b64bd52501ef945d511c73a1b7cf4d6c1d7f97bd31e13a8a2eafce0707b6331d60d0808d5ac4d1e8dba970e'

    def test_nem_signtx_multisig_signer(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
            "timeStamp": 74649215,
            "fee": 2000000,
            "type": nem.TYPE_MULTISIG_SIGNATURE,
            "deadline": 74735615,
            "otherTrans": {  # simple transaction transfer
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
                "signer": 'c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844',
            },
            "version": (0x98 << 24),
        })

        assert hexlify(tx.data) == b'02100000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042400000020000000e03479740771665bdd292df6fc29c9c63e72b0dbcba95ede615614acda979bf328000000544444324354364c514c49595135364b49584933454e544d36454b3344343450354b5a50464d4b32'
        assert hexlify(tx.signature) == b'ff731324a2269fd27e103c88a23ef767667a6641e339de3ce84d8cfeed000dcc18f9af1c68b4a12798a312b2e588c7b7174b578c5fc7503e5a5ef15562abed03'

        tx = self.client.nem_sign_tx(self.client.expand_path("m/44'/1'/0'/0'/0'"), {
            "timeStamp": 74649215,
            "fee": 2000000,
            "type": nem.TYPE_MULTISIG_SIGNATURE,
            "deadline": 74735615,
            "otherTrans": {  # simple transaction transfer
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
                "signer": 'c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844',
            },
            "version": (0x98 << 24),
        })

        assert hexlify(tx.data) == b'02100000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f74042400000020000000d4773c2daeb338a1f41e1595bcabf7a1d788517235c9796c6fd5e094f1aa474d28000000544444324354364c514c49595135364b49584933454e544d36454b3344343450354b5a50464d4b32'
        assert hexlify(tx.signature) == b'9f72079ece8d3bf647da3c09d03e39e94cbc98c525128c5f9cef1d24666b57e1960d95db3199d56435ff9faaf098860248fc8b5d859ddd9049a6f7a5973f320f'


