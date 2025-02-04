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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import assert_tx_matches

TX_API = TxCache("Testnet")

TXHASH_b36780 = bytes.fromhex(
    "b36780ceb86807ca6e7535a6fd418b1b788cb9b227d2c8a26a0de295e523219e"
)
TXHASH_0dac36 = bytes.fromhex(
    "0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5"
)

VECTORS = (  # amount_unit
    None,
    messages.AmountUnit.BITCOIN,
    messages.AmountUnit.MILLIBITCOIN,
    messages.AmountUnit.MICROBITCOIN,
    messages.AmountUnit.SATOSHI,
)


@pytest.mark.parametrize("amount_unit", VECTORS)
def test_signtx_testnet(session: Session, amount_unit):
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
    with session:
        _, serialized_tx = btc.sign_tx(
            session,
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


@pytest.mark.parametrize("amount_unit", VECTORS)
def test_signtx_btc(session: Session, amount_unit):
    # input tx: 0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7",
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session:
        _, serialized_tx = btc.sign_tx(
            session,
            "Bitcoin",
            [inp1],
            [out1],
            prev_txes=TxCache("Bitcoin"),
            amount_unit=amount_unit,
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/b893aeed4b12227b6f5348d7f6cb84ba2cda2ba70a41933a25f363b9d2fc2cf9",
        tx_hex="0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006b483045022100dd4dd136a70371bc9884c3c51fd52f4aed9ab8ee98f3ac7367bb19e6538096e702200c56be09c4359fc7eb494b4bdf8f2b72706b0575c4021373345b593e9661c7b6012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0148c40000000000001976a91419140511436e947448be994ab7fda9f98623e68e88ac00000000",
    )
