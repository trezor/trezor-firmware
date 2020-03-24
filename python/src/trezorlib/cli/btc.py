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

import click

from .. import btc, messages, protobuf, tools
from . import ChoiceType, with_client

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
@with_client
def get_address(client, coin, address, script_type, show_display):
    """Get address for specified path."""
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)
    return btc.get_address(
        client, coin, address_n, show_display, script_type=script_type
    )


@cli.command()
@click.option("-c", "--coin")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'")
@click.option("-e", "--curve")
@click.option("-t", "--script-type", type=ChoiceType(INPUT_SCRIPTS), default="address")
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_node(client, coin, address, curve, script_type, show_display):
    """Get public node of given path."""
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)
    result = btc.get_public_node(
        client,
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
@click.option("-c", "--coin", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.argument("json_file", type=click.File())
@with_client
def sign_tx(client, json_file):
    """Sign transaction.

    Transaction data must be provided in a JSON file. See `transaction-format.md` for
    description. You can use `tools/build_tx.py` from the source distribution to build
    the required JSON file interactively:

    $ python3 tools/build_tx.py | trezorctl btc sign-tx -
    """
    data = json.load(json_file)
    coin = data.get("coin_name", DEFAULT_COIN)
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
@with_client
def sign_message(client, coin, address, message, script_type):
    """Sign message using address of given path."""
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)
    res = btc.sign_message(client, coin, address_n, message, script_type)
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
@with_client
def verify_message(client, coin, address, signature, message):
    """Verify message."""
    signature = base64.b64decode(signature)
    coin = coin or DEFAULT_COIN
    return btc.verify_message(client, coin, address, signature, message)


#
# deprecated interactive signing
# ALL BELOW is legacy code and will be dropped
