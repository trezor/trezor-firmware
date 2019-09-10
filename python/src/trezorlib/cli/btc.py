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

import base64
import json
import sys

import click

from .. import btc, coins, messages, protobuf, tools
from . import ChoiceType

INPUT_SCRIPTS = {
    "address": messages.InputScriptType.SPENDADDRESS,
    "segwit": messages.InputScriptType.SPENDWITNESS,
    "p2shsegwit": messages.InputScriptType.SPENDP2SHWITNESS,
}

OUTPUT_SCRIPTS = {
    "address": messages.OutputScriptType.PAYTOADDRESS,
    "segwit": messages.OutputScriptType.PAYTOWITNESS,
    "p2shsegwit": messages.OutputScriptType.PAYTOP2SHWITNESS,
}

DEFAULT_COIN = "Bitcoin"


@click.group(name="btc")
def cli():
    """Bitcoin and Bitcoin-like coins commands."""


#
# Address functions
#


@cli.command()
@click.option("-c", "--coin")
@click.option("-n", "--address", required=True, help="BIP-32 path")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS), default="address")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_address(connect, coin, address, script_type, show_display):
    """Get address for specified path."""
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)
    return btc.get_address(
        connect(), coin, address_n, show_display, script_type=script_type
    )


@cli.command()
@click.option("-c", "--coin")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'")
@click.option("-e", "--curve")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS), default="address")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_public_node(connect, coin, address, curve, script_type, show_display):
    """Get public node of given path."""
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)
    result = btc.get_public_node(
        connect(),
        address_n,
        ecdsa_curve_name=curve,
        show_display=show_display,
        coin_name=coin,
        script_type=script_type,
    )
    return {
        "node": {
            "depth": result.node.depth,
            "fingerprint": "%08x" % result.node.fingerprint,
            "child_num": result.node.child_num,
            "chain_code": result.node.chain_code.hex(),
            "public_key": result.node.public_key.hex(),
        },
        "xpub": result.xpub,
    }


#
# Signing functions
#


@cli.command()
@click.option("-c", "--coin")
@click.argument("json_file", type=click.File(), required=False)
@click.pass_obj
def sign_tx(connect, coin, json_file):
    """Sign transaction."""
    client = connect()
    coin = coin or DEFAULT_COIN

    if json_file is None:
        return _sign_interactive(client, coin)

    data = json.load(json_file)
    coin = data.get("coin_name", coin)
    details = protobuf.dict_to_proto(messages.SignTx, data.get("details", {}))
    inputs = [
        protobuf.dict_to_proto(messages.TxInputType, i) for i in data.get("inputs", ())
    ]
    outputs = [
        protobuf.dict_to_proto(messages.TxOutputType, output)
        for output in data.get("outputs", ())
    ]
    prev_txes = {
        bytes.fromhex(txid): protobuf.dict_to_proto(messages.TransactionType, tx)
        for txid, tx in data.get("prev_txes", {}).items()
    }

    _, serialized_tx = btc.sign_tx(client, coin, inputs, outputs, details, prev_txes)

    click.echo()
    click.echo("Signed Transaction:")
    click.echo(serialized_tx.hex())


#
# Message functions
#


@cli.command()
@click.option("-c", "--coin")
@click.option("-n", "--address", required=True, help="BIP-32 path")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS), default="address")
@click.argument("message")
@click.pass_obj
def sign_message(connect, coin, address, message, script_type):
    """Sign message using address of given path."""
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)
    res = btc.sign_message(connect(), coin, address_n, message, script_type)
    return {
        "message": message,
        "address": res.address,
        "signature": base64.b64encode(res.signature).decode(),
    }


@cli.command()
@click.option("-c", "--coin")
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def verify_message(connect, coin, address, signature, message):
    """Verify message."""
    signature = base64.b64decode(signature)
    coin = coin or DEFAULT_COIN
    return btc.verify_message(connect(), coin, address, signature, message)


#
# deprecated interactive signing
# ALL BELOW is legacy code and will be dropped


def _default_script_type(address_n, script_types):
    script_type = "address"

    if address_n is None:
        pass
    elif address_n[0] == tools.H_(49):
        script_type = "p2shsegwit"
    elif address_n[0] == tools.H_(84):
        script_type = "segwit"

    return script_types[script_type]


def _get_inputs_interactive(coin_data, txapi):
    def outpoint(s):
        txid, vout = s.split(":")
        return bytes.fromhex(txid), int(vout)

    inputs = []
    txes = {}
    while True:
        click.echo()
        prev = click.prompt(
            "Previous output to spend (txid:vout)", type=outpoint, default=""
        )
        if not prev:
            break
        prev_hash, prev_index = prev
        address_n = click.prompt("BIP-32 path to derive the key", type=tools.parse_path)
        try:
            tx = txapi[prev_hash]
            txes[prev_hash] = tx
            amount = tx.bin_outputs[prev_index].amount
            click.echo("Prefilling input amount: {}".format(amount))
        except Exception as e:
            print(e)
            click.echo("Failed to fetch transation. This might bite you later.")
            amount = click.prompt("Input amount (satoshis)", type=int, default=0)

        sequence = click.prompt(
            "Sequence Number to use (RBF opt-in enabled by default)",
            type=int,
            default=0xFFFFFFFD,
        )
        script_type = click.prompt(
            "Input type",
            type=ChoiceType(INPUT_SCRIPTS),
            default=_default_script_type(address_n, INPUT_SCRIPTS),
        )

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
        click.echo()
        address = click.prompt("Output address (for non-change output)", default="")
        if address:
            address_n = None
        else:
            address = None
            address_n = click.prompt(
                "BIP-32 path (for change output)", type=tools.parse_path, default=""
            )
            if not address_n:
                break
        amount = click.prompt("Amount to spend (satoshis)", type=int)
        script_type = click.prompt(
            "Output type",
            type=ChoiceType(OUTPUT_SCRIPTS),
            default=_default_script_type(address_n, OUTPUT_SCRIPTS),
        )
        outputs.append(
            messages.TxOutputType(
                address_n=address_n,
                address=address,
                amount=amount,
                script_type=script_type,
            )
        )

    return outputs


def _sign_interactive(client, coin):
    click.echo("Warning: interactive sign-tx mode is deprecated.", err=True)
    click.echo(
        "Instead, you should format your transaction data as JSON and "
        "supply the file as an argument to sign-tx",
        err=True,
    )
    if coin in coins.tx_api:
        coin_data = coins.by_name[coin]
        txapi = coins.tx_api[coin]
    else:
        click.echo('Coin "%s" is not recognized.' % coin, err=True)
        click.echo(
            "Supported coin types: %s" % ", ".join(coins.tx_api.keys()), err=True
        )
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
    signtx.version = click.prompt("Transaction version", type=int, default=2)
    signtx.lock_time = click.prompt("Transaction locktime", type=int, default=0)
    if coin == "Capricoin":
        signtx.timestamp = click.prompt("Transaction timestamp", type=int)

    _, serialized_tx = btc.sign_tx(
        client, coin, inputs, outputs, details=signtx, prev_txes=txes
    )

    click.echo()
    click.echo("Signed Transaction:")
    click.echo(serialized_tx.hex())
    click.echo()
    click.echo("Use the following form to broadcast it to the network:")
    click.echo(txapi.pushtx_url)
