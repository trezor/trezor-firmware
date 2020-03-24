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

import re
import sys
from decimal import Decimal

import click

from .. import ethereum, tools
from . import with_client

try:
    import rlp
    import web3

    HAVE_SIGN_TX = True
except Exception:
    HAVE_SIGN_TX = False


PATH_HELP = "BIP-32 path, e.g. m/44'/60'/0'/0/0"

# fmt: off
ETHER_UNITS = {
    'wei':          1,
    'kwei':         1000,
    'babbage':      1000,
    'femtoether':   1000,
    'mwei':         1000000,
    'lovelace':     1000000,
    'picoether':    1000000,
    'gwei':         1000000000,
    'shannon':      1000000000,
    'nanoether':    1000000000,
    'nano':         1000000000,
    'szabo':        1000000000000,
    'microether':   1000000000000,
    'micro':        1000000000000,
    'finney':       1000000000000000,
    'milliether':   1000000000000000,
    'milli':        1000000000000000,
    'ether':        1000000000000000000,
    'eth':          1000000000000000000,
}
# fmt: on


def _amount_to_int(ctx, param, value):
    if value is None:
        return None
    if value.isdigit():
        return int(value)
    try:
        number, unit = re.match(r"^(\d+(?:.\d+)?)([a-z]+)", value).groups()
        scale = ETHER_UNITS[unit]
        decoded_number = Decimal(number)
        return int(decoded_number * scale)

    except Exception:
        raise click.BadParameter("Amount not understood")


def _list_units(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    maxlen = max(len(k) for k in ETHER_UNITS.keys()) + 1
    for unit, scale in ETHER_UNITS.items():
        click.echo("{:{maxlen}}:  {}".format(unit, scale, maxlen=maxlen))
    ctx.exit()


def _decode_hex(value):
    if value.startswith("0x") or value.startswith("0X"):
        return bytes.fromhex(value[2:])
    else:
        return bytes.fromhex(value)


def _erc20_contract(w3, token_address, to_address, amount):
    min_abi = [
        {
            "name": "transfer",
            "type": "function",
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "bool"}],
        }
    ]
    contract = w3.eth.contract(address=token_address, abi=min_abi)
    return contract.encodeABI("transfer", [to_address, amount])


#####################
#
# commands start here


@click.group(name="ethereum")
def cli():
    """Ethereum commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client, address, show_display):
    """Get Ethereum address in hex encoding."""
    address_n = tools.parse_path(address)
    return ethereum.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_node(client, address, show_display):
    """Get Ethereum public node of given path."""
    address_n = tools.parse_path(address)
    result = ethereum.get_public_node(client, address_n, show_display=show_display)
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


@cli.command()
@click.option(
    "-c", "--chain-id", type=int, default=1, help="EIP-155 chain id (replay protection)"
)
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-g", "--gas-limit", type=int, help="Gas limit (required for offline signing)"
)
@click.option(
    "-t",
    "--gas-price",
    help="Gas price (required for offline signing)",
    callback=_amount_to_int,
)
@click.option(
    "-i", "--nonce", type=int, help="Transaction counter (required for offline signing)"
)
@click.option("-d", "--data", help="Data as hex string, e.g. 0x12345678")
@click.option("-p", "--publish", is_flag=True, help="Publish transaction via RPC")
@click.option("-x", "--tx-type", type=int, help="TX type (used only for Wanchain)")
@click.option("-t", "--token", help="ERC20 token address")
@click.option(
    "--list-units",
    is_flag=True,
    help="List known currency units and exit.",
    is_eager=True,
    callback=_list_units,
    expose_value=False,
)
@click.argument("to_address")
@click.argument("amount", callback=_amount_to_int)
@with_client
def sign_tx(
    client,
    chain_id,
    address,
    amount,
    gas_limit,
    gas_price,
    nonce,
    data,
    publish,
    to_address,
    tx_type,
    token,
):
    """Sign (and optionally publish) Ethereum transaction.

    Use TO_ADDRESS as destination address, or set to "" for contract creation.

    Specify a contract address with the --token option to send an ERC20 token.

    You can specify AMOUNT and gas price either as a number of wei,
    or you can use a unit suffix.

    Use the --list-units option to show all known currency units.
    ERC20 token amounts are specified in eth/wei, custom units are not supported.

    If any of gas price, gas limit and nonce is not specified, this command will
    try to connect to an ethereum node and auto-fill these values. You can configure
    the connection with WEB3_PROVIDER_URI environment variable.
    """
    if not HAVE_SIGN_TX:
        click.echo("Ethereum requirements not installed.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install web3 rlp")
        sys.exit(1)

    w3 = web3.Web3()
    if (
        any(x is None for x in (gas_price, gas_limit, nonce))
        or publish
        and not w3.isConnected()
    ):
        click.echo("Failed to connect to Ethereum node.")
        click.echo(
            "If you want to sign offline, make sure you provide --gas-price, "
            "--gas-limit and --nonce arguments"
        )
        sys.exit(1)

    if data is not None and token is not None:
        click.echo("Can't send tokens and custom data at the same time")
        sys.exit(1)

    address_n = tools.parse_path(address)
    from_address = ethereum.get_address(client, address_n)

    if token:
        data = _erc20_contract(w3, token, to_address, amount)
        to_address = token
        amount = 0

    if data:
        data = _decode_hex(data)
    else:
        data = b""

    if gas_price is None:
        gas_price = w3.eth.gasPrice

    if gas_limit is None:
        gas_limit = w3.eth.estimateGas(
            {
                "to": to_address,
                "from": from_address,
                "value": amount,
                "data": "0x%s" % data.hex(),
            }
        )

    if nonce is None:
        nonce = w3.eth.getTransactionCount(from_address)

    sig = ethereum.sign_tx(
        client,
        n=address_n,
        tx_type=tx_type,
        nonce=nonce,
        gas_price=gas_price,
        gas_limit=gas_limit,
        to=to_address,
        value=amount,
        data=data,
        chain_id=chain_id,
    )

    to = _decode_hex(to_address)
    if tx_type is None:
        transaction = rlp.encode((nonce, gas_price, gas_limit, to, amount, data) + sig)
    else:
        transaction = rlp.encode(
            (tx_type, nonce, gas_price, gas_limit, to, amount, data) + sig
        )
    tx_hex = "0x%s" % transaction.hex()

    if publish:
        tx_hash = w3.eth.sendRawTransaction(tx_hex).hex()
        return "Transaction published with ID: %s" % tx_hash
    else:
        return "Signed raw transaction:\n%s" % tx_hex


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("message")
@with_client
def sign_message(client, address, message):
    """Sign message with Ethereum address."""
    address_n = tools.parse_path(address)
    ret = ethereum.sign_message(client, address_n, message)
    output = {
        "message": message,
        "address": ret.address,
        "signature": "0x%s" % ret.signature.hex(),
    }
    return output


@cli.command()
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@with_client
def verify_message(client, address, signature, message):
    """Verify message signed with Ethereum address."""
    signature = _decode_hex(signature)
    return ethereum.verify_message(client, address, signature, message)
