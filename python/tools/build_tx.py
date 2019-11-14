#!/usr/bin/env python3
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

import json
import sys

import click

from trezorlib import coins, messages, tools
from trezorlib.cli import ChoiceType
from trezorlib.cli.btc import INPUT_SCRIPTS, OUTPUT_SCRIPTS
from trezorlib.protobuf import to_dict


def echo(*args, **kwargs):
    return click.echo(*args, err=True, **kwargs)


def prompt(*args, **kwargs):
    return click.prompt(*args, err=True, **kwargs)


def _default_script_type(address_n, script_types):
    script_type = "address"

    if address_n is None:
        pass
    elif address_n[0] == tools.H_(49):
        script_type = "p2shsegwit"
    elif address_n[0] == tools.H_(84):
        script_type = "segwit"

    return script_type
    # return script_types[script_type]


def parse_vin(s):
    txid, vout = s.split(":")
    return bytes.fromhex(txid), int(vout)


def _get_inputs_interactive(coin_data, txapi):
    inputs = []
    txes = {}
    while True:
        echo()
        prev = prompt(
            "Previous output to spend (txid:vout)", type=parse_vin, default=""
        )
        if not prev:
            break
        prev_hash, prev_index = prev
        address_n = prompt("BIP-32 path to derive the key", type=tools.parse_path)
        try:
            tx = txapi[prev_hash]
            txes[prev_hash] = tx
            amount = tx.bin_outputs[prev_index].amount
            echo("Prefilling input amount: {}".format(amount))
        except Exception as e:
            print(e)
            echo("Failed to fetch transation. This might bite you later.")
            amount = prompt("Input amount (satoshis)", type=int, default=0)

        sequence = prompt(
            "Sequence Number to use (RBF opt-in enabled by default)",
            type=int,
            default=0xFFFFFFFD,
        )
        script_type = prompt(
            "Input type",
            type=ChoiceType(INPUT_SCRIPTS),
            default=_default_script_type(address_n, INPUT_SCRIPTS),
        )
        if isinstance(script_type, str):
            script_type = INPUT_SCRIPTS[script_type]

        new_input = messages.TxInputType(
            address_n=address_n,
            prev_hash=prev_hash,
            prev_index=prev_index,
            amount=amount,
            script_type=script_type,
            sequence=sequence,
        )
        if coin_data["bip115"]:
            prev_output = txapi.get_tx(prev_hash.hex()).bin_outputs[prev_index]
            new_input.prev_block_hash_bip115 = prev_output.block_hash
            new_input.prev_block_height_bip115 = prev_output.block_height

        inputs.append(new_input)

    return inputs, txes


def _get_outputs_interactive():
    outputs = []
    while True:
        echo()
        address = prompt("Output address (for non-change output)", default="")
        if address:
            address_n = None
            script_type = messages.OutputScriptType.PAYTOADDRESS
        else:
            address = None
            address_n = prompt(
                "BIP-32 path (for change output)", type=tools.parse_path, default=""
            )
            if not address_n:
                break
            script_type = prompt(
                "Output type",
                type=ChoiceType(OUTPUT_SCRIPTS),
                default=_default_script_type(address_n, OUTPUT_SCRIPTS),
            )
            if isinstance(script_type, str):
                script_type = OUTPUT_SCRIPTS[script_type]

        amount = prompt("Amount to spend (satoshis)", type=int)

        outputs.append(
            messages.TxOutputType(
                address_n=address_n,
                address=address,
                amount=amount,
                script_type=script_type,
            )
        )

    return outputs


@click.command()
def sign_interactive():
    coin = prompt("Coin name", default="Bitcoin")
    if coin in coins.tx_api:
        coin_data = coins.by_name[coin]
        txapi = coins.tx_api[coin]
    else:
        echo('Coin "%s" is not recognized.' % coin, err=True)
        echo("Supported coin types: %s" % ", ".join(coins.tx_api.keys()), err=True)
        sys.exit(1)

    inputs, txes = _get_inputs_interactive(coin_data, txapi)
    outputs = _get_outputs_interactive()

    if coin_data["bip115"]:
        current_block_height = txapi.current_height()
        # Zencash recommendation for the better protection
        block_height = current_block_height - 300
        block_hash = txapi.get_block_hash(block_height)
        # Blockhash passed in reverse order
        block_hash = block_hash[::-1]

        for output in outputs:
            output.block_hash_bip115 = block_hash
            output.block_height_bip115 = block_height

    signtx = messages.SignTx()
    signtx.version = prompt("Transaction version", type=int, default=2)
    signtx.lock_time = prompt("Transaction locktime", type=int, default=0)
    if coin == "Capricoin":
        signtx.timestamp = prompt("Transaction timestamp", type=int)

    result = {
        "coin_name": coin,
        "inputs": [to_dict(i, hexlify_bytes=True) for i in inputs],
        "outputs": [to_dict(o, hexlify_bytes=True) for o in outputs],
        "details": to_dict(signtx, hexlify_bytes=True),
        "prev_txes": {
            txhash.hex(): to_dict(txdata, hexlify_bytes=True)
            for txhash, txdata in txes.items()
        },
    }

    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    sign_interactive()
