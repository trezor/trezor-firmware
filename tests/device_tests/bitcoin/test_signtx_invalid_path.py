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

from trezorlib import btc, device, messages
from trezorlib.exceptions import TrezorFailure
from trezorlib.tools import H_, parse_path

from ...tx_cache import TxCache
from ..signtx import request_finished, request_input, request_meta, request_output

B = messages.ButtonRequestType
TX_CACHE_MAINNET = TxCache("Bitcoin")
TX_CACHE_BCASH = TxCache("Bcash")

TXHASH_8cc1f4 = bytes.fromhex(
    "8cc1f4adf7224ce855cf535a5104594a0004cb3b640d6714fdb00b9128832dd5"
)
TXHASH_d5f65e = bytes.fromhex(
    "d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882"
)
TXHASH_fa80a9 = bytes.fromhex(
    "fa80a9949f1094119195064462f54d0e0eabd3139becd4514ae635b8c7fe3a46"
)
TXHASH_5dfd1b = bytes.fromhex(
    "5dfd1b037633adc7f84a17b2df31c9994fe50b3ab3e246c44c4ceff3d326f62e"
)


# Adapted from TestMsgSigntx.test_one_one_fee,
# only changed the coin from Bitcoin to Litecoin.
# Litecoin does not have strong replay protection using SIGHASH_FORKID,
# spending from Bitcoin path should fail.
@pytest.mark.altcoin
def test_invalid_path_fail(client):
    # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
    # input 0: 0.0039 BTC

    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/0"),
        amount=390000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 by changing the version
    out1 = messages.TxOutputType(
        address="LfWz9wLHmqU9HoDkMg9NqbRosrHvEixeVZ",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    with pytest.raises(TrezorFailure) as exc:
        btc.sign_tx(client, "Litecoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)

    assert exc.value.code == messages.FailureType.DataError
    assert exc.value.message.endswith("Forbidden key path")


# Adapted from TestMsgSigntx.test_one_one_fee,
# only changed the coin from Bitcoin to Litecoin and set safety checks to prompt.
# Litecoin does not have strong replay protection using SIGHASH_FORKID, but
# spending from Bitcoin path should pass with safety checks set to prompt.
@pytest.mark.altcoin
def test_invalid_path_prompt(client):
    # tx: d5f65ee80147b4bcc70b75e4bbf2d7382021b871bd8867ef8fa525ef50864882
    # input 0: 0.0039 BTC

    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/0"),
        amount=390000,
        prev_hash=TXHASH_d5f65e,
        prev_index=0,
    )

    # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 by changing the version
    out1 = messages.TxOutputType(
        address="LfWz9wLHmqU9HoDkMg9NqbRosrHvEixeVZ",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    device.apply_settings(
        client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
    )

    btc.sign_tx(client, "Litecoin", [inp1], [out1], prev_txes=TX_CACHE_MAINNET)


# Adapted from TestMsgSigntx.test_one_one_fee,
# only changed the coin from Bitcoin to Bcash.
# Bcash does have strong replay protection using SIGHASH_FORKID,
# spending from Bitcoin path should work.
@pytest.mark.altcoin
def test_invalid_path_pass_forkid(client):
    # tx: 8cc1f4adf7224ce855cf535a5104594a0004cb3b640d6714fdb00b9128832dd5
    # input 0: 0.0039 BTC

    inp1 = messages.TxInputType(
        address_n=parse_path("44h/0h/0h/0/0"),
        amount=390000,
        prev_hash=TXHASH_8cc1f4,
        prev_index=0,
    )

    # address is converted from 1MJ2tj2ThBE62zXbBYA5ZaN3fdve5CPAz1 to cashaddr format
    out1 = messages.TxOutputType(
        address="bitcoincash:qr0fk25d5zygyn50u5w7h6jkvctas52n0qxff9ja6r",
        amount=390000 - 10000,
        script_type=messages.OutputScriptType.PAYTOADDRESS,
    )

    btc.sign_tx(client, "Bcash", [inp1], [out1], prev_txes=TX_CACHE_BCASH)


def test_attack_path_segwit(client):
    # Scenario: The attacker falsely claims that the transaction uses Testnet paths to
    # avoid the path warning dialog, but in step6_sign_segwit_inputs() uses Bitcoin paths
    # to get a valid signature.

    device.apply_settings(
        client, safety_checks=messages.SafetyCheckLevel.PromptTemporarily
    )

    inp1 = messages.TxInputType(
        # The actual input that the attcker wants to get signed.
        address_n=parse_path("84'/0'/0'/0/0"),
        amount=9426,
        prev_hash=TXHASH_fa80a9,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )
    inp2 = messages.TxInputType(
        # The actual input that the attcker wants to get signed.
        # We need this one to be from a different account, so that the match checker
        # allows the transaction to pass.
        address_n=parse_path("84'/0'/1'/0/1"),
        amount=7086,
        prev_hash=TXHASH_5dfd1b,
        prev_index=0,
        script_type=messages.InputScriptType.SPENDWITNESS,
    )

    out1 = messages.TxOutputType(
        # Attacker's Mainnet address encoded as Testnet.
        address="tb1q694ccp5qcc0udmfwgp692u2s2hjpq5h407urtu",
        script_type=messages.OutputScriptType.PAYTOADDRESS,
        amount=9426 + 7086 - 500,
    )

    attack_count = 6

    def attack_processor(msg):
        nonlocal attack_count
        # Make the inputs look like they are coming from Testnet paths until we reach the
        # signing phase.
        if attack_count > 0 and msg.tx.inputs and msg.tx.inputs[0] in (inp1, inp2):
            attack_count -= 1
            msg.tx.inputs[0].address_n[1] = H_(1)

        return msg

    with client:
        client.set_filter(messages.TxAck, attack_processor)
        client.set_expected_responses(
            [
                # Step: process inputs
                request_input(0),
                # Attacker bypasses warning about non-standard path.
                request_input(1),
                # Attacker bypasses warning about non-standard path.
                # Step: approve outputs
                request_output(0),
                messages.ButtonRequest(code=B.ConfirmOutput),
                messages.ButtonRequest(code=B.SignTx),
                # Step: verify inputs
                request_input(0),
                request_meta(TXHASH_fa80a9),
                request_input(0, TXHASH_fa80a9),
                request_output(0, TXHASH_fa80a9),
                request_output(1, TXHASH_fa80a9),
                request_input(1),
                request_meta(TXHASH_5dfd1b),
                request_input(0, TXHASH_5dfd1b),
                request_output(0, TXHASH_5dfd1b),
                request_output(1, TXHASH_5dfd1b),
                # Step: serialize inputs
                request_input(0),
                request_input(1),
                # Step: serialize outputs
                request_output(0),
                # Step: sign segwit inputs
                request_input(0),
                # Trezor must warn about non-standard path before signing.
                messages.ButtonRequest(code=B.UnknownDerivationPath),
                request_input(1),
                # Trezor must warn about non-standard path before signing.
                messages.ButtonRequest(code=B.UnknownDerivationPath),
                request_finished(),
            ]
        )

        btc.sign_tx(client, "Testnet", [inp1, inp2], [out1], prev_txes=TX_CACHE_MAINNET)
