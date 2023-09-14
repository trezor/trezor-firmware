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
from trezorlib.tools import parse_path

from ...tx_cache import TxCache
from .signtx import (
    request_extra_data,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType
TX_API = TxCache("Zcash Testnet")

TXHASH_aaf51e = bytes.fromhex(
    "aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc"
)
TXHASH_e38206 = bytes.fromhex(
    "e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368"
)

FAKE_TXHASH_v1 = bytes.fromhex(
    "8d800c64061967e480efbf3b19139d9136e586e9e3aaca65b9791e13cde4051b"
)
FAKE_TXHASH_v2 = bytes.fromhex(
    "6a9e8a6c36d6e33962b204d5942ddf62ed42f969cbf77f3075e298af926b056e"
)
FAKE_TXHASH_v3 = bytes.fromhex(
    "158640a6a19d771c34596cd1272b00f3ce95efe16dc1cedc496d40260fef0025"
)
FAKE_TXHASH_v4 = bytes.fromhex(
    "cb3c1190798dc7909f182ae9ae23e7c473d849ba5b933eb34538b9957fa87975"
)

pytestmark = [pytest.mark.altcoin, pytest.mark.zcash]


def test_v3_not_supported(client: Client):
    # prevout: aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc:1
    # input 1: 3.0 TAZ

    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300_000_000,
        prev_hash=TXHASH_aaf51e,
        prev_index=1,
    )

    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300_000_000 - 1_940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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


def test_one_one_fee_sapling(client: Client):
    # prevout: e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368:0
    # input 1: 3.0 TAZ

    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300_000_000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300_000_000 - 1_940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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


def test_version_group_id_missing(client: Client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300_000_000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300_000_000 - 1_940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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


def test_spend_old_versions(client: Client):
    # NOTE: fake input tx used

    input_v1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=123_000_000,
        prev_hash=FAKE_TXHASH_v1,
        prev_index=0,
    )
    input_v2 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/1"),
        amount=49_990_000,
        prev_hash=FAKE_TXHASH_v2,
        prev_index=0,
    )
    input_v3 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/2"),
        amount=300_000_000,
        prev_hash=FAKE_TXHASH_v3,
        prev_index=1,
    )
    input_v4 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/3"),
        amount=100_000,
        prev_hash=FAKE_TXHASH_v4,
        prev_index=0,
    )

    inputs = [input_v1, input_v2, input_v3, input_v4]

    for i, txi in enumerate(inputs, 1):
        txdata = TX_API[txi.prev_hash]
        assert txdata.version == i

    output = messages.TxOutputType(
        address="tmNvfeKR5PkcQazLEqddTskFr6Ev9tsovfQ",
        amount=sum(txi.amount for txi in inputs),
        script_type=messages.OutputScriptType.PAYTOADDRESS,
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
        == "0400008085202f89041b05e4cd131e79b965caaae3e986e536919d13193bbfef80e4671906640c808d000000006b483045022100cdfe9b6d122fafafd379b6475db67d4db3f79d77a648961a647a73f4a9561a3702201f4838467ac2a9bbbbb1067d24101fc46cbfa403f8c1258ec46d3d3ef00a72fb0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff6e056b92af98e275307ff7cb69f942ed62df2d94d504b26239e3d6366c8a9e6a000000006b4830450221009e6523a7c0e2ad691f45f8529ae609117b4441cdbc17b0b3800901cb89118cdd0220746c051a8cd213efcf8da34aea538ec6c31a5e3362733a724f88d7029a07954e01210294e3e5e77e22eea0e4c0d30d89beb4db7f69b4bf1ae709e411d6a06618b8f852ffffffff2500ef0f26406d49dccec16de1ef95cef3002b27d16c59341c779da1a6408615010000006a47304402205bf0e3316d2bcf8e97cb7f1fd8556858bc212c28621b2f6741faee83191abf73022015d56d65f7a5860c464f7540f279b28d7dedbbdbb13f4bc562dff42083d0ed40012103f5008445568548bd745a3dedccc6048969436bf1a49411f60938ff1938941f14ffffffff7579a87f95b93845b33e935bba49d873c4e723aee92a189f90c78d7990113ccb000000006a47304402200740dff2e8dc0ed6d44d0a0104e79bd668387508c93cfde75f1aa1094e63816b02207ecb432fdbf6e05d6b97a489575d62a7ff6e1a885205d33eeac08d9656597e640121029ad0b9519779c540b34fa8d11d24d14a5475546bfa28c7de50573d22a503ce21ffffffff01d0c7321c000000001976a91490ede9de4bed6e39008375eace793949de9a533288ac00000000000000000000000000000000000000"
    )


@pytest.mark.skip_t1
def test_external_presigned(client: Client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300_000_000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )

    inp2 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        # address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300_000_000,
        prev_hash=TXHASH_aaf51e,
        prev_index=1,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a914a579388225827d9f2fe9014add644487808c695d88ac"
        ),
        script_sig=bytes.fromhex(
            "47304402202495a38e5b368569a1a0c9fc95aa7e57a0dd5ae43f51300d7222dc139015233d022047833eaa571578f72c8468c8b537b36410388b7eb5001d75d1f4b954e1997d590121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        ),
    )

    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300_000_000 + 300_000_000 - 1_940,
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
