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

from trezorlib import nem
from trezorlib.tools import parse_path

from .common import TrezorTest


# assertion data from T1
@pytest.mark.nem
class TestMsgNEMSignTxMultisig(TrezorTest):
    def test_nem_signtx_aggregate_modification(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 74649215,
                "fee": 2000000,
                "type": nem.TYPE_AGGREGATE_MODIFICATION,
                "deadline": 74735615,
                "message": {},
                "modifications": [
                    {
                        "modificationType": 1,  # Add
                        "cosignatoryAccount": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844",
                    }
                ],
                "minCosignatories": {"relativeChange": 3},
                "version": (0x98 << 24),
            },
        )
        assert (
            tx.data.hex()
            == "01100000020000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b406208480841e0000000000ff5f740401000000280000000100000020000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f878440400000003000000"
        )
        assert (
            tx.signature.hex()
            == "1200e552d8732ce3eae96719731194abfc5a09d98f61bb35684f4eeaeff15b1bdf326ee7b1bbbe89d3f68c8e07ad3daf72e4c7f031094ad2236b97918ad98601"
        )

    def test_nem_signtx_multisig(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 1,
                "fee": 10000,
                "type": nem.TYPE_MULTISIG,
                "deadline": 74735615,
                "otherTrans": {  # simple transaction transfer
                    "timeStamp": 2,
                    "amount": 2000000,
                    "fee": 15000,
                    "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "type": nem.TYPE_TRANSACTION_TRANSFER,
                    "deadline": 67890,
                    "message": {
                        "payload": b"test_nem_transaction_transfer".hex(),
                        "type": 1,
                    },
                    "version": (0x98 << 24),
                    "signer": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844",
                },
                "version": (0x98 << 24),
            },
        )

        assert (
            tx.data.hex()
            == "04100000010000980100000020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b40620841027000000000000ff5f74049900000001010000010000980200000020000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844983a000000000000320901002800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324a80841e000000000025000000010000001d000000746573745f6e656d5f7472616e73616374696f6e5f7472616e73666572"
        )
        assert (
            tx.signature.hex()
            == "0cab2fddf2f02b5d7201675b9a71869292fe25ed33a366c7d2cbea7676fed491faaa03310079b7e17884b6ba2e3ea21c4f728d1cca8f190b8288207f6514820a"
        )

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 74649215,
                "fee": 150,
                "type": nem.TYPE_MULTISIG,
                "deadline": 789,
                "otherTrans": {
                    "timeStamp": 123456,
                    "fee": 2000,
                    "type": nem.TYPE_PROVISION_NAMESPACE,
                    "deadline": 100,
                    "message": {},
                    "newPart": "ABCDE",
                    "rentalFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "rentalFee": 1500,
                    "parent": None,
                    "version": (0x98 << 24),
                    "signer": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844",
                },
                "version": (0x98 << 24),
            },
        )

        assert (
            tx.data.hex()
            == "04100000010000987f0e730420000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b40620849600000000000000150300007d000000012000000100009840e2010020000000c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844d007000000000000640000002800000054414c49434532474d4133344358484437584c4a513533364e4d35554e4b5148544f524e4e54324adc05000000000000050000004142434445ffffffff"
        )
        assert (
            tx.signature.hex()
            == "c915ca3332380925f4050301cdc62269cf29437ac5955321b18da34e570c7fdbb1aec2940a2a553a2a5c90950a4db3c8d3ef899c1a108582e0657f66fbbb0b04"
        )

    def test_nem_signtx_multisig_signer(self):
        self.setup_mnemonic_nopin_nopassphrase()

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 333,
                "fee": 200,
                "type": nem.TYPE_MULTISIG_SIGNATURE,
                "deadline": 444,
                "otherTrans": {  # simple transaction transfer
                    "timeStamp": 555,
                    "amount": 2000000,
                    "fee": 2000000,
                    "recipient": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "type": nem.TYPE_TRANSACTION_TRANSFER,
                    "deadline": 666,
                    "message": {
                        "payload": b"test_nem_transaction_transfer".hex(),
                        "type": 1,
                    },
                    "version": (0x98 << 24),
                    "signer": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844",
                },
                "version": (0x98 << 24),
            },
        )

        assert (
            tx.data.hex()
            == "02100000010000984d01000020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b4062084c800000000000000bc010000240000002000000087923cd4805f3babe6b5af9cbb2b08be4458e39531618aed73c911f160c8e38528000000544444324354364c514c49595135364b49584933454e544d36454b3344343450354b5a50464d4b32"
        )
        assert (
            tx.signature.hex()
            == "286358a16ae545bff798feab93a713440c7c2f236d52ac0e995669d17a1915b0903667c97fa04418eccb42333cba95b19bccc8ac1faa8224dcfaeb41890ae807"
        )

        tx = nem.sign_tx(
            self.client,
            parse_path("m/44'/1'/0'/0'/0'"),
            {
                "timeStamp": 900000,
                "fee": 200000,
                "type": nem.TYPE_MULTISIG_SIGNATURE,
                "deadline": 100,
                "otherTrans": {  # simple transaction transfer
                    "timeStamp": 101111,
                    "fee": 1000,
                    "type": nem.TYPE_MOSAIC_SUPPLY_CHANGE,
                    "deadline": 13123,
                    "message": {},
                    "mosaicId": {"namespaceId": "hellom", "name": "Hello mosaic"},
                    "supplyType": 1,
                    "delta": 1,
                    "version": (0x98 << 24),
                    "creationFeeSink": "TALICE2GMA34CXHD7XLJQ536NM5UNKQHTORNNT2J",
                    "creationFee": 1500,
                    "signer": "c5f54ba980fcbb657dbaaa42700539b207873e134d2375efeab5f1ab52f87844",
                },
                "version": (0x98 << 24),
            },
        )

        assert (
            tx.data.hex()
            == "0210000001000098a0bb0d0020000000edfd32f6e760648c032f9acb4b30d514265f6a5b5f8a7154f2618922b4062084400d030000000000640000002400000020000000c51395626a89a71c1ed785fb5974307a049b3b9e2165d56ed0302fe6b4f02a0128000000544444324354364c514c49595135364b49584933454e544d36454b3344343450354b5a50464d4b32"
        )
        assert (
            tx.signature.hex()
            == "32b1fdf788c4a90c01eedf5972b7709745831d620c13e1e97b0de6481837e162ee551573f2409822754ae940731909ec4b79cf836487e898df476adb10467506"
        )
