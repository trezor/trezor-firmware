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
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

TXHASH_33043a = bytes.fromhex(
    "33043a28cfa924ca701983e628615559ed2b68c0c14eb706b3970fa8dd4b5209"
)

pytestmark = pytest.mark.altcoin


def test_send_p2tr(session: Session):
    inp1 = messages.TxInputType(
        # fc1prr07akly3xjtmggue0p04vghr8pdcgxrye2s00sahptwjeawxrkq2rxzr7
        address_n=parse_path("m/86h/75h/0h/0/1"),
        amount=99_997_780_000,
        prev_hash=TXHASH_33043a,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        # 86'/75'/0'/0/0
        address="fc1pxax0eaemn9fg2vfwvnz8wr2fjtr5e8junp50vx3yvx8aauv0hcvql824ml",
        amount=99_996_670_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(session, "Fujicoin", [inp1], [out1])
    # Transaction hex changed with fix #2085, all other details are the same as this tx:
    # https://explorer.fujicoin.org/tx/a1c6a81f5e8023b17e6e3e51e2596d5b5e1d4914ea13c0c31cef90b3c3edee86
    assert (
        serialized_tx.hex()
        == "0100000000010109524bdda80f97b306b74ec1c0682bed59556128e6831970ca24a9cf283a04330000000000ffffffff013018444817000000225120374cfcf73b995285312e64c4770d4992c74c9e5c9868f61a24618fdef18fbe1801409879ad5bd2488b5707e0632d4d6e788c3cff91d79233e10c22c2d7925a8f96f6753c5a8bc4efc107075408786fc1fb82c4064bcb60c65a1fa8ec92ef90d6548c00000000"
    )
