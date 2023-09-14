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
from trezorlib.tools import H_, parse_path, tx_hash

from ...tx_cache import TxCache
from .signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_API = TxCache("Bgold")

TXHASH_aade05 = bytes.fromhex(
    "aade0536c655334908e677204742f06092fc9dad30f7b98b0c7a51090e7fa8a9"
)
FAKE_TXHASH_7f1f6b = bytes.fromhex(
    "7f1f6bfe8d5a23e038c58bdcf47e6eb3b5ddb93300176b273564951105206b39"
)
FAKE_TXHASH_db7239 = bytes.fromhex(
    "db7239c358352c10996115b3de9e3f37ea0a97be4ea8c4b9e08996e257a21d0e"
)
FAKE_TXHASH_6f0398 = bytes.fromhex(
    "6f0398f8bac639312afc2e40210ce5253535f92326167f40e1f38dd7047b00ec"
)
FAKE_TXHASH_aae50f = bytes.fromhex(
    "aae50f8dc1c19c35517e5bbc2214d38e1ce4b4ff7cb3151b5b31bf0f723f8e06"
)
FAKE_TXHASH_a63dbe = bytes.fromhex(
    "a63dbedd8cd284bf0d3c468e84b9b0eeb14c3a08824eab8f80e7723a299f30db"
)

pytestmark = [pytest.mark.altcoin, pytest.mark.skip_tr]


# All data taken from T1
def test_send_bitcoin_gold_change(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/156h/0h/0/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_6f0398,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/156h/0h/1/0"),
        amount=1_896_050,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=1_252_382_934 - 1_896_050 - 1_000,
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
                request_meta(FAKE_TXHASH_6f0398),
                request_input(0, FAKE_TXHASH_6f0398),
                request_output(0, FAKE_TXHASH_6f0398),
                request_output(1, FAKE_TXHASH_6f0398),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "58fccf99181283bbde5f2634fed0bff490a02df0b61bf50742a0437107d13f54"
    )


def test_send_bitcoin_gold_nochange(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/156h/0h/0/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_6f0398,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/44h/156h/0h/0/1"),
        # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
        amount=38_448_607,
        prev_hash=FAKE_TXHASH_aae50f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=1_252_382_934 + 38_448_607 - 1_000,
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
                request_meta(FAKE_TXHASH_6f0398),
                request_input(0, FAKE_TXHASH_6f0398),
                request_output(0, FAKE_TXHASH_6f0398),
                request_output(1, FAKE_TXHASH_6f0398),
                request_input(1),
                request_meta(FAKE_TXHASH_aae50f),
                request_input(0, FAKE_TXHASH_aae50f),
                request_input(1, FAKE_TXHASH_aae50f),
                request_output(0, FAKE_TXHASH_aae50f),
                request_input(0),
                request_input(1),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "77b595d25ed2a4d08fee9e9219e48def9f26f3e0945fd370c445aba5b72888d4"
    )


def test_attack_change_input(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/156h/0h/0/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_6f0398,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    out1 = messages.TxOutputType(
        address_n=parse_path("m/44h/156h/0h/1/0"),
        amount=1_896_050,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=1_252_382_934 - 1_896_050 - 1_000,
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
                request_meta(FAKE_TXHASH_6f0398),
                request_input(0, FAKE_TXHASH_6f0398),
                request_output(0, FAKE_TXHASH_6f0398),
                request_output(1, FAKE_TXHASH_6f0398),
                request_input(0),
                messages.Failure(code=messages.FailureType.ProcessError),
            ]
        )
        with pytest.raises(TrezorFailure):
            btc.sign_tx(client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API)


