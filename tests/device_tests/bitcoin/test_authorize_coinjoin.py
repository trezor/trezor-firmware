# This file is part of the Trezor project.
#
# Copyright (C) 2020 SatoshiLabs and contributors
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

import time

import pytest

from trezorlib import btc, device, messages
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import parse_path

from ...common import is_core
from ...tx_cache import TxCache
from .payment_req import make_coinjoin_request
from .signtx import (
    assert_tx_matches,
    request_finished,
    request_input,
    request_meta,
    request_output,
)

B = messages.ButtonRequestType

TX_CACHE_TESTNET = TxCache("Testnet")
TX_CACHE_MAINNET = TxCache("Bitcoin")

FAKE_TXHASH_e5b7e2 = bytes.fromhex(
    "e5b7e21b5ba720e81efd6bfa9f854ababdcddc75a43bfa60bf0fe069cfd1bb8a"
)
FAKE_TXHASH_f982c0 = bytes.fromhex(
    "f982c0a283bd65a59aa89eded9e48f2a3319cb80361dfab4cf6192a03badb60a"
)
TXHASH_2cc3c1 = bytes.fromhex(
    "2cc3c1e33fb1cb7b4fccf4e0fead3fc077a1eb6c22e61561b343b704a5a8da6d"
)
TXHASH_7f3a34 = bytes.fromhex(
    "7f3a348106f9f3688069f389c00842b18d26770ec9a96ea94bf21623433a0f72"
)

PIN = "1234"
ROUND_ID_LEN = 32
SLIP25_PATH = parse_path("m/10025h")


