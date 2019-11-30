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
import os
import sys
import time

import click

from .. import coins, log, messages, protobuf, ui
from ..client import TrezorClient
from ..transport import enumerate_devices, get_transport
from ..transport.udp import UdpTransport
from . import (
    binance,
    btc,
    cardano,
    cosi,
    crypto,
    device,
    eos,
    ethereum,
    fido,
    firmware,
    lisk,
    monero,
    nem,
    nem2,
    protobuf,
    ripple,
    settings,
    stellar,
    tezos,
)

COMMAND_ALIASES = {
    "change-pin": settings.pin,
    "enable-passphrase": settings.passphrase_enable,
    "disable-passphrase": settings.passphrase_disable,
    "set-passphrase-source": settings.passphrase_source,
    "wipe-device": device.wipe,
    "reset-device": device.setup,
    "recovery-device": device.recover,
    "backup-device": device.backup,
    "sd-protect": device.sd_protect,
    "load-device": device.load,
    "self-test": device.self_test,
    "get-entropy": crypto.get_entropy,
    "encrypt-keyvalue": crypto.encrypt_keyvalue,
    "decrypt-keyvalue": crypto.decrypt_keyvalue,
    # currency name aliases:
    "bnb": binance.cli,
    "eth": ethereum.cli,
    "ada": cardano.cli,
    "lsk": lisk.cli,
    "xmr": monero.cli,
    "xrp": ripple.cli,
    "xlm": stellar.cli,
    "xtz": tezos.cli,
}


class TrezorctlGroup(click.Group):
    """Command group that handles compatibility for trezorctl.

    The purpose is twofold: convert underscores to dashes, and ensure old-style commands
    still work with new-style groups.

    Click 7.0 silently switched all underscore_commands to dash-commands.
    This implementation of `click.Group` responds to underscore_commands by invoking
    the respective dash-command.

    With trezorctl 0.11.5, we started to convert old-style long commands
    (such as "binance-sign-tx") to command groups ("binance") with subcommands
    ("sign-tx"). The `TrezorctlGroup` can perform subcommand lookup: if a command
    "binance-sign-tx" does not exist in the default group, it tries to find "sign-tx"
    subcommand of "binance" group.
    """

    def get_command(self, ctx, cmd_name):
        cmd_name = cmd_name.replace("_", "-")
        # try to look up the real name
        cmd = super().get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # look for a backwards compatibility alias
        if cmd_name in COMMAND_ALIASES:
            return COMMAND_ALIASES[cmd_name]

        # look for subcommand in btc - "sign-tx" is now "btc sign-tx"
        cmd = btc.cli.get_command(ctx, cmd_name)
        if cmd:
            return cmd

        # Old-style top-level commands looked like this: binance-sign-tx.
        # We are moving to 'binance' command with 'sign-tx' subcommand.
        try:
            command, subcommand = cmd_name.split("-", maxsplit=1)
            return super().get_command(ctx, command).get_command(ctx, subcommand)
        except Exception:
            pass

        # try to find a bitcoin-like coin whose shortcut matches the command
        for coin in coins.coins_list:
            if cmd_name.lower() == coin["shortcut"].lower():
                btc.DEFAULT_COIN = coin["coin_name"]
                return btc.cli

        return None


def configure_logging(verbose: int):
    if verbose:
        log.enable_debug_output(verbose)
        log.OMITTED_MESSAGES.add(messages.Features)


@click.command(cls=TrezorctlGroup, context_settings={"max_content_width": 400})
@click.option(
    "-p",
    "--path",
    help="Select device by specific path.",
    default=os.environ.get("TREZOR_PATH"),
)
@click.option("-v", "--verbose", count=True, help="Show communication messages.")
@click.option(
    "-j", "--json", "is_json", is_flag=True, help="Print result as JSON object"
)
@click.version_option()
@click.pass_context
def cli(ctx, path, verbose, is_json):
    configure_logging(verbose)

    def get_device():
        try:
            device = get_transport(path, prefix_search=False)
        except Exception:
            try:
                device = get_transport(path, prefix_search=True)
            except Exception:
                click.echo("Failed to find a Trezor device.")
                if path is not None:
                    click.echo("Using path: {}".format(path))
                sys.exit(1)
        return TrezorClient(transport=device, ui=ui.ClickUI())

    ctx.obj = get_device


