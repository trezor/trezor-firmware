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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API = TxCache("Bitcoin")
TX_API_TESTNET = TxCache("Testnet")

TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)
TXHASH_4075a1 = bytes.fromhex(
    "4075a1ae38ce607a20a9157840430354608201b3bfa2c7dba851473199f9d08f"
)


def test_opreturn(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/1h/0/21"),  # myGMXcCxmuDooMdzZFPMmvHviijzqYKhza
        amount=89_581,
        prev_hash=TXHASH_4075a1,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="2MyAH3SSRbmkABYPj8WCfizMiyUpmBB2j62",  # 49h/1h/0h/0/66
        amount=89_581 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        op_return_data=b"test of the op_return data",
        amount=0,
        script_type=messages.OutputScriptType.PAYTOOPRETURN,
    )

    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_4075a1),
                request_input(0, TXHASH_4075a1),
                request_output(0, TXHASH_4075a1),
                request_input(0),
                request_output(0),
                request_output(1),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Testnet", [inp1], [out1, out2], prev_txes=TX_API_TESTNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/c3185a82c0328304adfb52bfd07d4bca2c34f13153b32d9d034390365c46bbd2",
        tx_hex="01000000018fd0f999314751a8dbc7a2bfb3018260540343407815a9207a60ce38aea17540000000006b483045022100f6b228f0a1b8eb5037f13f28619aacc4c21a4c338318d631be2fda4cc653b6cf022015fc2975792f5d22d61601ca0523cad2d015b14fdf0ebe2af0790e3fac3ebbdb012102eee6b3ec6435f42ca071707eb1b14647d2121e0f8a53fa7fa9f92a691227a3d9ffffffff02dd3601000000000017a91440e1397e36e9bb6b731ac4ea186ba53111284e868700000000000000001c6a1a74657374206f6620746865206f705f72657475726e206461746100000000",
    )


def test_nonzero_opreturn(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/10h/0/5"),
        amount=390_000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        op_return_data=b"test of the op_return data",
        amount=10_000,
        script_type=messages.OutputScriptType.PAYTOOPRETURN,
    )

    with client:
        client.set_expected_responses(
            [request_input(0), request_output(0), messages.Failure()]
        )

        with pytest.raises(
            TrezorFailure, match="OP_RETURN output with non-zero amount"
        ):
            btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_API)


def test_opreturn_address(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/0h/0/2"),
        amount=390_000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/0h/0h/1/2"),
        amount=0,
        op_return_data=b"OMNI TRANSACTION GOES HERE",
        script_type=messages.OutputScriptType.PAYTOOPRETURN,
    )

    with client:
        client.set_expected_responses(
            [request_input(0), request_output(0), messages.Failure()]
        )
        with pytest.raises(
            TrezorFailure, match="Output's address_n provided but not expected."
        ):
            btc.sign_tx(client, "Bitcoin", [inp1], [out1], prev_txes=TX_API)