@pytest.mark.parametrize("chunkify", (True, False))
@pytest.mark.setup_client(pin=PIN)
def test_sign_tx(client: Client, chunkify: bool):
    # NOTE: FAKE input tx

    commitment_data = b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big")

    with client:
        client.use_pin_sequence([PIN])
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_rounds=2,
            max_coordinator_fee_rate=500_000,  # 0.5 %
            max_fee_per_kvbyte=3500,
            n=parse_path("m/10025h/1h/0h/1h"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    client.call(messages.LockDevice())

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest, messages.OwnershipProof]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=commitment_data,
            preauthorized=True,
        )

    with client:
        client.set_expected_responses(
            [messages.PreauthorizedRequest, messages.OwnershipProof]
        )
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/5"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=commitment_data,
            preauthorized=True,
        )

    inputs = [
        messages.TxInputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/0/0
            # tb1pkw382r3plt8vx6e22mtkejnqrxl4z7jugh3w4rjmfmgezzg0xqpsdaww8z
            amount=100_000,
            prev_hash=FAKE_TXHASH_e5b7e2,
            prev_index=0,
            script_type=messages.InputScriptType.EXTERNAL,
            script_pubkey=bytes.fromhex(
                "5120b3a2750e21facec36b2a56d76cca6019bf517a5c45e2ea8e5b4ed191090f3003"
            ),
            ownership_proof=bytearray.fromhex(
                "534c001901019cf1b0ad730100bd7a69e987d55348bb798e2b2096a6a5713e9517655bd2021300014052d479f48d34f1ca6872d4571413660040c3e98841ab23a2c5c1f37399b71bfa6f56364b79717ee90552076a872da68129694e1b4fb0e0651373dcf56db123c5"
            ),
            commitment_data=commitment_data,
        ),
        messages.TxInputType(
            address_n=parse_path("m/10025h/1h/0h/1h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        ),
    ]

    input_script_pubkeys = [
        bytes.fromhex(
            "5120b3a2750e21facec36b2a56d76cca6019bf517a5c45e2ea8e5b4ed191090f3003"
        ),
        bytes.fromhex(
            "51202f436892d90fb2665519efa3d9f0f5182859124f179486862c2cd7a78ea9ac19"
        ),
    ]

    outputs = [
        # Other's coinjoined output.
        messages.TxOutputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/1/0
            address="tb1pupzczx9cpgyqgtvycncr2mvxscl790luqd8g88qkdt2w3kn7ymhsrdueu2",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
        # Our coinjoined output.
        messages.TxOutputType(
            # tb1phkcspf88hge86djxgtwx2wu7ddghsw77d6sd7txtcxncu0xpx22shcydyf
            address_n=parse_path("m/10025h/1h/0h/1h/1/1"),
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
        # Our change output.
        messages.TxOutputType(
            # tb1pchruvduckkwuzm5hmytqz85emften5dnmkqu9uhfxwfywaqhuu0qjggqyp
            address_n=parse_path("m/10025h/1h/0h/1h/1/2"),
            amount=7_289_000 - 50_000 - 36_445 - 490,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
        # Other's change output.
        messages.TxOutputType(
            # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
            # m/10025h/1h/0h/1h/1/1
            address="tb1pvt7lzserh8xd5m6mq0zu9s5wxkpe5wgf5ts56v44jhrr6578hz8saxup5m",
            amount=100_000 - 50_000 - 500 - 490,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
        # Coordinator's output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=36_945,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
    ]

    output_script_pubkeys = [
        bytes.fromhex(
            "5120e0458118b80a08042d84c4f0356d86863fe2bffc034e839c166ad4e8da7e26ef"
        ),
        bytes.fromhex(
            "5120bdb100a4e7ba327d364642dc653b9e6b51783bde6ea0df2ccbc1a78e3cc13295"
        ),
        bytes.fromhex(
            "5120c5c7c63798b59dc16e97d916011e99da5799d1b3dd81c2f2e93392477417e71e"
        ),
        bytes.fromhex(
            "512062fdf14323b9ccda6f5b03c5c2c28e35839a3909a2e14d32b595c63d53c7b88f"
        ),
        bytes.fromhex("76a914a579388225827d9f2fe9014add644487808c695d88ac"),
    ]

    coinjoin_req = make_coinjoin_request(
        "www.example.com",
        inputs,
        input_script_pubkeys,
        outputs,
        output_script_pubkeys,
        no_fee_indices=[],
    )

    with client:
        client.set_expected_responses(
            [
                messages.PreauthorizedRequest(),
                request_input(0),
                request_input(1),
                request_output(0),
                request_output(1),
                request_output(2),
                request_output(3),
                request_output(4),
                request_input(1),
                request_finished(),
            ]
        )
        signatures, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            coinjoin_request=coinjoin_req,
            preauthorized=True,
            serialize=False,
            chunkify=chunkify,
        )

    assert serialized_tx == b""
    assert len(signatures) == 2
    assert signatures[0] is None
    assert (
        signatures[1].hex()
        == "c017fce789fa8db54a2ae032012d2dd6d7c76cc1c1a6f00e29b86acbf93022da8aa559009a574792c7b09b2535d288d6e03c6ed169902ed8c4c97626a83fbc11"
    )

    # Test for a second time.
    btc.sign_tx(
        client,
        "Testnet",
        inputs,
        outputs,
        prev_txes=TX_CACHE_TESTNET,
        coinjoin_request=coinjoin_req,
        preauthorized=True,
        chunkify=chunkify,
    )

    # Test for a third time, number of rounds should be exceeded.
    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            coinjoin_request=coinjoin_req,
            preauthorized=True,
            chunkify=chunkify,
        )


def test_sign_tx_large(client: Client):
    # NOTE: FAKE input tx

    commitment_data = b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big")
    own_input_count = 10
    total_input_count = 400
    own_output_count = 30
    total_output_count = 1200
    output_denom = 10_000  # sats
    max_expected_delay = 60  # seconds

    with client:
        btc.authorize_coinjoin(
            client,
            coordinator="www.example.com",
            max_rounds=2,
            max_coordinator_fee_rate=500_000,  # 0.5 %
            max_fee_per_kvbyte=3500,
            n=parse_path("m/10025h/1h/0h/1h"),
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    # INPUTS.

    external_input = messages.TxInputType(
        # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
        # m/10025h/1h/0h/1h/0/0
        # tb1pkw382r3plt8vx6e22mtkejnqrxl4z7jugh3w4rjmfmgezzg0xqpsdaww8z
        amount=output_denom * total_output_count // total_input_count,
        prev_hash=FAKE_TXHASH_e5b7e2,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "5120b3a2750e21facec36b2a56d76cca6019bf517a5c45e2ea8e5b4ed191090f3003"
        ),
        ownership_proof=bytearray.fromhex(
            "534c001901019cf1b0ad730100bd7a69e987d55348bb798e2b2096a6a5713e9517655bd2021300014052d479f48d34f1ca6872d4571413660040c3e98841ab23a2c5c1f37399b71bfa6f56364b79717ee90552076a872da68129694e1b4fb0e0651373dcf56db123c5"
        ),
        commitment_data=commitment_data,
    )

    internal_inputs = [
        messages.TxInputType(
            address_n=parse_path(f"m/10025h/1h/0h/1h/1/{i}"),
            amount=output_denom * own_output_count // own_input_count,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )
        for i in range(own_input_count)
    ]
    internal_input_script_pubkeys = [
        bytes.fromhex(
            "51202f436892d90fb2665519efa3d9f0f5182859124f179486862c2cd7a78ea9ac19"
        ),
        bytes.fromhex(
            "5120bdb100a4e7ba327d364642dc653b9e6b51783bde6ea0df2ccbc1a78e3cc13295"
        ),
        bytes.fromhex(
            "5120c5c7c63798b59dc16e97d916011e99da5799d1b3dd81c2f2e93392477417e71e"
        ),
        bytes.fromhex(
            "5120148db939506345b047d945fff64691508c90da036ea3313b38b386ba3ec64ec5"
        ),
        bytes.fromhex(
            "51202cf0ba67bc759b413c0a36e33f5223aee574a979cfc1bc6e59b136cc43a8da8d"
        ),
        bytes.fromhex(
            "51202ad44db2df5b2a4d46e3655b1ab2402229676e35a3a43c4f7cae73e862c10775"
        ),
        bytes.fromhex(
            "51209e101215e14de4bece6cabd552f11e5931cb53119f43e52c10f9c1de0fd03390"
        ),
        bytes.fromhex(
            "5120f799c40379196e8507b8adf72c78b6cc12bb9fbae38f3ad744dfcd19a5777253"
        ),
        bytes.fromhex(
            "5120db0563942a92fb8c89ced9325c2660607605cd645027d64a9f641e6bc1694020"
        ),
        bytes.fromhex(
            "51208f1bbec30c355ec71f7a87c5ea06547c9b9b8a51c7834cd726e13cbb83226d16"
        ),
    ]

    inputs = internal_inputs + [external_input] * (total_input_count - own_input_count)

    input_script_pubkeys = internal_input_script_pubkeys + [
        external_input.script_pubkey
    ] * (total_input_count - own_input_count)

    # OUTPUTS.

    external_output = messages.TxOutputType(
        # seed "alcohol woman abuse must during monitor noble actual mixed trade anger aisle"
        # m/10025h/1h/0h/1h/1/0
        address="tb1pupzczx9cpgyqgtvycncr2mvxscl790luqd8g88qkdt2w3kn7ymhsrdueu2",
        amount=output_denom,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    external_output_script_pubkey = bytes.fromhex(
        "5120e0458118b80a08042d84c4f0356d86863fe2bffc034e839c166ad4e8da7e26ef"
    )

    internal_output = messages.TxOutputType(
        # tb1phkcspf88hge86djxgtwx2wu7ddghsw77d6sd7txtcxncu0xpx22shcydyf
        address_n=parse_path("m/10025h/1h/0h/1h/1/1"),
        amount=output_denom,
        script_type=messages.OutputScriptType.PAYTOTAPROOT,
    )
    internal_output_script_pubkey = bytes.fromhex(
        "5120bdb100a4e7ba327d364642dc653b9e6b51783bde6ea0df2ccbc1a78e3cc13295"
    )

    outputs = [internal_output] * own_output_count + [external_output] * (
        total_output_count - own_output_count
    )

    output_script_pubkeys = [internal_output_script_pubkey] * own_output_count + [
        external_output_script_pubkey
    ] * (total_output_count - own_output_count)

    coinjoin_req = make_coinjoin_request(
        "www.example.com",
        inputs,
        input_script_pubkeys,
        outputs,
        output_script_pubkeys,
        no_fee_indices=[],
    )

    start = time.time()
    with client:
        btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            coinjoin_request=coinjoin_req,
            preauthorized=True,
            serialize=False,
        )
    delay = time.time() - start
    assert delay <= max_expected_delay


def test_sign_tx_spend(client: Client):
    # NOTE: FAKE input tx

    inputs = [
        messages.TxInputType(
            address_n=parse_path("m/10025h/1h/0h/1h/1/0"),
            amount=7_289_000,
            prev_hash=FAKE_TXHASH_f982c0,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDTAPROOT,
        ),
    ]

    outputs = [
        # Our change output.
        messages.TxOutputType(
            # tb1pchruvduckkwuzm5hmytqz85emften5dnmkqu9uhfxwfywaqhuu0qjggqyp
            address_n=parse_path("m/10025h/1h/0h/1h/1/2"),
            amount=7_289_000 - 50_000 - 400,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
        # Payment output.
        messages.TxOutputType(
            address="mvbu1Gdy8SUjTenqerxUaZyYjmveZvt33q",
            amount=50_000,
            script_type=messages.OutputScriptType.PAYTOADDRESS,
        ),
    ]

    # Ensure that Trezor refuses to spend from CoinJoin without user authorization.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
        )

    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest,
                request_input(0),
                request_output(0),
                request_output(1),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            unlock_path=SLIP25_PATH,
        )

    # Transaction does not exist on the blockchain, not using assert_tx_matches()
    assert (
        serialized_tx.hex()
        == "010000000001010ab6ad3ba09261cfb4fa1d3680cb19332a8fe4d9de9ea89aa565bd83a2c082f90100000000ffffffff02c8736e0000000000225120c5c7c63798b59dc16e97d916011e99da5799d1b3dd81c2f2e93392477417e71e50c30000000000001976a914a579388225827d9f2fe9014add644487808c695d88ac014006bc29900d39570fca291c038551817430965ac6aa26f286483559e692a14a82cfaf8e57610eae12a5af05ee1e9600acb31de4757349c0e3066701aa78f65d2a00000000"
    )


def test_sign_tx_migration(client: Client):
    inputs = [
        messages.TxInputType(
            address_n=parse_path("m/84h/1h/3h/0/12"),
            amount=1_393,
            prev_hash=TXHASH_2cc3c1,
            prev_index=0,
            script_type=messages.InputScriptType.SPENDWITNESS,
            sequence=0xFFFFFFFD,
        ),
        messages.TxInputType(
            address_n=parse_path("m/84h/1h/3h/0/13"),
            amount=8_159,
            prev_hash=TXHASH_7f3a34,
            prev_index=1,
            script_type=messages.InputScriptType.SPENDWITNESS,
            sequence=0xFFFFFFFD,
        ),
    ]

    outputs = [
        # CoinJoin account.
        messages.TxOutputType(
            # tb1pl3y9gf7xk2ryvmav5ar66ra0d2hk7lhh9mmusx3qvn0n09kmaghqh32ru7
            address_n=parse_path("m/10025h/1h/0h/1h/0/0"),
            amount=1_393 + 8_159 - 190,
            script_type=messages.OutputScriptType.PAYTOTAPROOT,
        ),
    ]

    # Ensure that Trezor refuses to receive to CoinJoin path without the user first authorizing access to CoinJoin paths.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
        )

    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest,
                request_input(0),
                request_input(1),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_2cc3c1),
                request_input(0, TXHASH_2cc3c1),
                request_output(0, TXHASH_2cc3c1),
                request_input(1),
                request_meta(TXHASH_7f3a34),
                request_input(0, TXHASH_7f3a34),
                request_input(1, TXHASH_7f3a34),
                request_input(2, TXHASH_7f3a34),
                request_output(0, TXHASH_7f3a34),
                request_output(1, TXHASH_7f3a34),
                request_input(0),
                request_input(1),
                request_output(0),
                request_input(0),
                request_input(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client,
            "Testnet",
            inputs,
            outputs,
            prev_txes=TX_CACHE_TESTNET,
            unlock_path=SLIP25_PATH,
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://tbtc1.trezor.io/api/tx/3452d339045f8a35f2a083992b8f73d907f8da9653e89ee175022ca8a649b822",
        tx_hex="010000000001026ddaa8a504b743b36115e6226ceba177c03fadfee0f4cc4f7bcbb13fe3c1c32c0000000000fdffffff720f3a432316f24ba96ea9c90e77268db14208c089f3698068f3f90681343a7f0100000000fdffffff019224000000000000225120fc485427c6b286466faca747ad0faf6aaf6f7ef72ef7c81a2064df3796dbea2e0247304402202f325d6e3ac764bb9d38003bb11022c5317a59ad8a2513dcabe7af9b23ff7c9f022011ff8161d9ed8cf82667b2b44dbe2f4538d41d8b353d64a01338881bce8de3690121030968050bc0647e28c09616d642cc88ab075b01e40616b53e446e7f122218a9da02483045022100f462c32fd90bf92a1aa4ca9fdb2dd9b5ef9adad6990b9bc7f9ca583e8b72d72a02202a6d9c2a8749d65bdb62a0ec4de27bad5fb13e2ae40be86afb95a477b60a1609012103e4dbaaee8486b328dba46adeb9afc3a56237aa5ca43df24eb61b04e6ca00099300000000",
    )


