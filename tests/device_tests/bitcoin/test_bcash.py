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
from trezorlib.tools import H_, parse_path

from ...tx_cache import TxCache
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API = TxCache("Bcash")

TXHASH_bc37c2 = bytes.fromhex(
    "bc37c28dfb467d2ecb50261387bf752a3977d7e5337915071bb4151e6b711a78"
)
FAKE_TXHASH_bd32ff = bytes.fromhex(
    "bd32ff85c3827fc2de6150548fb79d3e6826e353f08c68dda396b3321f2b1092"
)
TXHASH_502e85 = bytes.fromhex(
    "502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c"
)
FAKE_TXHASH_062fbd = bytes.fromhex(
    "062fbdf491a60db4daf48148899e390bc48ae5153ab465078693ec781a1a685d"
)
FAKE_TXHASH_203416 = bytes.fromhex(
    "203416cda0f2f7f0b4d666c6160190126edb07236394e927bf605821866f2a71"
)

pytestmark = pytest.mark.altcoin


def test_send_bch_change(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/0h/0/0"),
        # bitcoincash:qr08q88p9etk89wgv05nwlrkm4l0urz4cyl36hh9sv
        amount=1_995_344,
        prev_hash=TXHASH_bc37c2,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/145h/0h/1/0"),
        amount=1_896_050,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4",
        amount=73_452,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_bc37c2),
                request_input(0, TXHASH_bc37c2),
                request_output(0, TXHASH_bc37c2),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bcash", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://bch1.trezor.io/api/tx/502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c",
        tx_hex="0100000001781a716b1e15b41b07157933e5d777392a75bf87132650cb2e7d46fb8dc237bc000000006a473044022061aee4f17abe044d5df8c52c9ffd3b84e5a29743517e488b20ecf1ae0b3e4d3a02206bb84c55e407f3b684ff8d9bea0a3409cfd865795a19d10b3d3c31f12795c34a412103a020b36130021a0f037c1d1a02042e325c0cb666d6478c1afdcd9d913b9ef080ffffffff0272ee1c00000000001976a914b1401fce7e8bf123c88a0467e0ed11e3b9fbef5488acec1e0100000000001976a914d51eca49695cdf47e7f4b55507893e3ad53fe9d888ac00000000",
    )


def test_send_bch_nochange(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/0h/1/0"),
        # bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw
        amount=1_896_050,
        prev_hash=TXHASH_502e85,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/0h/0/1"),
        # bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4
        amount=73_452,
        prev_hash=TXHASH_502e85,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address="bitcoincash:qq6wnnkrz7ykaqvxrx4hmjvayvzjzml54uyk76arx4",
        amount=1_934_960,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_502e85),
                request_input(0, TXHASH_502e85),
                request_output(0, TXHASH_502e85),
                request_output(1, TXHASH_502e85),
                request_input(1),
                request_meta(TXHASH_502e85),
                request_input(0, TXHASH_502e85),
                request_output(0, TXHASH_502e85),
                request_output(1, TXHASH_502e85),
                request_input(0),
                request_input(1),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bcash", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://bch1.trezor.io/api/tx/5594fd9e5e26dcb4437cbbbba517401720849159bac4e2158e1e6401ffd5fdb7",
        tx_hex="01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000",
    )


def test_send_bch_oldaddr(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/0h/1/0"),
        # bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw
        amount=1_896_050,
        prev_hash=TXHASH_502e85,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/0h/0/1"),
        # bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4
        amount=73_452,
        prev_hash=TXHASH_502e85,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address="15pnEDZJo3ycPUamqP3tEDnEju1oW5fBCz",
        amount=1_934_960,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_502e85),
                request_input(0, TXHASH_502e85),
                request_output(0, TXHASH_502e85),
                request_output(1, TXHASH_502e85),
                request_input(1),
                request_meta(TXHASH_502e85),
                request_input(0, TXHASH_502e85),
                request_output(0, TXHASH_502e85),
                request_output(1, TXHASH_502e85),
                request_input(0),
                request_input(1),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bcash", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://bch1.trezor.io/api/tx/5594fd9e5e26dcb4437cbbbba517401720849159bac4e2158e1e6401ffd5fdb7",
        tx_hex="01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000",
    )


