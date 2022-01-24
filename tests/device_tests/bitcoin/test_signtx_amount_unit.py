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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import assert_tx_matches

TX_API = TxCache("Testnet")

TXHASH_b36780 = bytes.fromhex(
    "b36780ceb86807ca6e7535a6fd418b1b788cb9b227d2c8a26a0de295e523219e"
)

VECTORS = (  # amount_unit
    None,
    messages.AmountUnit.BITCOIN,
    messages.AmountUnit.MILLIBITCOIN,
    messages.AmountUnit.MICROBITCOIN,
    messages.AmountUnit.SATOSHI,
)


@pytest.mark.parametrize("amount_unit", VECTORS)
def test_signtx(client: Client, amount_unit):
    inp1 = messages.TxInputType(
        # tb1qajr3a3y5uz27lkxrmn7ck8lp22dgytvagr5nqy
        address_n=parse_path("m/84h/1h/0h/0/87"),
        amount=100_000,
        prev_hash=TXHASH_b36780,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="2N4Q5FhU2497BryFfUgbqkAJE87aKHUhXMp",
        amount=40_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="tb1qe48wz5ysk9mlzhkswcxct9tdjw6ejr2l9e6j8q",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=100_000 - 40_000 - 10_000,
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

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/65047a2b107d6301d72d4a1e49e7aea9cf06903fdc4ae74a4a9bba9bc1a414d2",
        tx_hex="010000000001019e2123e595e20d6aa2c8d227b2b98c781b8b41fda635756eca0768b8ce8067b30000000000ffffffff02409c00000000000017a9147a55d61848e77ca266e79a39bfc85c580a6426c98750c3000000000000160014cd4ee15090b177f15ed0760d85956d93b5990d5f0247304402200c734ed16a9226162a29133c14fad3565332c60346050ceb9246e73a2fc8485002203463d40cf78eb5cc9718d6617d9f251b987e96cb58525795a507acb9b91696c7012103f60fc56bf7b5326537c7e86e0a63b6cd008eeb87d39af324cee5bcc3424bf4d000000000",
    )
