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
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ..tx_cache import TxCache

TX_CACHE = TxCache("Peercoin")

TXHASH_41b29a = bytes.fromhex(
    "41b29ad615d8eea40a4654a052d18bb10cd08f203c351f4d241f88b031357d3d"
)


@pytest.mark.altcoin
@pytest.mark.peercoin
def test_timestamp_included(client):
    # tx: 41b29ad615d8eea40a4654a052d18bb10cd08f203c351f4d241f88b031357d3d
    # input 0: 0.1 PPC

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44'/6'/0'/0/0"),
        amount=100000,
        prev_hash=TXHASH_41b29a,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="PXtfyTjzgXSgTwK5AbszdHQSSxyQN3BLM5",
        amount=100000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    details = messages.SignTx(version=1, timestamp=0x5DC5448A)
    _, timestamp_tx = btc.sign_tx(
        client, "Peercoin", [inp1], [out1], details=details, prev_txes=TX_CACHE,
    )

    # Accepted by network https://explorer.peercoin.net/api/getrawtransaction?txid=f7e3624c143b6a170cc44f9337d0fa8ea8564a211de9c077c6889d8c78f80909&decrypt=1
    accepted_txhex = "010000008a44c55d013d7d3531b0881f244d1f353c208fd00cb18bd152a054460aa4eed815d69ab241000000006a473044022025c0ea702390c702c7ae8b5ea469820bea8d942c8c16439f8f0ba2e91e699efc02200db9b0a48fa2861695fa91df4831a4c7306587e5d2dc85419647f462717bc8f001210274cb0ee652d9457fbb0f3872d43155a6bc16f77bd5749d8826b53db443b1b278ffffffff01905f0100000000001976a914ff9a05654150fdc92b1655f49d7f2a8aaf6a3a2a88ac00000000"
    assert timestamp_tx.hex() == accepted_txhex


@pytest.mark.altcoin
@pytest.mark.peercoin
@pytest.mark.skip_ui
def test_timestamp_missing(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44'/6'/0'/0/0"),
        amount=100000,
        prev_hash=TXHASH_41b29a,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="PXtfyTjzgXSgTwK5AbszdHQSSxyQN3BLM5",
        amount=100000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    details = messages.SignTx(version=1, timestamp=None)
    with pytest.raises(TrezorFailure, match="Timestamp must be set."):
        btc.sign_tx(
            client, "Peercoin", [inp1], [out1], details=details, prev_txes=TX_CACHE,
        )

    details = messages.SignTx(version=1, timestamp=0)
    with pytest.raises(TrezorFailure, match="Timestamp must be set."):
        btc.sign_tx(
            client, "Peercoin", [inp1], [out1], details=details, prev_txes=TX_CACHE,
        )


@pytest.mark.altcoin
@pytest.mark.peercoin
@pytest.mark.skip_ui
def test_timestamp_missing_prevtx(client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44'/6'/0'/0/0"),
        amount=100000,
        prev_hash=TXHASH_41b29a,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="PXtfyTjzgXSgTwK5AbszdHQSSxyQN3BLM5",
        amount=100000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    details = messages.SignTx(version=1, timestamp=0x5DC5448A)

    prevtx = TX_CACHE[TXHASH_41b29a]
    prevtx.timestamp = 0

    with pytest.raises(TrezorFailure, match="Timestamp must be set."):
        btc.sign_tx(
            client,
            "Peercoin",
            [inp1],
            [out1],
            details=details,
            prev_txes={TXHASH_41b29a: prevtx},
        )

    prevtx.timestamp = None
    with pytest.raises(TrezorFailure, match="Timestamp must be set."):
        btc.sign_tx(
            client,
            "Peercoin",
            [inp1],
            [out1],
            details=details,
            prev_txes={TXHASH_41b29a: prevtx},
        )