@pytest.mark.multisig
def test_send_btg_multisig_change(client: Client):
    # NOTE: fake input tx used

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/48h/156h/{i}h/0h"), coin_name="Bgold"
        ).node
        for i in range(1, 4)
    ]

    EMPTY_SIGS = [b"", b"", b""]

    def getmultisig(chain, nr, signatures):
        return messages.MultisigRedeemScriptType(
            nodes=nodes, address_n=[chain, nr], signatures=signatures, m=2
        )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/156h/3h/0h/0/0"),
        multisig=getmultisig(0, 0, EMPTY_SIGS),
        # 33Ju286QvonBz5N1V754ZekQv4GLJqcc5R
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_a63dbe,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDMULTISIG,
    )
    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=24_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/48h/156h/3h/0h/1/0"),
        multisig=getmultisig(1, 0, EMPTY_SIGS),
        script_type=messages.OutputScriptType.PAYTOMULTISIG,
        amount=1_252_382_934 - 24_000 - 1_000,
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
                request_meta(FAKE_TXHASH_a63dbe),
                request_input(0, FAKE_TXHASH_a63dbe),
                request_output(0, FAKE_TXHASH_a63dbe),
                request_output(1, FAKE_TXHASH_a63dbe),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        signatures, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        signatures[0].hex()
        == "3045022100bb9b465d2bd7a22b17adc4d8c4600282cfaced0469969f32a2d85e152a528074022030a3698f460c7c935c284f4ffa97d6e44afc200b0c38319d259d15d3deb7c5ac"
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/48h/156h/1h/0h/0/0"),
        multisig=getmultisig(0, 0, [b"", b"", signatures[0]]),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_a63dbe,
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
                request_meta(FAKE_TXHASH_a63dbe),
                request_input(0, FAKE_TXHASH_a63dbe),
                request_output(0, FAKE_TXHASH_a63dbe),
                request_output(1, FAKE_TXHASH_a63dbe),
                request_input(0),
                request_output(0),
                request_output(1),
                request_finished(),
            ]
        )
        signatures, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        signatures[0].hex()
        == "30440220093c9b193883cd50e81668eb80efe6f82faf01ea707c16c4c33ce1eb40419ccf02200c81b328991389b53a04fcc091365bcc71c2a5c17f62982240b39f1bdefb91f7"
    )
    assert (
        tx_hash(serialized_tx).hex()
        == "e5f0bea13c61bf0d02972bbe66f4ca107abd13803015aa785f013114ecec55b7"
    )


def test_send_p2sh(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/156h/0h/1/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_db7239,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address="GZFLExxrvWFuFT1xRzhfwQWSE2bPDedBfn",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=1_252_382_934 - 11_000 - 12_300_000,
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
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_db7239),
                request_input(0, FAKE_TXHASH_db7239),
                request_output(0, FAKE_TXHASH_db7239),
                request_output(1, FAKE_TXHASH_db7239),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "fe743152e9480c1e12df378d012fb969a9b97f605c25cda98f08ed6c2e418dbf"
    )


def test_send_p2sh_witness_change(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/156h/0h/1/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_db7239,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=12_300_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )
    out2 = messages.TxOutputType(
        address_n=parse_path("m/49h/156h/0h/1/0"),
        script_type=messages.OutputScriptType.PAYTOP2SHWITNESS,
        amount=1_252_382_934 - 11_000 - 12_300_000,
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
                request_meta(FAKE_TXHASH_db7239),
                request_input(0, FAKE_TXHASH_db7239),
                request_output(0, FAKE_TXHASH_db7239),
                request_output(1, FAKE_TXHASH_db7239),
                request_input(0),
                request_output(0),
                request_output(1),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1], [out1, out2], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "b891b4aacfe2b7d7fc7653f617faac305aeab336a73ec57b3604ede71db598d6"
    )


