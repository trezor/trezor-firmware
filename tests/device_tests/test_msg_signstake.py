# This file is part of the Trezor project.
#
# Copyright (C) 2021 SatoshiLabs and contributors
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

from trezorlib import btc
from trezorlib.tools import parse_path

SCHNORRBCH_SIGNATURE_LENGTH = 64


def case(id, *args, altcoin=False):
    if altcoin:
        marks = pytest.mark.altcoin
    else:
        marks = ()
    return pytest.param(*args, id=id, marks=marks)


VECTORS = (  # case name, coin_name, address, txid, index, amount, height, is_coinbase, proofid, pubkey, signature
    case(
        # Extracted from an avalanche proof generated with Electrum ABC
        "Bitcoin ABC Testnet",
        "Bitcoin ABC Testnet",
        "44h/1h/0h/0/0",
        "0e480a97c7a545c85e101a2f13c9af0e115d43734e1448f0cac3e55fe8e7399d",
        2,
        60523789,
        1063500,
        False,
        "e8c5a7f70da287db84d7f8fcf8a36c486f82321c51746cdc6a151cf121a34868",
        "030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0",
        "47ca9a639293dadafc92bb3d91f24b53e4939a398093486a5dc110666f6a71a6"
        "aaf31b3876ddfb48ed0553953a264f5d8dee8e8a73b09c65265e9a3b228850c7",
    ),
)


@pytest.mark.skip_t1
@pytest.mark.altcoin
@pytest.mark.parametrize(
    "coin_name, path, txid, index, amount, height, is_coinbase, proofid, pubkey, signature",
    VECTORS,
)
def test_signstake(
    client,
    coin_name,
    path,
    txid,
    index,
    amount,
    height,
    is_coinbase,
    proofid,
    pubkey,
    signature,
):
    res = btc.sign_stake(
        client,
        coin_name=coin_name,
        address_n=parse_path(path),
        txid=bytes.fromhex(txid),
        index=index,
        amount=amount,
        height=height,
        is_coinbase=is_coinbase,
        proofid=bytes.fromhex(proofid),
    )

    assert res.pubkey.hex() == pubkey
    assert len(res.signature) == SCHNORRBCH_SIGNATURE_LENGTH
    assert res.signature.hex() == signature
