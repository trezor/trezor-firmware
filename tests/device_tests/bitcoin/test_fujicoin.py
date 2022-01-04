# This file is part of the Trezor project.
#
# Copyright (C) 2012-2021 SatoshiLabs and contributors
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
TX_API = TxCache("Fujicoin")

TXHASH_33043a = bytes.fromhex(
    "33043a28cfa924ca701983e628615559ed2b68c0c14eb706b3970fa8dd4b5209"
)

pytestmark = pytest.mark.altcoin


def test_send_p2tr(client):
    inp1 = messages.TxInputType(
        # fc1prr07akly3xjtmggue0p04vghr8pdcgxrye2s00sahptwjeawxrkq2rxzr7
        address_n=parse_path("86'/75'/0'/0/1"),
        amount=99997780000,
        prev_hash=TXHASH_33043a,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        # 86'/75'/0'/0/0
        address="fc1pxax0eaemn9fg2vfwvnz8wr2fjtr5e8junp50vx3yvx8aauv0hcvql824ml",
        amount=99996670000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Fujicoin", [inp1], [out1], prev_txes=TX_API
    )
    # https://explorer.fujicoin.org/tx/a1c6a81f5e8023b17e6e3e51e2596d5b5e1d4914ea13c0c31cef90b3c3edee86
    assert (
        serialized_tx.hex()
        == "0100000000010109524bdda80f97b306b74ec1c0682bed59556128e6831970ca24a9cf283a04330000000000ffffffff013018444817000000225120374cfcf73b995285312e64c4770d4992c74c9e5c9868f61a24618fdef18fbe180140310d04b3f7ec9c6bbc334254b5cb160d071368b3718a1e69a9f9c8c32634046cafc156115c223520eb061e5004e3f682973ed1c441b4cb9581a3ac08540227ee00000000"
    )
