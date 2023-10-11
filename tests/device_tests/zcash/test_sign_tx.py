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

from ..bitcoin.signtx import request_finished, request_input, request_output

B = messages.ButtonRequestType

TXHASH_aaf51e = bytes.fromhex(
    "aaf51e4606c264e47e5c42c958fe4cf1539c5172684721e38e69f4ef634d75dc"
)
TXHASH_e38206 = bytes.fromhex(  # FAKE TX
    "e3820602226974b1dd87b7113cc8aea8c63e5ae29293991e7bfa80c126930368"
)
TXHASH_f9231f = bytes.fromhex(
    "f9231f2d6cdcd86b4892c95a5d2045bacd81f4060e8127073456fbb7b7b51568"
)
TXHASH_c5309b = bytes.fromhex(
    "c5309bd6a18f6bf374918b1c96e872af02e80d678c53d37547de03048ace79bf"
)
TXHASH_431b68 = bytes.fromhex(
    "431b68c170799a1ba9a936f9bde4ba1fb5606b0ab0a770012875a23d23ba72a3"
)
TXHASH_4b6cec = bytes.fromhex(
    "4b6cecb81c825180786ebe07b65bcc76078afc5be0f1c64e08d764005012380d"
)

# This exact VERSION_GROUP_ID is absolutely necessary for a valid v5 transaction
# BRANCH_ID could maybe change
VERSION_GROUP_ID = 0x26A7270A
BRANCH_ID = 0xC2D6D0B4

pytestmark = [pytest.mark.altcoin, pytest.mark.zcash]


def test_version_group_id_missing(client: Client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )
    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300000000 - 1940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure, match="Version group ID must be set."):
        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1],
            version=5,
        )


