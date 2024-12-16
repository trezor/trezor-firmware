# This file is part of the Trezor project.
#
# Copyright (C) 2012-2024 SatoshiLabs and contributors
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
from trezorlib.debuglink import TrezorClientDebugLink as Client
from trezorlib.tools import parse_path

from ...common import is_core
from ...tx_cache import TxCache
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

TXHASH_0dac36 = bytes.fromhex(
    "0dac366fd8a67b2a89fbb0d31086e7acded7a5bbf9ef9daa935bc873229ef5b5"
)

def test_contact_label_address(client: Client):
    # Using a receive address with label directly
    receive_address = "13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7"
    label = "Test Label"
    label_message = label + "/" + receive_address
    label_sig = btc.sign_message(
      client,
      "Testnet",
      parse_path("m/44h/1h/0h/0/0"),
      label_message
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address=receive_address,
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        label=label,
        label_sig=label_sig.signature,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_0dac36),
                request_input(0, TXHASH_0dac36),
                request_output(0, TXHASH_0dac36),
                request_output(1, TXHASH_0dac36),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/b893aeed4b12227b6f5348d7f6cb84ba2cda2ba70a41933a25f363b9d2fc2cf9",
        tx_hex="0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006b483045022100dd4dd136a70371bc9884c3c51fd52f4aed9ab8ee98f3ac7367bb19e6538096e702200c56be09c4359fc7eb494b4bdf8f2b72706b0575c4021373345b593e9661c7b6012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0148c40000000000001976a91419140511436e947448be994ab7fda9f98623e68e88ac00000000",
    )

def test_contact_label_pubkey(client: Client):
    # Using a pubkey with label + receive address signed by the pubkey
    receive_address = "13Hbso8zgV5Wmqn3uA7h3QVtmPzs47wcJ7"
    label_pk = btc.get_address(client, "Testnet", parse_path("m/44h/1h/0h/0/0"))

    contact_pubkey = btc.sign_message(
      client,
      "Testnet",
      parse_path("m/44h/1h/0h/0/0"),
      receive_address
    )

    label = "Test Label"
    label_message = label + "/" + label_pk
    label_sig = btc.sign_message(
      client,
      "Testnet",
      parse_path("m/44h/1h/0h/0/0"),
      label_message
    )

    inp1 = messages.TxInputType(
        address_n=parse_path("m/44h/0h/5h/0/9"),  # 1H2CRJBrDMhkvCGZMW7T4oQwYbL8eVuh7p
        amount=63_988,
        prev_hash=TXHASH_0dac36,
        prev_index=0,
    )

    out1 = messages.TxOutputType(
        address=receive_address,
        amount=50_248,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        label=label,
        label_sig=label_sig.signature,
        label_pk=label_pk,
        address_pk_sig=contact_pubkey.signature,
    )

    with client:
        client.set_expected_responses(
            [
                request_input(0),
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                (is_core(client), messages.ButtonRequest(code=B.ConfirmOutput)),
                messages.ButtonRequest(code=B.SignTx),
                request_input(0),
                request_meta(TXHASH_0dac36),
                request_input(0, TXHASH_0dac36),
                request_output(0, TXHASH_0dac36),
                request_output(1, TXHASH_0dac36),
                request_input(0),
                request_output(0),
                request_output(0),
                request_finished(),
            ]
        )

        _, serialized_tx = btc.sign_tx(
            client, "Bitcoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET
        )

    assert_tx_matches(
        serialized_tx,
        hash_link="https://btc1.trezor.io/api/tx/b893aeed4b12227b6f5348d7f6cb84ba2cda2ba70a41933a25f363b9d2fc2cf9",
        tx_hex="0100000001b5f59e2273c85b93aa9deff9bba5d7deace78610d3b0fb892a7ba6d86f36ac0d000000006b483045022100dd4dd136a70371bc9884c3c51fd52f4aed9ab8ee98f3ac7367bb19e6538096e702200c56be09c4359fc7eb494b4bdf8f2b72706b0575c4021373345b593e9661c7b6012103d7f3a07085bee09697cf03125d5c8760dfed65403dba787f1d1d8b1251af2cbeffffffff0148c40000000000001976a91419140511436e947448be994ab7fda9f98623e68e88ac00000000",
    )