@cli.resultcallback()
def print_result(res, path, verbose, is_json):
    if is_json:
        if isinstance(res, protobuf.MessageType):
            click.echo(json.dumps({res.__class__.__name__: res.__dict__}))
        else:
            click.echo(json.dumps(res, sort_keys=True, indent=4))
    else:
        if isinstance(res, list):
            for line in res:
                click.echo(line)
        elif isinstance(res, dict):
            for k, v in res.items():
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        click.echo("%s.%s: %s" % (k, kk, vv))
                else:
                    click.echo("%s: %s" % (k, v))
        elif isinstance(res, protobuf.MessageType):
            click.echo(protobuf.format_message(res))
        elif res is not None:
            click.echo(res)


#
# Common functions
#


@cli.command(name="list")
def list_devices():
    """List connected Trezor devices."""
    return enumerate_devices()


@cli.command()
def version():
    """Show version of trezorctl/trezorlib."""
    from trezorlib import __version__ as VERSION

    return VERSION


#
# Basic device functions
#


@cli.command()
@click.argument("message")
@click.option("-b", "--button-protection", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.pass_obj
def ping(connect, message, button_protection, pin_protection, passphrase_protection):
    """Send ping message."""
    return connect().ping(
        message,
        button_protection=button_protection,
        pin_protection=pin_protection,
        passphrase_protection=passphrase_protection,
    )


@cli.command()
@click.pass_obj
def clear_session(connect):
    """Clear session (remove cached PIN, passphrase, etc.)."""
    return connect().clear_session()


@cli.command()
@click.pass_obj
def get_features(connect):
    """Retrieve device features and settings."""
    return connect().features


@cli.command()
def usb_reset():
    """Perform USB reset on stuck devices.

    This can fix LIBUSB_ERROR_PIPE and similar errors when connecting to a device
    in a messed state.
    """
    from trezorlib.transport.webusb import WebUsbTransport

    WebUsbTransport.enumerate(usb_reset=True)


@cli.command()
@click.option("-t", "--timeout", type=float, default=10, help="Timeout in seconds")
@click.pass_context
def wait_for_emulator(ctx, timeout):
    """Wait until Trezor Emulator comes up.

    Tries to connect to emulator and returns when it succeeds.
    """
    path = ctx.parent.params.get("path")
    if path:
        if not path.startswith("udp:"):
            raise click.ClickException("You must use UDP path, not {}".format(path))
        path = path.replace("udp:", "")

    start = time.monotonic()
    UdpTransport(path).wait_until_ready(timeout)
    end = time.monotonic()

    if ctx.parent.params.get("verbose"):
        click.echo("Waited for {:.3f} seconds".format(end - start))


#
# Basic coin functions
#


@cli.command(help="Sign message using address of given path.")
@click.option("-c", "--coin", default="Bitcoin")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.option(
    "-t",
    "--script-type",
    type=click.Choice(["address", "segwit", "p2shsegwit"]),
    default="address",
)
@click.argument("message")
@click.pass_obj
def sign_message(connect, coin, address, message, script_type):
    client = connect()
    address_n = tools.parse_path(address)
    typemap = {
        "address": proto.InputScriptType.SPENDADDRESS,
        "segwit": proto.InputScriptType.SPENDWITNESS,
        "p2shsegwit": proto.InputScriptType.SPENDP2SHWITNESS,
    }
    script_type = typemap[script_type]
    res = btc.sign_message(client, coin, address_n, message, script_type)
    return {
        "message": message,
        "address": res.address,
        "signature": base64.b64encode(res.signature),
    }


@cli.command(help="Verify message.")
@click.option("-c", "--coin", default="Bitcoin")
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def verify_message(connect, coin, address, signature, message):
    signature = base64.b64decode(signature)
    return btc.verify_message(connect(), coin, address, signature, message)


@cli.command(help="Sign message with Ethereum address.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/60'/0'/0/0"
)
@click.argument("message")
@click.pass_obj
def ethereum_sign_message(connect, address, message):
    client = connect()
    address_n = tools.parse_path(address)
    ret = ethereum.sign_message(client, address_n, message)
    output = {
        "message": message,
        "address": ret.address,
        "signature": "0x%s" % ret.signature.hex(),
    }
    return output


def ethereum_decode_hex(value):
    if value.startswith("0x") or value.startswith("0X"):
        return bytes.fromhex(value[2:])
    else:
        return bytes.fromhex(value)


@cli.command(help="Verify message signed with Ethereum address.")
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def ethereum_verify_message(connect, address, signature, message):
    signature = ethereum_decode_hex(signature)
    return ethereum.verify_message(connect(), address, signature, message)


@cli.command(help="Encrypt value by given key and path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def encrypt_keyvalue(connect, address, key, value):
    client = connect()
    address_n = tools.parse_path(address)
    res = misc.encrypt_keyvalue(client, address_n, key, value.encode())
    return res.hex()


@cli.command(help="Decrypt value by given key and path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def decrypt_keyvalue(connect, address, key, value):
    client = connect()
    address_n = tools.parse_path(address)
    return misc.decrypt_keyvalue(client, address_n, key, bytes.fromhex(value))


# @cli.command(help='Encrypt message.')
# @click.option('-c', '--coin', default='Bitcoin')
# @click.option('-d', '--display-only', is_flag=True)
# @click.option('-n', '--address', required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0")
# @click.argument('pubkey')
# @click.argument('message')
# @click.pass_obj
# def encrypt_message(connect, coin, display_only, address, pubkey, message):
#     client = connect()
#     pubkey = bytes.fromhex(pubkey)
#     address_n = tools.parse_path(address)
#     res = client.encrypt_message(pubkey, message, display_only, coin, address_n)
#     return {
#         'nonce': res.nonce.hex(),
#         'message': res.message.hex(),
#         'hmac': res.hmac.hex(),
#         'payload': base64.b64encode(res.nonce + res.message + res.hmac),
#     }


# @cli.command(help='Decrypt message.')
# @click.option('-n', '--address', required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0")
# @click.argument('payload')
# @click.pass_obj
# def decrypt_message(connect, address, payload):
#     client = connect()
#     address_n = tools.parse_path(address)
#     payload = base64.b64decode(payload)
#     nonce, message, msg_hmac = payload[:33], payload[33:-8], payload[-8:]
#     return client.decrypt_message(address_n, nonce, message, msg_hmac)


#
# Ethereum functions
#


@cli.command(help="Get Ethereum address in hex encoding.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/60'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def ethereum_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return ethereum.get_address(client, address_n, show_display)


@cli.command(help="Get Ethereum public node of given path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/60'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def ethereum_get_public_node(connect, address, show_display):
    client = connect()
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


def ethereum_amount_to_int(ctx, param, value):
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
        import traceback

        traceback.print_exc()
        raise click.BadParameter("Amount not understood")


def ethereum_list_units(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    maxlen = max(len(k) for k in ETHER_UNITS.keys()) + 1
    for unit, scale in ETHER_UNITS.items():
        click.echo("{:{maxlen}}:  {}".format(unit, scale, maxlen=maxlen))
    ctx.exit()


def ethereum_erc20_contract(w3, token_address, to_address, amount):
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


@cli.command()
@click.option(
    "-c", "--chain-id", type=int, default=1, help="EIP-155 chain id (replay protection)"
)
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to source address, e.g., m/44'/60'/0'/0/0",
)
@click.option(
    "-g", "--gas-limit", type=int, help="Gas limit (required for offline signing)"
)
@click.option(
    "-t",
    "--gas-price",
    help="Gas price (required for offline signing)",
    callback=ethereum_amount_to_int,
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
    callback=ethereum_list_units,
    expose_value=False,
)
@click.argument("to_address")
@click.argument("amount", callback=ethereum_amount_to_int)
@click.pass_obj
def ethereum_sign_tx(
    connect,
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
    if not ETHEREUM_SIGN_TX:
        click.echo("Ethereum requirements not installed.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install web3 rlp")
        sys.exit(1)

    w3 = web3.Web3()
    if (
        gas_price is None or gas_limit is None or nonce is None or publish
    ) and not w3.isConnected():
        click.echo("Failed to connect to Ethereum node.")
        click.echo(
            "If you want to sign offline, make sure you provide --gas-price, "
            "--gas-limit and --nonce arguments"
        )
        sys.exit(1)

    if data is not None and token is not None:
        click.echo("Can't send tokens and custom data at the same time")
        sys.exit(1)

    client = connect()
    address_n = tools.parse_path(address)
    from_address = ethereum.get_address(client, address_n)

    if token:
        data = ethereum_erc20_contract(w3, token, to_address, amount)
        to_address = token
        amount = 0

    if data:
        data = ethereum_decode_hex(data)
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

    to = ethereum_decode_hex(to_address)
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


#
# EOS functions
#


@cli.command(help="Get Eos public key in base58 encoding.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/194'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def eos_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    res = eos.get_public_key(client, address_n, show_display)
    return "WIF: {}\nRaw: {}".format(res.wif_public_key, res.raw_public_key.hex())


@cli.command(help="Init sign (and optionally publish) EOS transaction. ")
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to source address, e.g., m/44'/194'/0'/0/0",
)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.pass_obj
def eos_sign_transaction(connect, address, file):
    client = connect()

    tx_json = json.load(file)

    address_n = tools.parse_path(address)
    return eos.sign_tx(client, address_n, tx_json["transaction"], tx_json["chain_id"])


#
# ADA functions
#


@cli.command(help="Sign Cardano transaction.")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.option("-N", "--network", type=int, default=1)
@click.pass_obj
def cardano_sign_tx(connect, file, network):
    client = connect()

    transaction = json.load(file)

    inputs = [cardano.create_input(input) for input in transaction["inputs"]]
    outputs = [cardano.create_output(output) for output in transaction["outputs"]]
    transactions = transaction["transactions"]

    signed_transaction = cardano.sign_tx(client, inputs, outputs, transactions, network)

    return {
        "tx_hash": signed_transaction.tx_hash.hex(),
        "tx_body": signed_transaction.tx_body.hex(),
    }


@cli.command(help="Get Cardano address.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def cardano_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)

    return cardano.get_address(client, address_n, show_display)


@cli.command(help="Get Cardano public key.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"
)
@click.pass_obj
def cardano_get_public_key(connect, address):
    client = connect()
    address_n = tools.parse_path(address)

    return cardano.get_public_key(client, address_n)


#
# NEM functions
#


@cli.command(help="Get NEM address for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/43'/0'")
@click.option("-N", "--network", type=int, default=0x68)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def nem_get_address(connect, address, network, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return nem.get_address(client, address_n, network, show_display)


@cli.command(help="Sign (and optionally broadcast) NEM transaction.")
@click.option("-n", "--address", help="BIP-32 path to signing key")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction in NIS (RequestPrepareAnnounce) format",
)
@click.option("-b", "--broadcast", help="NIS to announce transaction to")
@click.pass_obj
def nem_sign_tx(connect, address, file, broadcast):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = nem.sign_tx(client, address_n, json.load(file))

    payload = {"data": transaction.data.hex(), "signature": transaction.signature.hex()}

    if broadcast:
        return requests.post(
            "{}/transaction/announce".format(broadcast), json=payload
        ).json()
    else:
        return payload

#
# NEM2 functions
#

# TODO
# @cli.command(help="Get NEM2 Public Key for specified path.")
# @click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/43'/0'")
# @click.option("-N", "--network", type=int, default=0x68)
# @click.option("-d", "--show-display", is_flag=True)
# @click.pass_obj
# def nem2_get_address(connect, address, network, show_display):
#     client = connect()
#     address_n = tools.parse_path(address)
#     return nem.get_address(client, address_n, network, show_display)


@cli.command(help="Sign NEM2 transaction.")
@click.option("-n", "--address", required=True, help="BIP-32 path to signing key")
@click.option("-g", "--generation_hash", required=True, help="NEM2 network generation hash")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction object as per typescript sdk",
)
@click.pass_obj
def nem2_sign_tx(connect, address, generation_hash, file):
    client = connect()
    address_n = tools.parse_path(address)
    generation_hash = generation_hash

    transaction = nem2.sign_tx(client, address_n, generation_hash, json.load(file))

    payload = {"payload": transaction.payload.hex(), "hash": transaction.hash.hex()}

    return payload


#
# Lisk functions
#


@cli.command(help="Get Lisk address for specified path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/134'/0'/0'"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def lisk_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return lisk.get_address(client, address_n, show_display)


@cli.command(help="Get Lisk public key for specified path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/134'/0'/0'"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def lisk_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    res = lisk.get_public_key(client, address_n, show_display)
    output = {"public_key": res.public_key.hex()}
    return output


@cli.command(help="Sign Lisk transaction.")
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to signing key, e.g. m/44'/134'/0'/0'",
)
@click.option(
    "-f", "--file", type=click.File("r"), default="-", help="Transaction in JSON format"
)
# @click.option('-b', '--broadcast', help='Broadcast Lisk transaction')
@click.pass_obj
def lisk_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = lisk.sign_tx(client, address_n, json.load(file))

    payload = {"signature": transaction.signature.hex()}

    return payload


@cli.command(help="Sign message with Lisk address.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/134'/0'/0'"
)
@click.argument("message")
@click.pass_obj
def lisk_sign_message(connect, address, message):
    client = connect()
    address_n = client.expand_path(address)
    res = lisk.sign_message(client, address_n, message)
    output = {
        "message": message,
        "public_key": res.public_key.hex(),
        "signature": res.signature.hex(),
    }
    return output


@cli.command(help="Verify message signed with Lisk address.")
@click.argument("pubkey")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def lisk_verify_message(connect, pubkey, signature, message):
    signature = bytes.fromhex(signature)
    pubkey = bytes.fromhex(pubkey)
    return lisk.verify_message(connect(), pubkey, signature, message)


#
# Monero functions
#


@cli.command(help="Get Monero address for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/128'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "-t", "--network-type", type=click.Choice(["0", "1", "2", "3"]), default="0"
)
@click.pass_obj
def monero_get_address(connect, address, show_display, network_type):
    client = connect()
    address_n = tools.parse_path(address)
    network_type = int(network_type)
    return monero.get_address(client, address_n, show_display, network_type)


@cli.command(help="Get Monero watch key for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/128'/0'")
@click.option(
    "-t", "--network-type", type=click.Choice(["0", "1", "2", "3"]), default="0"
)
@click.pass_obj
def monero_get_watch_key(connect, address, network_type):
    client = connect()
    address_n = tools.parse_path(address)
    network_type = int(network_type)
    res = monero.get_watch_key(client, address_n, network_type)
    output = {"address": res.address.decode(), "watch_key": res.watch_key.hex()}
    return output


#
# CoSi functions
#


@cli.command(help="Ask device to commit to CoSi signing.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.argument("data")
@click.pass_obj
def cosi_commit(connect, address, data):
    client = connect()
    address_n = tools.parse_path(address)
    return cosi.commit(client, address_n, bytes.fromhex(data))


@cli.command(help="Ask device to sign using CoSi.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.argument("data")
@click.argument("global_commitment")
@click.argument("global_pubkey")
@click.pass_obj
def cosi_sign(connect, address, data, global_commitment, global_pubkey):
    client = connect()
    address_n = tools.parse_path(address)
    return cosi.sign(
        client,
        address_n,
        bytes.fromhex(data),
        bytes.fromhex(global_commitment),
        bytes.fromhex(global_pubkey),
    )


#
# Stellar functions
#
@cli.command(help="Get Stellar public address")
@click.option(
    "-n",
    "--address",
    required=False,
    help="BIP32 path. Always use hardened paths and the m/44'/148'/ prefix",
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def stellar_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return stellar.get_address(client, address_n, show_display)


@cli.command(help="Sign a base64-encoded transaction envelope")
@click.option(
    "-n",
    "--address",
    required=False,
    help="BIP32 path. Always use hardened paths and the m/44'/148'/ prefix",
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option(
    "-n",
    "--network-passphrase",
    default=stellar.DEFAULT_NETWORK_PASSPHRASE,
    required=False,
    help="Network passphrase (blank for public network). Testnet is: 'Test SDF Network ; September 2015'",
)
@click.argument("b64envelope")
@click.pass_obj
def stellar_sign_transaction(connect, b64envelope, address, network_passphrase):
    client = connect()
    address_n = tools.parse_path(address)
    tx, operations = stellar.parse_transaction_bytes(base64.b64decode(b64envelope))
    resp = stellar.sign_tx(client, tx, operations, address_n, network_passphrase)

    return base64.b64encode(resp.signature)


#
# Ripple functions
#
@cli.command(help="Get Ripple address")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/144'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def ripple_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return ripple.get_address(client, address_n, show_display)


@cli.command(help="Sign Ripple transaction")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/144'/0'/0/0"
)
@click.option(
    "-f", "--file", type=click.File("r"), default="-", help="Transaction in JSON format"
)
@click.pass_obj
def ripple_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)
    msg = ripple.create_sign_tx_msg(json.load(file))

    result = ripple.sign_tx(client, address_n, msg)
    click.echo("Signature:")
    click.echo(result.signature.hex())
    click.echo()
    click.echo("Serialized tx including the signature:")
    click.echo(result.serialized_tx.hex())


#
# Tezos functions
#
@cli.command(help="Get Tezos address for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/1729'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def tezos_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return tezos.get_address(client, address_n, show_display)


@cli.command(help="Get Tezos public key.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/1729'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def tezos_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return tezos.get_public_key(client, address_n, show_display)


@cli.command(help="Sign Tezos transaction.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/1729'/0'")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction in JSON format (byte fields should be hexlified)",
)
@click.pass_obj
def tezos_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)
    msg = protobuf.dict_to_proto(proto.TezosSignTx, json.load(file))
    return tezos.sign_tx(client, address_n, msg)


#
# Binance functions
#


@cli.command(help="Get Binance address for specified path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/714'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def binance_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)

    return binance.get_address(client, address_n, show_display)


@cli.command(help="Get Binance public key.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/714'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def binance_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)

    return binance.get_public_key(client, address_n, show_display).hex()


@cli.command(help="Sign Binance transaction")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/714'/0'/0/0"
)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.pass_obj
def binance_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)

    return binance.sign_tx(client, address_n, json.load(file))


#
# WebAuthn functions
#


@cli.command(help="List all resident credentials on the device.")
@click.pass_obj
def webauthn_list_credentials(connect):
    creds = webauthn.list_credentials(connect())
    for cred in creds:
        click.echo("")
        click.echo("WebAuthn credential at index {}:".format(cred.index))
        if cred.rp_id is not None:
            click.echo("  Relying party ID:       {}".format(cred.rp_id))
        if cred.rp_name is not None:
            click.echo("  Relying party name:     {}".format(cred.rp_name))
        if cred.user_id is not None:
            click.echo("  User ID:                {}".format(cred.user_id.hex()))
        if cred.user_name is not None:
            click.echo("  User name:              {}".format(cred.user_name))
        if cred.user_display_name is not None:
            click.echo("  User display name:      {}".format(cred.user_display_name))
        if cred.creation_time is not None:
            click.echo("  Creation time:          {}".format(cred.creation_time))
        if cred.hmac_secret is not None:
            click.echo("  hmac-secret enabled:    {}".format(cred.hmac_secret))
        if cred.use_sign_count is not None:
            click.echo("  Use signature counter:  {}".format(cred.use_sign_count))
        click.echo("  Credential ID:          {}".format(cred.id.hex()))

    if not creds:
        click.echo("There are no resident credentials stored on the device.")


@cli.command()
@click.argument("hex_credential_id")
@click.pass_obj
def webauthn_add_credential(connect, hex_credential_id):
    """Add the credential with the given ID as a resident credential.

    HEX_CREDENTIAL_ID is the credential ID as a hexadecimal string.
    """
    return webauthn.add_credential(connect(), bytes.fromhex(hex_credential_id))


@cli.command(help="Remove the resident credential at the given index.")
@click.option(
    "-i", "--index", required=True, type=click.IntRange(0, 15), help="Credential index."
)
@click.pass_obj
def webauthn_remove_credential(connect, index):
    return webauthn.remove_credential(connect(), index)


#
# Main
#


if __name__ == "__main__":
    cli()  # pylint: disable=E1120