def test_spend_v4_input(client: Client):
    # 4b6cecb81c825180786ebe07b65bcc76078afc5be0f1c64e08d764005012380d is a v4 tx

    inp1 = messages.TxInputType(
        # tmAgYbANTzZp7YoMkRbbaemQETgV5GkBEjF
        address_n=parse_path("m/44h/1h/0h/0/7"),
        amount=989_680,
        prev_hash=TXHASH_4b6cec,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        # m/44h/1h/0h/0/9
        address="tmBMyeJebzkP5naji8XUKqLyL1NDwNkgJFt",
        amount=989_680 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
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
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

        # Accepted by network: txid = b29b1f27763e8caf9fe51f33a6a7daf138438b5278efcd60941782244e35b19e
        assert (
            serialized_tx.hex()
            == "050000800a27a726b4d0d6c20000000000000000010d3812500064d7084ec6f1e05bfc8a0776cc5bb607be6e788051821cb8ec6c4b000000006b483045022100cc6efc5678eefec9dd95a890e5961be3e8fc64ea6654959873316fcd2d523d36022036036e2e23071812319d170484926bc641d54028613acaa28b1fd2530013a3400121035169c4d6a36b6c4f3e210f46d329efa1cb7a67ffce7d62062d4a8a17c23756e1ffffffff01e0f20e00000000001976a9141215d421cb8cec1dea62cbd9e4e07c01520d873f88ac000000"
        )


def test_send_to_multisig(client: Client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/8"),
        amount=1_000_000,
        prev_hash=bytes.fromhex(
            "d8cfa377012ca0b8d856586693b530835bf2fa14add0380e24ec6755bed5b931"
        ),
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address="t2PQpjcfpYHK1bcXZcSaTbg5cQRV93B2NRY",
        amount=1_000_000 - 19_400,
        script_type=messages.OutputScriptType.PAYTOSCRIPTHASH,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
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
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

        # Accepted by network: txid = 431b68c170799a1ba9a936f9bde4ba1fb5606b0ab0a770012875a23d23ba72a3
        assert (
            serialized_tx.hex()
            == "050000800a27a726b4d0d6c200000000000000000131b9d5be5567ec240e38d0ad14faf25b8330b593665856d8b8a02c0177a3cfd8000000006a4730440220578ca11522b12ab2048b5c81a2ef788cccfacdb42d08efb31a802ee75909c38c02202fd12addfae4822141821b14a012828c7a4a46cc02de777101d1b8ee14128070012103260dc4925b14addb52b4e62c698b99d2318f3d909477a081ae8e5d94dc3c66d8ffffffff0178f60e000000000017a914b8f771de8bbdcfee76e0dbf76f1005f2028bf3e787000000"
        )


def test_spend_v5_input(client: Client):
    inp1 = messages.TxInputType(
        # tmBMyeJebzkP5naji8XUKqLyL1NDwNkgJFt
        address_n=parse_path("m/44h/1h/0h/0/9"),
        amount=4_154_120,
        prev_hash=TXHASH_f9231f,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        # m/44h/1h/0h/0/0
        address="tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu",
        amount=4_154_120 - 19_400,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
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
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

        # Accepted by network: txid = c5309bd6a18f6bf374918b1c96e872af02e80d678c53d37547de03048ace79bf
        assert (
            serialized_tx.hex()
            == "050000800a27a726b4d0d6c20000000000000000016815b5b7b7fb56340727810e06f481cdba45205d5ac992486bd8dc6c2d1f23f9000000006a47304402201fc2effdaa338d4fd42a018debed2c8a170c57c7763faabf9596ea408961cc5b02200dd35764d2797723c73f2984c5ea49522d4558ca3c5143e95235f522f65c84b5012102b3397d76b093624981b3c3a279c79496d16820f821528b9e403bdfc162b34c3cffffffff0140173f00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000000"
        )


def test_one_two(client: Client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=4_134_720,
        prev_hash=TXHASH_c5309b,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        # m/44h/1h/0h/0/8
        address="tmCYEhUmZGpzyFrhUdKqwt64DrPqkFNChxx",
        amount=1_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=4_134_720 - 1_000_000 - 2_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1, out2],
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

        # Accepted by network: txid = d8cfa377012ca0b8d856586693b530835bf2fa14add0380e24ec6755bed5b931
        assert (
            serialized_tx.hex()
            == "050000800a27a726b4d0d6c2000000000000000001bf79ce8a0403de4775d3538c670de802af72e8961c8b9174f36b8fa1d69b30c5000000006b483045022100be78eccf801dda4dd33f9d4e04c2aae01022869d1d506d51669204ec269d71a90220394a51838faf40176058cf45fe7032be9c5c942e21aff35d7dbe4b96ab5e0a500121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0240420f00000000001976a9141efeae5c937bfc7f095a06aabdb5476a5d6d19db88ac30cd2f00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000000"
        )


@pytest.mark.skip_t1
def test_unified_address(client: Client):
    # identical to the test_one_two
    # but receiver address is unified with an orchard address
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=4_134_720,
        prev_hash=TXHASH_c5309b,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        # p2pkh: m/44h/1h/0h/0/8 + orchard: m/32h/1h/0h
        address="utest1xt8k2akcdnncjfz8sfxkm49quc4w627skp3qpggkwp8c8ay3htftjf7tur9kftcw0w4vu4scwfg93ckfag84khy9k40yanl5k0qkanh9cyhddgws786qeqn37rtyf6rx4eflz09zk06",
        amount=1_000_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    out2 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=4_134_720 - 1_000_000 - 2_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                request_output(1),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1, out2],
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

        # Accepted by network: txid = d8cfa377012ca0b8d856586693b530835bf2fa14add0380e24ec6755bed5b931
        assert (
            serialized_tx.hex()
            == "050000800a27a726b4d0d6c2000000000000000001bf79ce8a0403de4775d3538c670de802af72e8961c8b9174f36b8fa1d69b30c5000000006b483045022100be78eccf801dda4dd33f9d4e04c2aae01022869d1d506d51669204ec269d71a90220394a51838faf40176058cf45fe7032be9c5c942e21aff35d7dbe4b96ab5e0a500121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff0240420f00000000001976a9141efeae5c937bfc7f095a06aabdb5476a5d6d19db88ac30cd2f00000000001976a914a579388225827d9f2fe9014add644487808c695d88ac000000"
        )


@pytest.mark.skip_t1
def test_external_presigned(client: Client):
    inp1 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_e38206,
        prev_index=0,
    )

    inp2 = messages.TxInputType(
        # tmQoJ3PTXgQLaRRZZYT6xk8XtjRbr2kCqwu
        # address_n=parse_path("m/44h/1h/0h/0/0"),
        amount=300000000,
        prev_hash=TXHASH_aaf51e,
        prev_index=1,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a914a579388225827d9f2fe9014add644487808c695d88ac"
        ),
        script_sig=bytes.fromhex(
            "47304402207635614c690bfe8701ebe822a7322273feaa8d664a82780901628fd4c907879e022011541c320b9d994b16ee7251b41a76e5edb5842cf2fa77db2c9381f32f921b0f0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0"
        ),
    )

    out1 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=300000000 + 300000000 - 1940,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        is_core = client.features.model in ("T", "Safe 3")
        client.set_expected_responses(
            [
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(1),
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
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

        # FAKE tx
        assert (
            serialized_tx.hex()
            == "050000800a27a726b4d0d6c200000000000000000268039326c180fa7b1e999392e25a3ec6a8aec83c11b787ddb1746922020682e3000000006b48304502210083493f0a49e80b95469ea933e369500b69e73871d3e6d6c404f4bc8fc98701a80220326f5159a3fa17abc001cc6126ba5268ec78f34cccd559821fb7b57cbe0697080121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffffdc754d63eff4698ee321476872519c53f14cfe58c9425c7ee464c206461ef5aa010000006a47304402207635614c690bfe8701ebe822a7322273feaa8d664a82780901628fd4c907879e022011541c320b9d994b16ee7251b41a76e5edb5842cf2fa77db2c9381f32f921b0f0121030e669acac1f280d1ddf441cd2ba5e97417bf2689e4bbec86df4f831bf9f7ffd0ffffffff016c3ec323000000001976a9145b157a678a10021243307e4bb58f36375aa80e1088ac000000"
        )


def test_refuse_replacement_tx(client: Client):
    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/1h/0h/0/4"),
        amount=174998,
        prev_hash=bytes.fromhex(
            "beafc7cbd873d06dbee88a7002768ad5864228639db514c81cfb29f108bb1e7a"
        ),
        prev_index=0,
        orig_hash=bytes.fromhex(
            "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
        ),
        orig_index=0,
    )

    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/1h/0h/1/2"),
        amount=174998 - 50000 - 1111,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=bytes.fromhex(
            "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
        ),
        orig_index=0,
    )

    out2 = messages.TxOutputType(
        address="tmJ1xYxP8XNTtCoDgvdmQPSrxh5qZJgy65Z",
        amount=50000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        orig_hash=bytes.fromhex(
            "50f6f1209ca92d7359564be803cb2c932cde7d370f7cee50fd1fad6790f6206d"
        ),
        orig_index=1,
    )

    with pytest.raises(
        TrezorFailure, match="Replacement transactions are not supported."
    ):
        btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1, out2],
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )


