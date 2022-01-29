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
from ..signtx import (
    request_extra_data,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API = TxCache("Komodo")

TXHASH_2807c = bytes.fromhex(
    "2807c5b126ec8e2b078cab0f12e4c8b4ce1d7724905f8ebef8dca26b0c8e0f1d"
)
TXHASH_7b28bd = bytes.fromhex(
    "7b28bd91119e9776f0d4ebd80e570165818a829bbf4477cd1afe5149dbcd34b1"
)

pytestmark = [pytest.mark.altcoin, pytest.mark.komodo]


def test_one_one_fee_sapling(client):
    # prevout: 2807c5b126ec8e2b078cab0f12e4c8b4ce1d7724905f8ebef8dca26b0c8e0f1d:0
    # input 1: 10.9998 KMD

    inp1 = messages.TxInputType(
        # R9HgJZo6JBKmPvhm7whLSR8wiHyZrEDVRi
        address_n=parse_path("44'/141'/0'/0/0"),
        amount=1099980000,
        prev_hash=TXHASH_2807c,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="R9HgJZo6JBKmPvhm7whLSR8wiHyZrEDVRi",
        amount=1099980000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_2807c),
                request_input(0, TXHASH_2807c),
                request_output(0, TXHASH_2807c),
                request_extra_data(0, 11, TXHASH_2807c),
                request_input(0),
                request_output(0),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client,
            "Komodo",
            [inp1],
            [out1],
            version=4,
            version_group_id=0x892F2085,
            branch_id=0x76B809BB,
            lock_time=0x5D2A30B8,
            prev_txes=TX_API,
        )

    # Accepted by network: tx 7b28bd91119e9776f0d4ebd80e570165818a829bbf4477cd1afe5149dbcd34b1
    assert (
        serialized_tx.hex()
        == "0400008085202f89011d0f8e0c6ba2dcf8be8e5f9024771dceb4c8e4120fab8c072b8eec26b1c50728000000006a4730440220158c970ca2fc6bcc33026eb5366f0342f63b35d178f7efb334b1df78fe90b67202207bc4ff69f67cf843b08564a5adc77bf5593e28ab4d5104911824ac13fe885d8f012102a87aef7b1a8f676e452d6240767699719cd58b0261c822472c25df146938bca5ffffffff01d0359041000000001976a91400178fa0b6fc253a3a402ee2cadd8a7bfec08f6388acb8302a5d000000000000000000000000000000"
    )


def test_one_one_rewards_claim(client):
    # prevout: 7b28bd91119e9776f0d4ebd80e570165818a829bbf4477cd1afe5149dbcd34b1:0
    # input 1: 10.9997 KMD

    inp1 = messages.TxInputType(
        # R9HgJZo6JBKmPvhm7whLSR8wiHyZrEDVRi
        address_n=parse_path("44'/141'/0'/0/0"),
        amount=1099970000,
        prev_hash=TXHASH_7b28bd,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="R9HgJZo6JBKmPvhm7whLSR8wiHyZrEDVRi",
        amount=1099970000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # kmd interest, vout sum > vin sum
    out2 = messages.TxOutputType(
        address="R9HgJZo6JBKmPvhm7whLSR8wiHyZrEDVRi",
        amount=79605,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_7b28bd),
                request_input(0, TXHASH_7b28bd),
                request_output(0, TXHASH_7b28bd),
                request_extra_data(0, 11, TXHASH_7b28bd),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client,
            "Komodo",
            [inp1],
            [out1, out2],
            prev_txes=TX_API,
            version=4,
            version_group_id=0x892F2085,
            branch_id=0x76B809BB,
            lock_time=0x5D2AF1F2,
        )

    # Accepted by network: tx c775678ceb18277729b427c7acf2f8ce63ac02fc2366f47ce08a3f443ff0e059
    assert (
        serialized_tx.hex()
        == "0400008085202f8901b134cddb4951fe1acd7744bf9b828a816501570ed8ebd4f076979e1191bd287b000000006a4730440220483a58f5be3a147c773c663008c992a7fcea4d03bdf4c1d4bc0535c0d98ddf0602207b19d69140dd00c7a94f048c712aeaed55dfd27f581c7212d9cc5e476fe1dc9f012102a87aef7b1a8f676e452d6240767699719cd58b0261c822472c25df146938bca5ffffffff02c00e9041000000001976a91400178fa0b6fc253a3a402ee2cadd8a7bfec08f6388acf5360100000000001976a91400178fa0b6fc253a3a402ee2cadd8a7bfec08f6388acf2f12a5d000000000000000000000000000000"
    )