def test_wrong_coordinator(client: Client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        coordinator="www.example.com",
        max_rounds=10,
        max_coordinator_fee_rate=500_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.org" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_wrong_account_type(client: Client):
    params = {
        "client": client,
        "coordinator": "www.example.com",
        "max_rounds": 10,
        "max_coordinator_fee_rate": 500_000,  # 0.5 %
        "max_fee_per_kvbyte": 3500,
        "coin_name": "Testnet",
    }

    # Ensure that Trezor accepts CoinJoin authorizations only for SLIP-0025 paths.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.authorize_coinjoin(
            **params,
            n=parse_path("m/86h/1h/0h"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    # Ensure that correct parameters succeed.
    btc.authorize_coinjoin(
        **params,
        n=parse_path("m/10025h/1h/0h/1h"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )


def test_cancel_authorization(client: Client):
    # Ensure that a preauthorized GetOwnershipProof fails if the commitment_data doesn't match the coordinator.

    btc.authorize_coinjoin(
        client,
        coordinator="www.example.com",
        max_rounds=10,
        max_coordinator_fee_rate=500_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    device.cancel_authorization(client)

    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x0fwww.example.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )


def test_get_public_key(client: Client):
    ACCOUNT_PATH = parse_path("m/10025h/1h/0h/1h")
    EXPECTED_XPUB = "tpubDEMKm4M3S2Grx5DHTfbX9et5HQb9KhdjDCkUYdH9gvVofvPTE6yb2MH52P9uc4mx6eFohUmfN1f4hhHNK28GaZnWRXr3b8KkfFcySo1SmXU"

    # Ensure that user cannot access SLIP-25 path without UnlockPath.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        resp = btc.get_public_node(
            client,
            ACCOUNT_PATH,
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDTAPROOT,
        )

    # Get unlock path MAC.
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest,
                messages.Failure(code=messages.FailureType.ActionCancelled),
            ]
        )
        unlock_path_mac = device.unlock_path(client, n=SLIP25_PATH)

    # Ensure that UnlockPath fails with invalid MAC.
    invalid_unlock_path_mac = bytes([unlock_path_mac[0] ^ 1]) + unlock_path_mac[1:]
    with pytest.raises(TrezorFailure, match="Invalid MAC"):
        resp = btc.get_public_node(
            client,
            ACCOUNT_PATH,
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDTAPROOT,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=invalid_unlock_path_mac,
        )

    # Ensure that user does not need to confirm access when path unlock is requested with MAC.
    with client:
        client.set_expected_responses(
            [
                messages.UnlockedPathRequest,
                messages.PublicKey,
            ]
        )
        resp = btc.get_public_node(
            client,
            ACCOUNT_PATH,
            coin_name="Testnet",
            script_type=messages.InputScriptType.SPENDTAPROOT,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )
        assert resp.xpub == EXPECTED_XPUB