def test_attack_change_input(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/10h/0/0"),
        amount=1_995_344,
        prev_hash=FAKE_TXHASH_bd32ff,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/145h/10h/1/0"),
        amount=1_896_050,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4",
        amount=73_452,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    attack_count = 2

    def attack_processor(msg):
        nonlocal attack_count

        if msg.tx.inputs and msg.tx.inputs[0] == inp1:
            if attack_count > 0:
                attack_count -= 1
            else:
                msg.tx.inputs[0].address_n[2] = H_(1)

        return msg

    with client:
        is_core = client.features.model in ("T", "R")
        client.set_filter(messages.TxAck, attack_processor)
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_bd32ff),
                request_input(0, FAKE_TXHASH_bd32ff),
                request_output(0, FAKE_TXHASH_bd32ff),
                request_input(0),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(TrezorFailure):
            btc.sign_tx(client, "Bcash", [inp1], [out1, out2], prev_txes=TX_API)


@pytest.mark.multisig
def test_send_bch_multisig_wrongchange(client: Client):
    # NOTE: fake input tx used

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/48h/145h/{i}h/0h"), coin_name="Bcash"
        ).node
        for i in range(1, 4)
    ]

    def getmultisig(chain, nr, signatures):
        return messages.MultisigRedeemScriptType(
            nodes=nodes, address_n=[chain, nr], signatures=signatures, m=2
        )

    correcthorse = messages.HDNodeType(
        depth=1,
        fingerprint=0,
        child_num=0,
        chain_code=bytes.fromhex(
            "0000000000000000000000000000000000000000000000000000000000000000"
        ),
        public_key=bytes.fromhex(
            "0378d430274f8c5ec1321338151e9f27f4c676a008bdf8638d07c0b6be9ab35c71"
        ),
    )
    sig = bytes.fromhex(
        "304402207274b5a4d15e75f3df7319a375557b0efba9b27bc63f9f183a17da95a6125c94022000efac57629f1522e2d3958430e2ef073b0706cfac06cce492651b79858f09ae"
    )
    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/145h/1h/0h/1/0"),
        multisig=getmultisig(1, 0, [b"", sig, b""]),
        # bitcoincash:pp6kcpkhua7789g2vyj0qfkcux3yvje7euhyhltn0a
        amount=24_000,
        prev_hash=FAKE_TXHASH_062fbd,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDMULTISIG,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/48h/145h/1h/0h/1/1"),
        multisig=messages.MultisigRedeemScriptType(
            pubkeys=[
                messages.HDNodePathType(node=nodes[0], address_n=[1, 1]),
                messages.HDNodePathType(node=correcthorse, address_n=[]),
                messages.HDNodePathType(node=correcthorse, address_n=[]),
            ],
            signatures=[b"", b"", b""],
            m=2,
        ),
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
        amount=23_000,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_062fbd),
                request_input(0, FAKE_TXHASH_062fbd),
                request_output(0, FAKE_TXHASH_062fbd),
                request_output(1, FAKE_TXHASH_062fbd),
                request_input(0),
                request_output(0),
                request_finished(),
            ]
        )
        (signatures1, serialized_tx) = btc.sign_tx(
            client, "Bcash", [inp1], [out1], prev_txes=TX_API
        )
    assert (
        signatures1[0].hex()
        == "3044022044d6faf6cca46c368a24220079863e5fb608192eb33e0726d8f529980465122302202903f91c1cc32dee5530f1fc5b88aad2563b44ba74471fd4903b974124db25da"
    )
    assert (
        serialized_tx.hex()
        == "01000000015d681a1a78ec93860765b43a15e58ac40b399e894881f4dab40da691f4bd2f0601000000fc00473044022044d6faf6cca46c368a24220079863e5fb608192eb33e0726d8f529980465122302202903f91c1cc32dee5530f1fc5b88aad2563b44ba74471fd4903b974124db25da4147304402207274b5a4d15e75f3df7319a375557b0efba9b27bc63f9f183a17da95a6125c94022000efac57629f1522e2d3958430e2ef073b0706cfac06cce492651b79858f09ae414c69522102962724052105f03332ab700812afc5ca665d264b13339be1fe7f7fdd3a2a685821024364cd1fdc2aa05bc8b09874a57aa1082a47ac9062d35f22ed5f4afefb3f67fc21024d375b44804f3b0c3493ea0806eb25cc85f51e0d616d6bd6e4ef0388e71cd29e53aeffffffff01d85900000000000017a9140d5566bfc721e6c3d5ab583841d387f3939ffed38700000000"
    )


