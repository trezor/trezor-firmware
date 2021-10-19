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
from trezorlib.tools import parse_path

from ..tx_cache import TxCache
from .signtx import (
    request_extra_data,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = proto.ButtonRequestType
TX_API = TxCache("Zcash Testnet")

TXHASH_aaf51e = bytes.fromhex(
    "aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc"
)
TXHASH_e38206 = bytes.fromhex(
    "e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368"
)

TXHASH_v1 = bytes.fromhex(
    "fb91ae741b120125b6d5c33a62f50a201b6ffd1cdc470c378c1ac8c654808246"
)
TXHASH_v2 = bytes.fromhex(
    "03d30e19959d46d62ac796b8b23497b8c5700c59c4c75e1dbce7b8de49e242ef"
)
TXHASH_v3 = bytes.fromhex(
    "f9418829d18140815f961c3f968b08700c283b616f3cb0f43413ae89e68ab76c"
)
TXHASH_v4 = bytes.fromhex(
    "5d8de67264b08eecc8e3bee19a11a7f54a2bce1dc4f2a699538e372ae92e9c0f"
)


@pytest.mark.altcoin
@pytest.mark.zcash
class TestMsgSigntxZcash:
    def test_v3_not_supported(self, client):
        # prevout: aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc:1
        # input 1: 3.0 TAZ

        inp1 = proto.TxInputType(
            # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            address_n=parse_path("m/44h/1h/0h/0/0"),
            amount=300000000,
            prev_hash=TXHASH_aaf51e,
            prev_index=1,
        )

        out1 = proto.TxOutputType(
            address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
            amount=300000000 - 1940,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client, pytest.raises(TrezorFailure, match="DataError"):
            btc.sign_tx(
                client,
                "Zcash Testnet",
                [inp1],
                [out1],
                version=3,
                version_group_id=0x03C48270,
                branch_id=0x5BA81B19,
                prev_txes=TX_API,
            )

    def test_one_one_fee_sapling(self, client):
        # prevout: e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368:0
        # input 1: 3.0 TAZ

        inp1 = proto.TxInputType(
            # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            address_n=parse_path("m/44h/1h/0h/0/0"),
            amount=300000000,
            prev_hash=TXHASH_e38206,
            prev_index=0,
        )

        out1 = proto.TxOutputType(
            address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
            amount=300000000 - 1940,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            client.set_expected_responses(
                [
                    request_input(0),
                    request_output(0),
                    proto.ButtonRequest(code=B.ConfirmOutput),
                    proto.ButtonRequest(code=B.SignTx),
                    request_input(0),
                    request_meta(TXHASH_e38206),
                    request_input(0, TXHASH_e38206),
                    request_input(1, TXHASH_e38206),
                    request_output(0, TXHASH_e38206),
                    request_output(1, TXHASH_e38206),
                    request_extra_data(0, 1, TXHASH_e38206),
                    request_input(0),
                    request_output(0),
                    request_finished(),
                ]
            )

            _, serialized_tx = btc.sign_tx(
                client,
                "Zcash Testnet",
                [inp1],
                [out1],
                version=4,
                version_group_id=0x892F2085,
                branch_id=0x76B809BB,
                prev_txes=TX_API,
            )

        # Accepted by network: tx 0cef132c1d6d67f11cfa48f7fca3209da29cf872ac782354bedb686e61a17a78
        assert (
            serialized_tx.hex()
            == "0400008085202f890168039326c180fa7b1e999392e25a3ec6a8aec83c11b787ddb1746922020682e3000000006b483045022100f28298891f48706697a6f898ac18e39ce2c7cebe547b585d51cc22d80b1b21a602201a807b8a18544832d95d1e3ada82c0617bc6d97d3f24d1fb4801ac396647aa880121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff016c9be111000000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac00000000000000000000000000000000000000"
        )

    def test_version_group_id_missing(self, client):
        inp1 = proto.TxInputType(
            # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            address_n=parse_path("m/44h/1h/0h/0/0"),
            amount=300000000,
            prev_hash=TXHASH_e38206,
            prev_index=0,
        )
        out1 = proto.TxOutputType(
            address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
            amount=300000000 - 1940,
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with pytest.raises(TrezorFailure, match="Version group ID must be set."):
            btc.sign_tx(
                client,
                "Zcash Testnet",
                [inp1],
                [out1],
                version=4,
                prev_txes=TX_API,
            )

    def test_spend_old_versions(self, client):
        # inputs are NOT OWNED by this seed
        input_v1 = proto.TxInputType(
            address_n=parse_path("m/44h/1h/0h/0/0"),
            amount=123000000,
            prev_hash=TXHASH_v1,
            prev_index=0,
        )
        input_v2 = proto.TxInputType(
            address_n=parse_path("m/44h/1h/0h/0/1"),
            amount=49990000,
            prev_hash=TXHASH_v2,
            prev_index=0,
        )
        input_v3 = proto.TxInputType(
            address_n=parse_path("m/44h/1h/0h/0/2"),
            amount=300000000,
            prev_hash=TXHASH_v3,
            prev_index=1,
        )
        input_v4 = proto.TxInputType(
            address_n=parse_path("m/44h/1h/0h/0/3"),
            amount=100000,
            prev_hash=TXHASH_v4,
            prev_index=0,
        )

        inputs = [input_v1, input_v2, input_v3, input_v4]

        for i, txi in enumerate(inputs, 1):
            txdata = TX_API[txi.prev_hash]
            assert txdata.version == i

        output = proto.TxOutputType(
            address="tmNvfeKR5PkcQazLEqddTskFr6Ev9tsovfQ",
            amount=sum(txi.amount for txi in inputs),
            script_type=proto.OutputScriptType.PAYTOADDRESS,
        )

        with client:
            _, serialized_tx = btc.sign_tx(
                client,
                "Zcash Testnet",
                inputs,
                [output],
                version=4,
                version_group_id=0x892F2085,
                branch_id=0x76B809BB,
                prev_txes=TX_API,
            )

        assert (
            serialized_tx.hex()
            == "0400008085202f890446828054c6c81a8c370c47dc1cfd6f1b200af5623ac3d5b62501121b74ae91fb000000006b483045022100d40e85efbadd378fc603dc8b11c70774086de631fe5b1418ac2b95a478f86507022072e999d8ddd75a0b33bd2adcc88e7234e6251b9e73c9223e7c59e0d1f8d1ff220121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffffef42e249deb8e7bc1d5ec7c4590c70c5b89734b2b896c72ad6469d95190ed303000000006b483045022100917d96445d64c80f9569cb9ca45c04c9b6d7b0fda6b9fd0b1d311837366c699202202cd6140489cf38b5d97ed271ba28603f4693c2a36113cc6ec423301f077c5a8e01210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852ffffffff6cb78ae689ae1334f4b03c6f613b280c70088b963f1c965f814081d1298841f9010000006a473044022058768c74c9b1698070636388d7d2ae8223748f13b0a5f402716e4d49fc5bc5f30220658d1e6095dcfbe66669b4141d23af28c9ed5bae73480889429b41742be85f32012103f5008445568548bd745a3dedccc6048969436bf1a49411f60938ff1938941f14ffffffff0f9c2ee92a378e5399a6f2c41dce2b4af5a7119ae1bee3c8ec8eb06472e68d5d000000006b483045022100e64853d86bed039c4edce4abaf80d41486cd21c63bec79c0308ea05a351663e302206732aa22a5dee7bd7f3cc8268faebe31a08abadb4b7e3a4257509bc7baa052b60121029ad0b9519779c540b34fa8d11d24d14a5475546bfa28c7de50573d22a503ce21ffffffff01d0c7321c000000001976a91490ede9de4bed6e39008375eace793949de9a533288ac00000000000000000000000000000000000000"
        )

    @pytest.mark.skip_t1
    def test_external_presigned(self, client):
        inp1 = proto.TxInputType(
            # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            address_n=parse_path("m/44h/1h/0h/0/0"),
            amount=300000000,
            prev_hash=TXHASH_e38206,
            prev_index=0,
        )

        inp2 = proto.TxInputType(
            # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
            # address_n=parse_path("m/44h/1h/0h/0/0"),
            amount=300000000,
            prev_hash=TXHASH_aaf51e,
            prev_index=1,
            script_type=proto.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex(
                "76a914a579388225827d9f2fe9014add644487808c695d88ac"
            ),
            script_sig=bytes.fromhex(
                "47304402202495a38e5b368569a1a0c9fc95aa7e57a0dd5ae43f51300d7222dc139015233d022047833eaa571578f72c8468c8b537b36410388b7eb5001d75d1f4b954e1997d590121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
            ),
        )

        out1 = proto.TxOutputType(
            address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
            amount=300000000 + 300000000 - 1940,
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
                    request_meta(TXHASH_e38206),
                    request_input(0, TXHASH_e38206),
                    request_input(1, TXHASH_e38206),
                    request_output(0, TXHASH_e38206),
                    request_output(1, TXHASH_e38206),
                    request_extra_data(0, 1, TXHASH_e38206),
                    request_input(1),
                    request_meta(TXHASH_aaf51e),
                    request_input(0, TXHASH_aaf51e),
                    request_output(0, TXHASH_aaf51e),
                    request_output(1, TXHASH_aaf51e),
                    request_extra_data(0, 1, TXHASH_aaf51e),
                    request_input(0),
                    request_input(1),
                    request_output(0),
                    request_finished(),
                ]
            )

            _, serialized_tx = btc.sign_tx(
                client,
                "Zcash Testnet",
                [inp1, inp2],
                [out1],
                version=4,
                version_group_id=0x892F2085,
                branch_id=0x76B809BB,
                prev_txes=TX_API,
            )

        assert (
            serialized_tx.hex()
            == "0400008085202f890268039326c180fa7b1e999392e25a3ec6a8aec83c11b787ddb1746922020682e3000000006a473044022007efbf539f8d612d8e140c6af2289b447c34e3d36edd75d539f269fe5526878302206830f6b0398494bca09afdd967fedcd016f49468711cfcd7aafd9a128ee568d20121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffffdc754d63eff4698ee321476872519c53f14cfe58c9425c7ee464c206461ef5aa010000006a47304402202495a38e5b368569a1a0c9fc95aa7e57a0dd5ae43f51300d7222dc139015233d022047833eaa571578f72c8468c8b537b36410388b7eb5001d75d1f4b954e1997d590121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff016c3ec323000000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac00000000000000000000000000000000000000"
        )
