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

TXHASH_e95b91 = bytes.fromhex(
    "e95b91410a42cce8c4c3348c05835a4e01b1a83c4259b630096bcde6c9bb3198"
)

pytestmark = pytest.mark.altcoin


def test_send_p2tr(client):
    inp1 = messages.TxInputType(
        # fc1pzfqhhmyve3gjxkm4ga5p5f0ueclspn2x2y3cpafra5hp0kna0f5s8na3n9
        address_n=parse_path("86'/75'/0'/0/1"),
        amount=100000000000,
        prev_hash=TXHASH_e95b91,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )
    out1 = messages.TxOutputType(
        # 86'/75'/0'/0/0
        address="fc1plf6fmfsrx086qpzjcvn6w29ms2d08rjknphye8phdtqcn0vk9mzswzaz59",
        amount=99998890000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    _, serialized_tx = btc.sign_tx(
        client, "Fujicoin", [inp1], [out1], prev_txes=TX_API
    )
    # https://explorer.fujicoin.org/tx/46b799bfa25d5771b3f894745934240ee9f4a17d139c4182e6287252c4cca15b
    assert (
        serialized_tx.hex()
        == "010000000001019831bbc9e6cd6b0930b659423ca8b1014e5a83058c34c3c4e8cc420a41915be90100000000ffffffff0110f8654817000000225120fa749da60333cfa00452c327a728bb829af38e56986e4c9c376ac189bd962ec50140f3846661a78423ba5bdbc874b8d75594fa5a15aab07627a95faae4cabdacc82cc271a90c7ab215e61f30dca1245f601f4a9e1184725e72223cca43a8c66f6db800000000"
    )