@pytest.mark.multisig
def test_send_bch_multisig_change(client: Client):
    # NOTE: fake input tx used

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/48h/145h/{i}h/0h"), coin_name="Bcash"
        ).node
        for i in range(1, 4)
    ]

    EMPTY_SIGNATURES = [b"", b"", b""]

    def getmultisig(chain, nr, signatures):
        return messages.MultisigRedeemScriptType(
            nodes=nodes, address_n=[chain, nr], signatures=signatures, m=2
        )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/145h/3h/0h/0/0"),
        multisig=getmultisig(0, 0, EMPTY_SIGNATURES),
        amount=48_490,
        prev_hash=FAKE_TXHASH_203416,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
    )
    out1 = messages.TxOutputType(
        address="bitcoincash:qqq8gx2j76nw4dfefumxmdwvtf2tpsjznusgsmzex9",
        amount=24_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/48h/145h/3h/0h/1/0"),
        multisig=getmultisig(1, 0, EMPTY_SIGNATURES),
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
        amount=24_000,
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
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_203416),
                request_input(0, FAKE_TXHASH_203416),
                request_output(0, FAKE_TXHASH_203416),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        (signatures1, serialized_tx) = btc.sign_tx(
            client, "Bcash", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        signatures1[0].hex()
        == "3045022100fc790bc8d069cafb6422e937fb922cc15cca0c32919402e415c03ce0208dab6a02205d218b33c6e0a990e0f78646b4b75c67c8de05a7cc42a9c892d748b94ea25112"
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/145h/1h/0h/0/0"),
        multisig=getmultisig(0, 0, [b"", b"", signatures1[0]]),
        # bitcoincash:pqguz4nqq64jhr5v3kvpq4dsjrkda75hwy86gq0qzw
        amount=48_490,
        prev_hash=FAKE_TXHASH_203416,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
    )
    out2.address_n[2] = H_(1)

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_203416),
                request_input(0, FAKE_TXHASH_203416),
                request_output(0, FAKE_TXHASH_203416),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        (signatures1, serialized_tx) = btc.sign_tx(
            client, "Bcash", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        signatures1[0].hex()
        == "3045022100bf3f7b31f1e6c063cebf2651edde5ae4bc1d65cc815aaa83bc60a035b2b0391802206cd098f23bf66f10ce23bd3596f05cf3a71da891d7abfe89d777c14ee2856601"
    )
    assert (
        serialized_tx.hex()
        == "0100000001712a6f86215860bf27e994632307db6e12900116c666d6b4f0f7f2a0cd16342000000000fdfe0000483045022100bf3f7b31f1e6c063cebf2651edde5ae4bc1d65cc815aaa83bc60a035b2b0391802206cd098f23bf66f10ce23bd3596f05cf3a71da891d7abfe89d777c14ee285660141483045022100fc790bc8d069cafb6422e937fb922cc15cca0c32919402e415c03ce0208dab6a02205d218b33c6e0a990e0f78646b4b75c67c8de05a7cc42a9c892d748b94ea25112414c6952210290cc724ccb90a6c7c1c3b291938449464ea474390183909e51bcd2807ecb779d210222f537684e2933563f737192fbf1947fd9034402e5708d10f6decd8e1f03e172210350df5cb41013d6b06581230556006b0a85ccccd205745cc10c927755193c241b53aeffffffff02c05d0000000000001976a91400741952f6a6eab5394f366db5cc5a54b0c2429f88acc05d00000000000017a914dfc8c2dda26f7151ed7df8aeeca24089e6410fdd8700000000"
    )


@pytest.mark.skip_t1
def test_send_bch_external_presigned(client: Client):
    inp1 = messages.TxInputType(
        # address_n=parse_path("44'/145'/0'/1/0"),
        # bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw
        amount=1_896_050,
        prev_hash=TXHASH_502e85,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a914b1401fce7e8bf123c88a0467e0ed11e3b9fbef5488ac"
        ),
        script_sig=bytes.fromhex(
            "47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2d"
        ),
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/145h/0h/0/1"),
        # bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4
        amount=73_452,
        prev_hash=TXHASH_502e85,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address="bitcoincash:qq6wnnkrz7ykaqvxrx4hmjvayvzjzml54uyk76arx4",
        amount=1_934_960,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    with client:
        is_core = client.features.model in ("T", "R")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_502e85),
                request_input(0, TXHASH_502e85),
                request_output(0, TXHASH_502e85),
                request_output(1, TXHASH_502e85),
                request_input(1),
                request_meta(TXHASH_502e85),
                request_input(0, TXHASH_502e85),
                request_output(0, TXHASH_502e85),
                request_output(1, TXHASH_502e85),
                request_input(0),
                request_input(1),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bcash", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://bch1.trezor.io/api/tx/5594fd9e5e26dcb4437cbbbba517401720849159bac4e2158e1e6401ffd5fdb7",
        tx_hex="01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000",
    )