def test_get_address(client: Client):
    # Ensure that the SLIP-0025 external chain is inaccessible without user confirmation.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/0/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
        )

    # Unlock CoinJoin path.
    with client:
        client.set_expected_responses(
            [
                messages.ButtonRequest(code=B.Other),
                messages.UnlockedPathRequest,
                messages.Failure(code=messages.FailureType.ActionCancelled),
            ]
        )
        unlock_path_mac = device.unlock_path(client, SLIP25_PATH)

    # Ensure that the SLIP-0025 external chain is accessible after user confirmation.
    for chunkify in (True, False):
        resp = btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/0/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
            chunkify=chunkify,
        )
        assert resp == "tb1pl3y9gf7xk2ryvmav5ar66ra0d2hk7lhh9mmusx3qvn0n09kmaghqh32ru7"

    resp = btc.get_address(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/0/1"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        show_display=False,
        unlock_path=SLIP25_PATH,
        unlock_path_mac=unlock_path_mac,
    )
    assert resp == "tb1p64rqq64rtt7eq6p0htegalcjl2nkjz64ur8xsclc59s5845jty7skp2843"

    # Ensure that the SLIP-0025 internal chain is inaccessible even with user authorization.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )

    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/1"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=False,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )

    # Ensure that another SLIP-0025 account is inaccessible with the same MAC.
    with pytest.raises(TrezorFailure, match="Forbidden key path"):
        btc.get_address(
            client,
            "Testnet",
            parse_path("m/10025h/1h/1h/1h/0/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            show_display=True,
            unlock_path=SLIP25_PATH,
            unlock_path_mac=unlock_path_mac,
        )


def test_multisession_authorization(client: Client):
    # Authorize CoinJoin with www.example1.com in session 1.
    btc.authorize_coinjoin(
        client,
        coordinator="www.example1.com",
        max_rounds=10,
        max_coordinator_fee_rate=500_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    # Open a second session.
    session_id1 = client.session_id
    client.init_device(new_session=True)

    # Authorize CoinJoin with www.example2.com in session 2.
    btc.authorize_coinjoin(
        client,
        coordinator="www.example2.com",
        max_rounds=10,
        max_coordinator_fee_rate=500_000,  # 0.5 %
        max_fee_per_kvbyte=3500,
        n=parse_path("m/10025h/1h/0h/1h"),
        coin_name="Testnet",
        script_type=messages.InputScriptType.SPENDTAPROOT,
    )

    # Requesting a preauthorized ownership proof for www.example1.com should fail in session 2.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Requesting a preauthorized ownership proof for www.example2.com should succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        user_confirmation=True,
        commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c0019010169d0c751442f4c9adacbd42987121d75b36e3932db217e5bb3784f368f5a4c5d00014097bb2f1f87aea1e809756a6f2ef84109613ccf1bf9b96ffb9305b6193b3942510a8650693ca8af74f0f63401baa384d0c0f7188f1d2df56b91362646c82223a8"
    )

    # Switch back to the first session.
    session_id2 = client.session_id
    client.init_device(session_id=session_id1)

    # Requesting a preauthorized ownership proof for www.example1.com should succeed in session 1.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        user_confirmation=True,
        commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )

    assert (
        ownership_proof.hex()
        == "534c0019010169d0c751442f4c9adacbd42987121d75b36e3932db217e5bb3784f368f5a4c5d00014078fefa8243283cd575c885f97fd2e3405c934ab4d3e415ff5fe27d49f347bbb592e03ff6195f46c94a592799748c8dd7daea8b3fc4b2011b7e58a74ee296853b"
    )

    # Requesting a preauthorized ownership proof for www.example2.com should fail in session 1.
    with pytest.raises(TrezorFailure, match="Unauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Cancel the authorization in session 1.
    device.cancel_authorization(client)

    # Requesting a preauthorized ownership proof should fail now.
    with pytest.raises(TrezorFailure, match="No preauthorized operation"):
        ownership_proof, _ = btc.get_ownership_proof(
            client,
            "Testnet",
            parse_path("m/10025h/1h/0h/1h/1/0"),
            script_type=messages.InputScriptType.SPENDTAPROOT,
            user_confirmation=True,
            commitment_data=b"\x10www.example1.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
            preauthorized=True,
        )

    # Switch to the second session.
    client.init_device(session_id=session_id2)

    # Requesting a preauthorized ownership proof for www.example2.com should still succeed in session 2.
    ownership_proof, _ = btc.get_ownership_proof(
        client,
        "Testnet",
        parse_path("m/10025h/1h/0h/1h/1/0"),
        script_type=messages.InputScriptType.SPENDTAPROOT,
        user_confirmation=True,
        commitment_data=b"\x10www.example2.com" + (1).to_bytes(ROUND_ID_LEN, "big"),
        preauthorized=True,
    )
