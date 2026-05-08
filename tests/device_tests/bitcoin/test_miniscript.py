# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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
from trezorlib.debuglink import DebugSession as Session
from trezorlib.tools import H_, parse_path

from ...bip32 import deserialize
from ...common import is_core
from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

TPUBS = [
    "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
    "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
]

pytestmark = [pytest.mark.miniscript]

DATA = [
    (0, 0, "tb1qwr00r4x9a2ycm7fn48c7kqm6kpsp56ydwx482ns5c3wxmrwqwu2stjh6cc"),
    (0, 1, "tb1qzvr7ptes6kq2ee0745a7h2n639etfz43nsz9d2jn8u6wz8egx0hqnr5pza"),
    (0, 2, "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"),
    (0, 3, "tb1qc6zh83pdaj64tkmvu5969falc95s7sgs6yku5nh9asspzfmtq8cq7yxr2a"),
    (1, 0, "tb1q5f45hdwm06sf9wa20pcwa5rr9xn99m4yfpzdg406044nl9jhadps2ghwl5"),
    (1, 1, "tb1qk47jne78xqrzxwj5wc8l3qypneh96jumw56lkp50akhqpw5jmr6qwxdctf"),
    (1, 2, "tb1q68hg7scyjs20dndpdl7crr3kue0g8a5pkvktwlnwk4ygheazyfzqnhy9gm"),
]

VECTORS = (  # coin, path, script_type, address
    pytest.param(
        "Testnet",
        "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(1))))".format(*TPUBS),
        [change, index],
        address,
        id=f'Liana-{"internal" if change else "external"}-{index}',
    )
    for change, index, address in DATA
)


@pytest.mark.parametrize("coin, miniscript, n, address", VECTORS)
def test_miniscript_get_address(
    session: Session,
    coin: str,
    miniscript: str,
    n: list[int],
    address: str,
):
    assert (
        btc.get_address(
            session,
            coin,
            n=n,
            miniscript=miniscript,
        )
        == address
    )

TX_CACHE_SIGNET = TxCache("Signet")

def test_miniscript_spend(session: Session):
    TPUBS = [
        # ALL x 12 [5c9e228d/84'/1'/0']
        "tpubDCZB6sR48s4T5Cr8qHUYSZEFCQMMHRg8AoVKVmvcAP5bRw7ArDKeoNwKAJujV3xCPkBvXH5ejSgbgyN6kREmF7sMd41NdbuHa8n1DZNxSMg",
        # GYM x 12 [72758bc3/84'/1'/0']
        "tpubDCNhwLKYSSu2FKssoMziAdwhAAKS3bASH7wZYkNmJ7sU5hW9LgDaAQPqe7ivAkskSF29B1CkRRg4g2mbovXgAL9Mby6i9xBdhZh2txDeSLb",
    ]

    # 1st always, or 2nd after 1 block
    DESC = "wsh(or_d(pk({0}/<0;1>/*),and_v(v:pkh({1}/<0;1>/*),older(1))))".format(*TPUBS)
    COIN = "Testnet"

    assert btc.get_public_node(session, parse_path(f"m/84h/1h/0h"), coin_name=COIN).xpub == TPUBS[0]
    assert btc.get_address(session, n=[0, 2], miniscript=DESC, coin_name=COIN) == "tb1qerjma9tcyn6qh5yt7wdqqm3q8sz7ft6dn7pratjclzc8pha27rcsgjn0sp"

    TXHASH_5694f1 = bytes.fromhex("5694f194cb1389ab66c066397534b8ad1cd635c4c1effe26088491d3c8500949")

    inp1 = messages.TxInputType(
        address_n=parse_path("m/84h/1h/0h/0/2"),
        prev_hash=TXHASH_5694f1,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMINISCRIPT,
        miniscript=DESC,
        amount=10_000,
    )

    out1 = messages.TxOutputType(
        address="tb1ql8qjvr3f6yjjpdlmtuwvjnznad8rx7fkcgwvgg",
        amount=10_000 - 1_000,
        script_type=messages.OutputScriptType.PAYTOWITNESS,
    )

    signatures, serialized = btc.sign_tx(
        session, "Testnet", [inp1], [out1], prev_txes=TX_CACHE_SIGNET
    )

    assert signatures[0].hex() == "3045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca"

    assert serialized.hex() == "01000000000101490950c8d391840826feefc1c435d61cadb834753966c066ab8913cb94f194560100000000ffffffff012823000000000000160014f9c1260e29d12520b7fb5f1cc94c53eb4e33793602483045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca01210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e9300000000"

# 01000000000101490950c8d391840826feefc1c435d61cadb834753966c066ab8913cb94f194560100000000ffffffff012823000000000000160014f9c1260e29d12520b7fb5f1cc94c53eb4e33793602483045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca01210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e9300000000

##
#0x02483045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca01210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e9300000000,

# 0357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e93 OP_CHECKSIG OP_IFDUP OP_NOTIF OP_DUP OP_HASH160 ebf9ce6f9053f23c2e4053576914d9e238ef9f05 OP_EQUALVERIFY OP_CHECKSIGVERIFY OP_PUSHNUM_1 OP_CSV OP_ENDIF
# 21 0357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e93ac736476a914ebf9ce6f9053f23c2e4053576914d9e238ef9f0588ad51b268

#  build/bin/bitcoin-cli -signet decoderawtransaction 01000000000101490950c8d391840826feefc1c435d61cadb834753966c066ab8913cb94f194560100000000ffffffff012823000000000000160014f9c1260e29d12520b7fb5f1cc94c53eb4e33793602483045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca01210357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e9300000000
# {
#   "txid": "f359d5889cdce6aae9ca65d838d30250f3435cf697fb9393a8fe92597f67aad8",
#   "hash": "77a874d19b02b63bf3a995dd0049459615ebfab70f8636b86966cbd4e50a0dca",
#   "version": 1,
#   "size": 192,
#   "vsize": 110,
#   "weight": 438,
#   "locktime": 0,
#   "vin": [
#     {
#       "txid": "5694f194cb1389ab66c066397534b8ad1cd635c4c1effe26088491d3c8500949",
#       "vout": 1,
#       "scriptSig": {
#         "asm": "",
#         "hex": ""
#       },
#       "txinwitness": [
#         "3045022100e97a3e8284019dcc8eb91cd0bdf8df03dabc1dc55af9af1de4e01b7b7bdc793302204946f21cd7d3d47c5f4f543ce4936187c53eeafc113a2f1cfa72abd0509670ca01",
#         "0357cb3a5918d15d224f14a89f0eb54478272108f6cbb9c473c1565e55260f6e93"
#       ],
#       "sequence": 4294967295
#     }
#   ],
#   "vout": [
#     {
#       "value": 0.00009000,
#       "n": 0,
#       "scriptPubKey": {
#         "asm": "0 f9c1260e29d12520b7fb5f1cc94c53eb4e337936",
#         "desc": "addr(tb1ql8qjvr3f6yjjpdlmtuwvjnznad8rx7fkcgwvgg)#nuum2z22",
#         "hex": "0014f9c1260e29d12520b7fb5f1cc94c53eb4e337936",
#         "address": "tb1ql8qjvr3f6yjjpdlmtuwvjnznad8rx7fkcgwvgg",
#         "type": "witness_v0_keyhash"
#       }
#     }
#   ]
# }
