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

from trezorlib import btc, messages
from trezorlib.tools import parse_path

from ...tx_cache import TxCache

B = messages.ButtonRequestType
TX_API = TxCache("Groestlcoin")
TX_API_TESTNET = TxCache("Groestlcoin Testnet")

TXHASH_cb74c8 = bytes.fromhex(
    "cb74c8478c5814742c87cffdb4a21231869888f8042fb07a90e015a9db1f9d4a"
)
TXHASH_09a48b = bytes.fromhex(
    "09a48bce2f9d5c6e4f0cb9ea1b32d0891855e8acfe5334f9ebd72b9ad2de60cf"
)
TXHASH_4f2f85 = bytes.fromhex(
    "4f2f857f39ed1afe05542d058fb0be865a387446e32fc876d086203f483f61d1"
)

pytestmark = pytest.mark.altcoin


def test_legacy(client):
    inp1 = messages.TxInputType(
        # FXHDsC5ZqWQHkDmShzgRVZ1MatpWhwxTAA
        address_n=parse_path("44'/17'/0'/0/2"),
        amount=210016,
        prev_hash=TXHASH_cb74c8,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="FtM4zAn9aVYgHgxmamWBgWPyZsb6RhvkA9",
        amount=210016 - 192,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Groestlcoin", [inp1], [out1], prev_txes=TX_API
    )
    assert (
        serialized_tx.hex()
        == "01000000014a9d1fdba915e0907ab02f04f88898863112a2b4fdcf872c7414588c47c874cb000000006a47304402201fb96d20d0778f54520ab59afe70d5fb20e500ecc9f02281cf57934e8029e8e10220383d5a3e80f2e1eb92765b6da0f23d454aecbd8236f083d483e9a7430236876101210331693756f749180aeed0a65a0fab0625a2250bd9abca502282a4cf0723152e67ffffffff01a0330300000000001976a914fe40329c95c5598ac60752a5310b320cb52d18e688ac00000000"
    )


def test_legacy_change(client):
    inp1 = messages.TxInputType(
        # FXHDsC5ZqWQHkDmShzgRVZ1MatpWhwxTAA
        address_n=parse_path("44'/17'/0'/0/2"),
        amount=210016,
        prev_hash=TXHASH_cb74c8,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("44'/17'/0'/0/3"),  # FtM4zAn9aVYgHgxmamWBgWPyZsb6RhvkA9
        amount=210016 - 192,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Groestlcoin", [inp1], [out1], prev_txes=TX_API
    )
    assert (
        serialized_tx.hex()
        == "01000000014a9d1fdba915e0907ab02f04f88898863112a2b4fdcf872c7414588c47c874cb000000006a47304402201fb96d20d0778f54520ab59afe70d5fb20e500ecc9f02281cf57934e8029e8e10220383d5a3e80f2e1eb92765b6da0f23d454aecbd8236f083d483e9a7430236876101210331693756f749180aeed0a65a0fab0625a2250bd9abca502282a4cf0723152e67ffffffff01a0330300000000001976a914fe40329c95c5598ac60752a5310b320cb52d18e688ac00000000"
    )


def test_send_segwit_p2sh(client):
    inp1 = messages.TxInputType(
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7
        address_n=parse_path("49'/1'/0'/1/0"),
        amount=123456789,
        prev_hash=TXHASH_09a48b,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        sequence=0xFFFFFFFE,
    )
    out1 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y",
        amount=12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7",
        amount=123456789 - 11000 - 12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client,
        "Groestlcoin Testnet",
        [inp1],
        [out1, out2],
        lock_time=650756,
        prev_txes=TX_API_TESTNET,
    )
    assert (
        serialized_tx.hex()
        == "01000000000101cf60ded29a2bd7ebf93453feace8551889d0321beab90c4f6e5c9d2fce8ba4090000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5feffffff02e0aebb00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7904ee0900"
    )


def test_send_segwit_p2sh_change(client):
    inp1 = messages.TxInputType(
        # 2N1LGaGg836mqSQqiuUBLfcyGBhyZYBtBZ7
        address_n=parse_path("49'/1'/0'/1/0"),
        amount=123456789,
        prev_hash=TXHASH_09a48b,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        sequence=0xFFFFFFFE,
    )
    out1 = messages.TxOutputType(
        address="mvbu1Gdy8SUjTenqerxUaZyYjmvedc787y",
        amount=12300000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("49'/1'/0'/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=123456789 - 11000 - 12300000,
    )
    _, serialized_tx = btc.sign_tx(
        client,
        "Groestlcoin Testnet",
        [inp1],
        [out1, out2],
        lock_time=650756,
        prev_txes=TX_API_TESTNET,
    )
    assert (
        serialized_tx.hex()
        == "01000000000101cf60ded29a2bd7ebf93453feace8551889d0321beab90c4f6e5c9d2fce8ba4090000000017160014d16b8c0680c61fc6ed2e407455715055e41052f5feffffff02e0aebb00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac3df39f060000000017a91458b53ea7f832e8f096e896b8713a8c6df0e892ca8702483045022100b7ce2972bcbc3a661fe320ba901e680913b2753fcb47055c9c6ba632fc4acf81022001c3cfd6c2fe92eb60f5176ce0f43707114dd7223da19c56f2df89c13c2fef80012103e7bfe10708f715e8538c92d46ca50db6f657bbc455b7494e6a0303ccdb868b7904ee0900"
    )


def test_send_segwit_native(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/0/0"),
        amount=12300000,
        prev_hash=TXHASH_4f2f85,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
        sequence=0xFFFFFFFE,
    )
    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e",
        amount=5000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="tgrs1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt9lkd57",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=12300000 - 11000 - 5000000,
    )
    _, serialized_tx = btc.sign_tx(
        client,
        "Groestlcoin Testnet",
        [inp1],
        [out1, out2],
        lock_time=650713,
        prev_txes=TX_API_TESTNET,
    )
    assert (
        serialized_tx.hex()
        == "01000000000101d1613f483f2086d076c82fe34674385a86beb08f052d5405fe1aed397f852f4f0000000000feffffff02404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987a8386f0000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b02483045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862d9ed0900"
    )


def test_send_segwit_native_change(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/0/0"),
        amount=12300000,
        prev_hash=TXHASH_4f2f85,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
        sequence=0xFFFFFFFE,
    )
    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKDv3V3e",
        amount=5000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("84'/1'/0'/1/0"),
        script_type=messages.OutputScriptType.PAYTOWITNESS,
        amount=12300000 - 11000 - 5000000,
    )
    _, serialized_tx = btc.sign_tx(
        client,
        "Groestlcoin Testnet",
        [inp1],
        [out1, out2],
        lock_time=650713,
        prev_txes=TX_API_TESTNET,
    )
    assert (
        serialized_tx.hex()
        == "01000000000101d1613f483f2086d076c82fe34674385a86beb08f052d5405fe1aed397f852f4f0000000000feffffff02404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987a8386f0000000000160014cc8067093f6f843d6d3e22004a4290cd0c0f336b02483045022100ea8780bc1e60e14e945a80654a41748bbf1aa7d6f2e40a88d91dfc2de1f34bd10220181a474a3420444bd188501d8d270736e1e9fe379da9970de992ff445b0972e3012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f862d9ed0900"
    )