def test_spend_multisig(client: Client):
    # Cloned from tests/device_tests/bitcoin/test_multisig.py::test_2_of_3

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/48h/1h/{index}h/0h"), coin_name="Zcash Testnet"
        ).node
        for index in range(1, 4)
    ]

    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[0, 0], signatures=[b"", b"", b""], m=2
    )
    # Let's go to sign with key 1
    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/1h/1h/0h/0/0"),
        amount=980_600,
        prev_hash=TXHASH_431b68,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    out1 = messages.TxOutputType(
        # m/44h/1h/0h/0/4
        address="tmHRQfcNVCZnjY8g6X7Yp6Tcpx8M5gy4Joj",
        amount=980_600 - 10_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    # Expected responses are the same for both two signings
    is_core = client.features.model in ("T", "Safe 3")
    expected_responses = [
        request_input(0),
        request_output(0),
        messages.ButtonRequest(code=B.ConfirmOutput),
        (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
        messages.ButtonRequest(code=B.SignTx),
        request_input(0),
        request_output(0),
        request_finished(),
    ]

    with client:
        client.set_expected_responses(expected_responses)
        signatures1, _ = btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp1],
            [out1],
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

    assert (
        signatures1[0].hex()
        == "3045022100d1f91921391ca4a985cbe080ce8be71f1b8ceba6049151bffe7dc6cc27a4a4d80220082fb171f7536779cd216f0508e0205039b2f20988d05455dac9bc22bc713005"
    )

    # Now we have first signature

    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes,
        address_n=[0, 0],
        signatures=[
            signatures1[0],
            b"",
            b"",
        ],  # Fill signature from previous signing process
        m=2,
    )

    # Let's do a second signature with key 3
    inp3 = messages.TxInputType(
        address_n=parse_path("m/48h/1h/3h/0h/0/0"),
        amount=980_600,
        prev_hash=TXHASH_431b68,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
        multisig=multisig,
    )

    with client:
        client.set_expected_responses(expected_responses)
        signatures2, serialized_tx = btc.sign_tx(
            client,
            "Zcash Testnet",
            [inp3],
            [out1],
            version=5,
            version_group_id=VERSION_GROUP_ID,
            branch_id=BRANCH_ID,
        )

    assert (
        signatures2[0].hex()
        == "3044022058bb0b1ac0d6b62b6f86bdb32879e9240369387282e73a96cb6fbeba56f5493e02206dabb42fc4ce4f5d97bc641f353e7351949695d8e6383764e76eebe572cc33fc"
    )

    # Accepted by network: txid = 38f6771c8deabc3a8b960e0c8b6aa464ddfab469e7298e91a7900101f7b60880
    assert (
        serialized_tx.hex()
        == "050000800a27a726b4d0d6c2000000000000000001a372ba233da275280170a7b00a6b60b51fbae4bdf936a9a91b9a7970c1681b4300000000fdfd0000483045022100d1f91921391ca4a985cbe080ce8be71f1b8ceba6049151bffe7dc6cc27a4a4d80220082fb171f7536779cd216f0508e0205039b2f20988d05455dac9bc22bc71300501473044022058bb0b1ac0d6b62b6f86bdb32879e9240369387282e73a96cb6fbeba56f5493e02206dabb42fc4ce4f5d97bc641f353e7351949695d8e6383764e76eebe572cc33fc014c69522103725d6c5253f2040a9a73af24bcc196bf302d6cc94374dd7197b138e10912670121038924e94fff15302a3fb45ad4fc0ed17178800f0f1c2bdacb1017f4db951aa9f12102aae8affd0eb8e1181d665daef4de1828f23053c548ec9bafc3a787f558aa014153aeffffffff0168cf0e00000000001976a914548cb80e45b1d36312fe0cb075e5e337e3c54cef88ac000000"
    )
