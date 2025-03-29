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

from trezorlib import btc, messages
from trezorlib.debuglink import SessionDebugWrapper as Session
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import assert_tx_matches

TX_API = TxCache("Testnet")

TXHASH_357728 = bytes.fromhex(
    "3577280f334f5d0ffcf994c2e346d307046dec4ba2aaa9ababb7b96c54b27cc1"
)
TXHASH_7afc31 = bytes.fromhex(
    "7afc31334c88840b295eedba9bffce93ba142577867cdde199fec03545e49eb9"
)
TXHASH_cf52d7 = bytes.fromhex(
    "cf52d7ece8f614a70e0da43eaf9fa1bb9e7ebdd14feca3278d8899071ac44948"
)


def test_non_segwit_segwit_inputs(session: Session):
    # First is non-segwit, second is segwit.

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/7"),  # mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG
        amount=10_000,
        prev_hash=TXHASH_cf52d7,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    inp2 = messages.TxInputType(
        # tb1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt96jk9x
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=10_000,
        prev_hash=TXHASH_7afc31,
        prev_index=4,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=10_000 + 10_000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session.client:
        signatures, serialized_tx = btc.sign_tx(
            session, "Testnet", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 2
    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/e4b3150748dfaad0df9b55aadf13a231a0c84baf0f5be56a704375c0ee5f873b",
        tx_hex="010000000001024849c41a0799888d27a3ec4fd1bd7e9ebba19faf3ea40d0ea714f6e8ecd752cf000000006a473044022003ecf52d057d7a1d16b246fa13aa5bac893cf3cd46dc7fb832d1dc5e68279c4802201026004b05c0774ddb552968f4394cf144272fa387fd728e0b7a4e7d7be131200121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffffb99ee44535c0fe99e1dd7c86772514ba93ceff9bbaed5e290b84884c3331fc7a0400000000ffffffff01384a000000000000160014a579388225827d9f2fe9014add644487808c695d00024830450221009d5c89cc9d0e878583564f10f4ce1400a3239096581474be05e703c098cfadad02201ad115ce2ce6dea9c2df4bbba95385fd5f687673089a6ceeba5daea473f65d5d012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f00000000",
    )


def test_segwit_non_segwit_inputs(session: Session):
    # First is segwit, second is non-segwit.

    inp1 = messages.TxInputType(
        # tb1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt96jk9x
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=10_000,
        prev_hash=TXHASH_7afc31,
        prev_index=1,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/7"),  # mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG
        amount=10_000,
        prev_hash=TXHASH_cf52d7,
        prev_index=1,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=10_000 + 10_000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session.client:
        signatures, serialized_tx = btc.sign_tx(
            session, "Testnet", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 2
    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/15611ef30e38a23620462ef0199003c3cbc5902216b0150420fb63ec094e8fe7",
        tx_hex="01000000000102b99ee44535c0fe99e1dd7c86772514ba93ceff9bbaed5e290b84884c3331fc7a0100000000ffffffff4849c41a0799888d27a3ec4fd1bd7e9ebba19faf3ea40d0ea714f6e8ecd752cf010000006a47304402204aa76f35f07621bb336b9cd91808b47a4a55aaa1e9841077ba5397e50c0024e502200256916e8a2a3792745089817953b163a8b8a7af10264ea5f9250ce0b8b327640121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffff01384a000000000000160014a579388225827d9f2fe9014add644487808c695d0247304402206b927741e6616ddf78e47b28f321aaecfc0b72c9a0a1e479d89d2af690e7277a02207f95a427c56ba79ed3974697fdc0b3a91a60cb455ad70ba58ac8061585ed5fb5012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f0000000000",
    )


def test_segwit_non_segwit_segwit_inputs(session: Session):
    # First is segwit, second is non-segwit and third is segwit again.

    inp1 = messages.TxInputType(
        # tb1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt96jk9x
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=10_000,
        prev_hash=TXHASH_7afc31,
        prev_index=2,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/7"),  # mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG
        amount=10_000,
        prev_hash=TXHASH_cf52d7,
        prev_index=2,
    )
    inp3 = messages.TxInputType(
        # tb1qkvwu9g3k2pdxewfqr7syz89r3gj557l3uuf9r9
        address_n=parse_path("m/84h/1h/0h/0/0"),
        amount=10_000,
        prev_hash=TXHASH_7afc31,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=10_000 + 10_000 + 10_000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session.client:
        signatures, serialized_tx = btc.sign_tx(
            session, "Testnet", [inp1, inp2, inp3], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 3
    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/5ff5ddaa28241353a714bbcc57ce86a6cf1caf31d33948c62da2f55dadb2533b",
        tx_hex="01000000000103b99ee44535c0fe99e1dd7c86772514ba93ceff9bbaed5e290b84884c3331fc7a0200000000ffffffff4849c41a0799888d27a3ec4fd1bd7e9ebba19faf3ea40d0ea714f6e8ecd752cf020000006b483045022100d2610b791fcf72f2d2780781948e5129dcfaa738f92441c38102758cdea880fe02205b4314e1afd0270e93498c5a410a379f86a4b9b1ed47d9909284c31e10c380000121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffffb99ee44535c0fe99e1dd7c86772514ba93ceff9bbaed5e290b84884c3331fc7a0000000000ffffffff014871000000000000160014a579388225827d9f2fe9014add644487808c695d0248304502210082abb0696513b4a6582ad673ea99898fc3564ccb310bf5b6f32b338a54e6c481022009cb1404626fe381ed20ade6f0b3c367856584cc5da030360807a7a15f364816012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f0002483045022100f886bc7abfdd12e5c0b27e61075bd9c5e1f2aaa9b87623024732217e7d482c2402205ae8ad88872d655593c205333075989841623e0a7a3b3062e7fcd18afa69868a012103adc58245cf28406af0ef5cc24b8afba7f1be6c72f279b642d85c48798685f86200000000",
    )


def test_non_segwit_segwit_non_segwit_inputs(session: Session):
    # First is non-segwit, second is segwit and third is non-segwit again.

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/7"),  # mgV9Z3YuSbxGb2b2Y1T6VCqtU2osui7vhG
        amount=10_000,
        prev_hash=TXHASH_cf52d7,
        prev_index=3,
    )
    inp2 = messages.TxInputType(
        # tb1qejqxwzfld7zr6mf7ygqy5s5se5xq7vmt96jk9x
        address_n=parse_path("m/84h/1h/0h/1/0"),
        amount=10_000,
        prev_hash=TXHASH_7afc31,
        prev_index=3,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp3 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/1h/0/0"),  # msUqRgCWS7ryuFcF34EaKTrsTe3xHra128
        amount=10_000,
        prev_hash=TXHASH_357728,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="tb1q54un3q39sf7e7tlfq99d6ezys7qgc62a6rxllc",
        amount=10_000 + 10_000 + 10_000 - 1000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with session.client:
        signatures, serialized_tx = btc.sign_tx(
            session, "Testnet", [inp1, inp2, inp3], [out1], prev_txes=TX_API
        )

    assert len(signatures) == 3
    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/af4b1333244958e380cdd50f8fbb11530bc80208ddb8e8d5b35ebd51c0f486be",
        tx_hex="010000000001034849c41a0799888d27a3ec4fd1bd7e9ebba19faf3ea40d0ea714f6e8ecd752cf030000006b48304502210082d5f5568a131bfbc19757a28916c645b7eeb0943f8fec2ca3a0083019f87526022057cb783bf3d57103a352d0cfeed4fa4a400785d03684c03a3a1475dc70829e450121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffffb99ee44535c0fe99e1dd7c86772514ba93ceff9bbaed5e290b84884c3331fc7a0300000000ffffffffc17cb2546cb9b7ababa9aaa24bec6d0407d346e3c294f9fc0f5d4f330f287735000000006a47304402207b65dc4bafca0195cdbac0f29cd59a9c30811b7a9f668285a2f28a5aed3f222302204dfc3338fbe68ade24a4eed5c9fbafd1a75f2ccb722d5834851425103b111759012103bae960983f83e28fcb8f0e5f3dc1f1297b9f9636612fd0835b768e1b7275fb9dffffffff014871000000000000160014a579388225827d9f2fe9014add644487808c695d000247304402204ec4c1b7a0f7b98571d294fdf2ed0312eeff8ee01869d2b49b683bc61092cca70220381c11cff198611f2986e52fc697f570be255a0194117aef110f73b8e265d44c012103505647c017ff2156eb6da20fae72173d3b681a1d0a629f95f49e884db300689f0000000000",
    )
