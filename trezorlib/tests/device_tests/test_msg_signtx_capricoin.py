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

from trezorlib import btc, messages
from trezorlib.tools import parse_path

from ..support.tx_cache import tx_cache
from .conftest import setup_client

TXHASH_3bf506 = bytes.fromhex(
    "3bf506c81ce84eda891679ddc797d162c17c60b15d6c0ac23be5e31369e7235f"
)

TXHASH_f3a6e6 = bytes.fromhex(
    "f3a6e6411f1b2dffd76d2729bae8e056f8f9ecf8996d3f428e75a6f23f2c5e8c"
)


@pytest.mark.capricoin
@pytest.mark.skip_t1  # T1 support is not planned
@setup_client()
def test_timestamp_included(client):
    # tx: 3bf506c81ce84eda891679ddc797d162c17c60b15d6c0ac23be5e31369e7235f
    # input 0: 0.01 CPC
    # tx: f3a6e6411f1b2dffd76d2729bae8e056f8f9ecf8996d3f428e75a6f23f2c5e8c
    # input 0: 0.02 CPC

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44'/289'/0'/0/0"), prev_hash=TXHASH_3bf506, prev_index=0
    )

    inp2 = messages.TxInputType(
        address_n=parse_path("m/44'/289'/0'/0/0"), prev_hash=TXHASH_f3a6e6, prev_index=1
    )

    out1 = messages.TxOutputType(
        address="CUGi8RGPWxbHM6FxF4eMEfqmQ6Bs5VjCdr",
        amount=3000000 - 20000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        details = messages.SignTx(version=1, timestamp=0x5BCF5C66)
        _, timestamp_tx = btc.sign_tx(
            client,
            "Capricoin",
            [inp1, inp2],
            [out1],
            details=details,
            prev_txes=tx_cache("Capricoin"),
        )

    # Accepted by network https://insight.capricoin.org/tx/1bf227e6e24fe1f8ac98849fe06a2c5b77762e906fcf7e82787675f7f3a10bb8
    accepted_txhex = "01000000665ccf5b025f23e76913e3e53bc20a6c5db1607cc162d197c7dd791689da4ee81cc806f53b000000006b483045022100fce7ccbeb9524f36d118ebcfebcb133a05c236c4478e2051cfd5c9632920aee602206921b7be1a81f30cce3d8e7dba4597fc16a2761c42321c49d65eeacdfe3781250121021fcf98aee04939ec7df5762f426dc2d1db8026e3a73c3bbe44749dacfbb61230ffffffff8c5e2c3ff2a6758e423f6d99f8ecf9f856e0e8ba29276dd7ff2d1b1f41e6a6f3010000006a473044022015d967166fe9f89fbed8747328b1c4658aa1d7163e731c5fd5908feafe08e9a6022028af30801098418bd298cc60b143c52c48466f5791256721304b6eba4fdf0b3c0121021fcf98aee04939ec7df5762f426dc2d1db8026e3a73c3bbe44749dacfbb61230ffffffff01a0782d00000000001976a914818437acfd15780debd31f3fd21d4ca678bb36d188ac00000000"
    assert timestamp_tx.hex() == accepted_txhex