@pytest.mark.multisig
def test_send_multisig_1(client: Client):
    # NOTE: fake input tx used

    nodes = [
        btc.get_public_node(
            client, parse_path(f"m/49h/156h/{i}h"), coin_name="Bgold"
        ).node
        for i in range(1, 4)
    ]
    multisig = messages.MultisigRedeemScriptType(
        nodes=nodes, address_n=[1, 0], signatures=[b"", b"", b""], m=2
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/49h/156h/1h/1/0"),
        prev_hash=FAKE_TXHASH_7f1f6b,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
        multisig=multisig,
        amount=1_252_382_934,
    )

    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=1_252_382_934 - 1_000,
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
                request_meta(FAKE_TXHASH_7f1f6b),
                request_input(0, FAKE_TXHASH_7f1f6b),
                request_output(0, FAKE_TXHASH_7f1f6b),
                request_output(1, FAKE_TXHASH_7f1f6b),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        signatures, _ = btc.sign_tx(client, "Bgold", [inp1], [out1], prev_txes=TX_API)
        # store signature
        inp1.multisig.signatures[0] = signatures[0]
        # sign with third key
        inp1.address_n[2] = H_(3)
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core, messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(FAKE_TXHASH_7f1f6b),
                request_input(0, FAKE_TXHASH_7f1f6b),
                request_output(0, FAKE_TXHASH_7f1f6b),
                request_output(1, FAKE_TXHASH_7f1f6b),
                request_input(0),
                request_output(0),
                request_input(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1], [out1], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "98e87ee2b5254e9346f2768993950dbfc3a3a4bd084983d0fb78337f1deeca3c"
    )


def test_send_mixed_inputs(client: Client):
    # NOTE: fake input tx used
    # First is non-segwit, second is segwit.

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/156h/0h/0/1"),
        # 1LRspCZNFJcbuNKQkXgHMDucctFRQya5a3
        amount=38_448_607,
        prev_hash=FAKE_TXHASH_aae50f,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    inp2 = messages.TxInputType(
        address_n=parse_path("m/49h/156h/0h/1/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_db7239,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDP2SHWITNESS,
    )
    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=38_448_607 + 1_252_382_934 - 1_000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with client:
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "52b17dc977c51eac75b330fe071ebcae8adde73437e3612e7b9bb501b00df840"
    )


@pytest.mark.skip_t1
def test_send_btg_external_presigned(client: Client):
    # NOTE: fake input tx used

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/156h/0h/0/0"),
        amount=1_252_382_934,
        prev_hash=FAKE_TXHASH_6f0398,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDADDRESS,
    )
    inp2 = messages.TxInputType(
        # address_n=parse_path("49'/156'/0'/0/0"),
        amount=58_456,
        prev_hash=TXHASH_aade05,
        prev_index=0,
        script_type=messages.InputScriptType.EXTERNAL,
        script_pubkey=bytes.fromhex(
            "76a9147c5edda9b293db2c8894b9d81efd77764910c44588ac"
        ),
        script_sig=bytes.fromhex(
            "4830450221008fb6fe8913178f2a3ab6fad1665c99a9ea0b7f5d4c079208dfc0a6d528a6d2f602206b2cd948bc367caec7da7c0806fe640a55fe8005979cadc4d414b1590109226141210386789a34fe1a49bfc3e174adc6706c6222b0d80de76b884a0e3d32f8e9c4dc3e"
        ),
    )
    out1 = messages.TxOutputType(
        address="GfDB1tvjfm3bukeoBTtfNqrJVFohS2kCTe",
        amount=1_252_382_934 + 58_456 - 1_000,
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
                request_meta(FAKE_TXHASH_6f0398),
                request_input(0, FAKE_TXHASH_6f0398),
                request_output(0, FAKE_TXHASH_6f0398),
                request_output(1, FAKE_TXHASH_6f0398),
                request_input(1),
                request_meta(TXHASH_aade05),
                request_input(0, TXHASH_aade05),
                request_output(0, TXHASH_aade05),
                request_output(1, TXHASH_aade05),
                request_input(0),
                request_input(1),
                request_output(0),
                request_finished(),
            ]
        )
        _, serialized_tx = btc.sign_tx(
            client, "Bgold", [inp1, inp2], [out1], prev_txes=TX_API
        )

    assert (
        tx_hash(serialized_tx).hex()
        == "3265a374759499b2043cf8ce57d11cf7ad35999bc5c470daa45eafef9c2ba2f2"
    )
