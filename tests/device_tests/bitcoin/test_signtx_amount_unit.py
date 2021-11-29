# This file is part of the Trezor project.
#
# Copyright (C) 2012-2020 SatoshiLabs and contributors
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

TX_API = TxCache("Testnet")

TXHASH_091446 = bytes.fromhex(
    "09144602765ce3dd8f4329445b20e3684e948709c5cdcaf12da3bb079c99448a"
)

VECTORS = (  # amount_unit
    None,
    messages.AmountUnit.BITCOIN,
    messages.AmountUnit.MILLIBITCOIN,
    messages.AmountUnit.MICROBITCOIN,
    messages.AmountUnit.SATOSHI,
)


@pytest.mark.parametrize("amount_unit", VECTORS)
def test_signtx(client, amount_unit):
    inp1 = messages.TxInputType(
        address_n=parse_path("84'/1'/0'/0/0"),
        amount=12300000,
        prev_hash=TXHASH_091446,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=5000000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=12300000 - 11000 - 5000000,
    )
    with client:
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            [inp1],
            [out1, out2],
            prev_txes=TX_API,
            amount_unit=amount_unit,
        )

    assert (
        serialized_tx.hex()
        == "010000000001018a44999c07bba32df1cacdc50987944e68e3205b4429438fdde35c76024614090000000000ffffffff02404b4c000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c987a8386f0000000000160014d16b8c0680c61fc6ed2e407455715055e41052f502473044022073ce72dcf2f6e42eeb44adbe7d5038cf3763f168d1c04bd8b873a19b53331f51022016b051725731e7f53a567021bcd9c370727f551c81e857ebae7c128472119652012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000"
    )
