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
import construct as c

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


XpubStruct = c.Struct(
    "version" / c.Int32ub,
    "depth" / c.Int8ub,
    "fingerprint" / c.Int32ub,
    "child_num" / c.Int32ub,
    "chain_code" / c.Bytes(32),
    "key" / c.Bytes(33),
    c.Terminated,
)


def xpub_deserialize(xpubstr):
    xpub_bytes = tools.b58check_decode(xpubstr)
    data = XpubStruct.parse(xpub_bytes)
    node = messages.HDNodeType(
        depth=data.depth,
        fingerprint=data.fingerprint,
        child_num=data.child_num,
        chain_code=data.chain_code,
    )
    if data.key[0] == 0:
        node.private_key = data.key[1:]
    else:
        node.public_key = data.key

    return data.version, node


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
@click.option("-x", "--multisig-xpub", multiple=True, help="XPUBs of multisig owners")
@click.option("-m", "--multisig-threshold", type=int, help="Number of signatures")
@click.option(
    "-N",
    "--multisig-suffix-length",
    help="BIP-32 suffix length for multisig",
    type=int,
    default=2,
)
@with_client
def get_address(
    client,
    coin,
    address,
    script_type,
    show_display,
    multisig_xpub,
    multisig_threshold,
    multisig_suffix_length,
):
    """Get address for specified path.

    To obtain a multisig address, provide XPUBs of all signers (including your own) in
    the intended order. All XPUBs should be on the same level. By default, it is assumed
    that the XPUBs are on the account level, and the last two components of --address
    should be derived from all of them.

    For BIP-45 multisig:

    \b
    $ trezorctl btc get-public-node -n m/45h/0
    xpub0101
    $ trezorctl btc get-address -n m/45h/0/0/7 -m 3 -x xpub0101 -x xpub0202 -x xpub0303

    This assumes that the other signers also created xpubs at address "m/45h/i".
    For all the signers, the final keys will be derived with the "/0/7" suffix.

    You can specify a different suffix length by using the -N option. For example, to
    use final xpubs, specify '-N 0'.
    """
    coin = coin or DEFAULT_COIN
    address_n = tools.parse_path(address)

    if multisig_xpub:
        if multisig_threshold is None:
            raise click.ClickException("Please specify signature threshold")

        multisig_suffix = address_n[-multisig_suffix_length:]
        nodes = [xpub_deserialize(x)[1] for x in multisig_xpub]
        multisig = messages.MultisigRedeemScriptType(
            nodes=nodes, address_n=multisig_suffix, m=multisig_threshold
        )
        if script_type == messages.InputScriptType.SPENDADDRESS:
            script_type = messages.InputScriptType.SPENDMULTISIG
    else:
        multisig = None

    return btc.get_address(
        client,
        coin,
        address_n,
        show_display,
        script_type=script_type,
        multisig=multisig,
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
@click.option("-c", "--coin", is_flag=True, hidden=True, expose_value=False)
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
