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

from trezorlib import btc, messages as proto
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path

from ..tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = proto.ButtonRequestType
TX_API = TxCache("Bcash")

TXHASH_bc37c2 = bytes.fromhex(
    "bc37c28dfb467d2ecb50261387bf752a3977d7e5337915071bb4151e6b711a78"
)
TXHASH_502e85 = bytes.fromhex(
    "502e8577b237b0152843a416f8f1ab0c63321b1be7a8cad7bf5c5c216fcf062c"
)
TXHASH_f68caf = bytes.fromhex(
    "f68caf10df12d5b07a34601d88fa6856c6edcbf4d05ebef3486510ae1c293d5f"
)
TXHASH_8b6db9 = bytes.fromhex(
    "8b6db9b8ba24235d86b053ea2ccb484fc32b96f89c3c39f98d86f90db16076a0"
)


@pytest.mark.altcoin
class TestMsgSigntxBch:
    def test_send_bch_change(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/145'/0'/0/0"),
            # bitcoincash:qr08q88p9etk89wgv05nwlrkm4l0urz4cyl36hh9sv
            amount=1995344,
            prev_hash=TXHASH_bc37c2,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/145'/0'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4",
            amount=73452,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
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

        assert (
            serialized_tx.hex()
            == "0100000001781a716b1e15b41b07157933e5d777392a75bf87132650cb2e7d46fb8dc237bc000000006a473044022061aee4f17abe044d5df8c52c9ffd3b84e5a29743517e488b20ecf1ae0b3e4d3a02206bb84c55e407f3b684ff8d9bea0a3409cfd865795a19d10b3d3c31f12795c34a412103a020b36130021a0f037c1d1a02042e325c0cb666d6478c1afdcd9d913b9ef080ffffffff0272ee1c00000000001976a914b1401fce7e8bf123c88a0467e0ed11e3b9fbef5488acec1e0100000000001976a914d51eca49695cdf47e7f4b55507893e3ad53fe9d888ac00000000"
        )

    def test_send_bch_nochange(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/145'/0'/1/0"),
            # bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw
            amount=1896050,
            prev_hash=TXHASH_502e85,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=parse_path("44'/145'/0'/0/1"),
            # bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4
            amount=73452,
            prev_hash=TXHASH_502e85,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="bitcoincash:qq6wnnkrz7ykaqvxrx4hmjvayvzjzml54uyk76arx4",
            amount=1934960,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
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

        assert (
            serialized_tx.hex()
            == "01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000"
        )

    def test_send_bch_oldaddr(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/145'/0'/1/0"),
            # bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw
            amount=1896050,
            prev_hash=TXHASH_502e85,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        inp2 = proto.TxInputType(
            address_n=parse_path("44'/145'/0'/0/1"),
            # bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4
            amount=73452,
            prev_hash=TXHASH_502e85,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="15pnEDZJo3ycPUamqP3tEDnEju1oW5fBCz",
            amount=1934960,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
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

        assert (
            serialized_tx.hex()
            == "01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000"
        )

    def test_attack_change_input(self, client):
        inp1 = proto.TxInputType(
            address_n=parse_path("44'/145'/10'/0/0"),
            amount=1995344,
            prev_hash=TXHASH_bc37c2,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("44'/145'/10'/1/0"),
            amount=1896050,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address="bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4",
            amount=73452,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
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

        client.set_filter(proto.TxAck, attack_processor)

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    request_output(1),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_bc37c2),
                    request_input(0, TXHASH_bc37c2),
                    request_output(0, TXHASH_bc37c2),
                    request_input(0),
                    proto.Failure(code=proto.FailureType.ProcessError),
                ]
            )
            with pytest.raises(TrezorFailure):
                btc.sign_tx(client, "Bcash", [inp1], [out1, out2], prev_txes=TX_API)

    @pytest.mark.multisig
    def test_send_bch_multisig_wrongchange(self, client):
        nodes = [
            btc.get_public_node(
                client, parse_path(f"48'/145'/{i}'"), coin_name="Bcash"
            ).node
            for i in range(1, 4)
        ]

        def getmultisig(chain, nr, signatures=[b"", b"", b""], nodes=nodes):
            return proto.MultisigRedeemScriptType(
                nodes=nodes, address_n=[chain, nr], signatures=signatures, m=2
            )

        correcthorse = proto.HDNodeType(
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
        inp1 = proto.TxInputType(
            address_n=parse_path("48'/145'/1'/1/0"),
            multisig=getmultisig(1, 0, [b"", sig, b""]),
            # bitcoincash:pp6kcpkhua7789g2vyj0qfkcux3yvje7euhyhltn0a
            amount=24000,
            prev_hash=TXHASH_f68caf,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address_n=parse_path("48'/145'/1'/1/1"),
            multisig=proto.MultisigRedeemScriptType(
                pubkeys=[
                    proto.HDNodePathType(node=nodes[0], address_n=[1, 1]),
                    proto.HDNodePathType(node=correcthorse, address_n=[]),
                    proto.HDNodePathType(node=correcthorse, address_n=[]),
                ],
                signatures=[b"", b"", b""],
                m=2,
            ),
            script_type=proto.OutputScriptType.PAYTOMULTISIG,
            amount=23000,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_f68caf),
                    request_input(0, TXHASH_f68caf),
                    request_output(0, TXHASH_f68caf),
                    request_output(1, TXHASH_f68caf),
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
            == "304402201badcdcafef4855ed58621f95935efcbc72068510472140f4ec5e252faa0af93022003310a43488288f70aedee96a5af2643a255268a6858cda9ae3001ea5e3c7557"
        )
        assert (
            serialized_tx.hex()
            == "01000000015f3d291cae106548f3be5ed0f4cbedc65668fa881d60347ab0d512df10af8cf601000000fc0047304402201badcdcafef4855ed58621f95935efcbc72068510472140f4ec5e252faa0af93022003310a43488288f70aedee96a5af2643a255268a6858cda9ae3001ea5e3c75574147304402207274b5a4d15e75f3df7319a375557b0efba9b27bc63f9f183a17da95a6125c94022000efac57629f1522e2d3958430e2ef073b0706cfac06cce492651b79858f09ae414c69522102245739b55787a27228a4fe78b3a324366cc645fbaa708cad45da351a334341192102debbdcb0b6970d5ade84a50fdbda1c701cdde5c9925d9b6cd8e05a9a15dbef352102ffe5fa04547b2b0c3cfbc21c08a1ddfb147025fee10274cdcd5c1bdeee88eae253aeffffffff01d85900000000000017a914a23eb2a1ed4003d357770120f5c370e199ee55468700000000"
        )

    @pytest.mark.multisig
    def test_send_bch_multisig_change(self, client):
        nodes = [
            btc.get_public_node(
                client, parse_path(f"48'/145'/{i}'"), coin_name="Bcash"
            ).node
            for i in range(1, 4)
        ]

        def getmultisig(chain, nr, signatures=[b"", b"", b""], nodes=nodes):
            return proto.MultisigRedeemScriptType(
                nodes=nodes, address_n=[chain, nr], signatures=signatures, m=2
            )

        inp1 = proto.TxInputType(
            address_n=parse_path("48'/145'/3'/0/0"),
            multisig=getmultisig(0, 0),
            amount=48490,
            prev_hash=TXHASH_8b6db9,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out1 = proto.TxOutputType(
            address="bitcoincash:qqq8gx2j76nw4dfefumxmdwvtf2tpsjznusgsmzex9",
            amount=24000,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        out2 = proto.TxOutputType(
            address_n=parse_path("48'/145'/3'/1/0"),
            multisig=getmultisig(1, 0),
            script_type=proto.OutputScriptType.PAYTOMULTISIG,
            amount=24000,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_8b6db9),
                    request_input(0, TXHASH_8b6db9),
                    request_output(0, TXHASH_8b6db9),
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
            == "3045022100a05f77bb39515c21c43e6c4ba401f39ed5d409dc3cfcd90f9a8345a08cc4bc8202205faf8f3b0775748278495324fdd60f370460452e4995e546450209ec4804a0f3"
        )

        inp1 = proto.TxInputType(
            address_n=parse_path("48'/145'/1'/0/0"),
            multisig=getmultisig(0, 0, [b"", b"", signatures1[0]]),
            # bitcoincash:pqguz4nqq64jhr5v3kvpq4dsjrkda75hwy86gq0qzw
            amount=48490,
            prev_hash=TXHASH_8b6db9,
            prev_index=0,
            script_type=proto.InputScriptType.SPENDMULTISIG,
        )
        out2.address_n[2] = H_(1)

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    request_output(1),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_8b6db9),
                    request_input(0, TXHASH_8b6db9),
                    request_output(0, TXHASH_8b6db9),
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
            == "3044022006f239ef1f065a70873ab9d2c81a623a04ec7a37a0ec5299d3c585668f441f49022032b2f9ef13bc61230d14f6d79b9ad1bbebdf47b95e4757e9af1b1dcdf520d3ab"
        )
        assert (
            serialized_tx.hex()
            == "0100000001a07660b10df9868df9393c9cf8962bc34f48cb2cea53b0865d2324bab8b96d8b00000000fdfd0000473044022006f239ef1f065a70873ab9d2c81a623a04ec7a37a0ec5299d3c585668f441f49022032b2f9ef13bc61230d14f6d79b9ad1bbebdf47b95e4757e9af1b1dcdf520d3ab41483045022100a05f77bb39515c21c43e6c4ba401f39ed5d409dc3cfcd90f9a8345a08cc4bc8202205faf8f3b0775748278495324fdd60f370460452e4995e546450209ec4804a0f3414c69522102f8ca0d9665af03de32a7c19a167a4f6e97e4e0ed9505f75d11f7a45ab60b1f4d2103263d87cefd687bc15b4ef7801f9f538267b66d46f18e9fccc41d54071cfdd1ce210388568bf42f02298308eb6fa2fa4b446d544600253b4409be27e2c0c1a71c424853aeffffffff02c05d0000000000001976a91400741952f6a6eab5394f366db5cc5a54b0c2429f88acc05d00000000000017a91478574751407449b97f8054be2e40e684ad07d3738700000000"
        )

    @pytest.mark.skip_t1
    def test_send_bch_external_presigned(self, client):
        inp1 = proto.TxInputType(
            # address_n=parse_path("44'/145'/0'/1/0"),
            # bitcoincash:qzc5q87w069lzg7g3gzx0c8dz83mn7l02scej5aluw
            amount=1896050,
            prev_hash=TXHASH_502e85,
            prev_index=0,
            script_type=proto.InputScriptType.EXTERNAL,
            script_sig=bytes.fromhex(
                "47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2d"
            ),
        )
        inp2 = proto.TxInputType(
            address_n=parse_path("44'/145'/0'/0/1"),
            # bitcoincash:qr23ajjfd9wd73l87j642puf8cad20lfmqdgwvpat4
            amount=73452,
            prev_hash=TXHASH_502e85,
            prev_index=1,
            script_type=proto.InputScriptType.SPENDADDRESS,
        )
        out1 = proto.TxOutputType(
            address="bitcoincash:qq6wnnkrz7ykaqvxrx4hmjvayvzjzml54uyk76arx4",
            amount=1934960,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )
        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
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

        assert (
            serialized_tx.hex()
            == "01000000022c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50000000006a47304402207a2a955f1cb3dc5f03f2c82934f55654882af4e852e5159639f6349e9386ec4002205fb8419dce4e648eae8f67bc4e369adfb130a87d2ea2d668f8144213b12bb457412103174c61e9c5362507e8061e28d2c0ce3d4df4e73f3535ae0b12f37809e0f92d2dffffffff2c06cf6f215c5cbfd7caa8e71b1b32630cabf1f816a4432815b037b277852e50010000006a473044022062151cf960b71823bbe68c7ed2c2a93ad1b9706a30255fddb02fcbe056d8c26102207bad1f0872bc5f0cfaf22e45c925c35d6c1466e303163b75cb7688038f1a5541412102595caf9aeb6ffdd0e82b150739a83297358b9a77564de382671056ad9e5b8c58ffffffff0170861d00000000001976a91434e9cec317896e818619ab7dc99d2305216ff4af88ac00000000"
        )
