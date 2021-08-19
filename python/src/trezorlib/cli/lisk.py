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

import click

from .. import lisk, tools
from . import with_client

PATH_HELP = "BIP-32 path, e.g. m/44'/134'/0'/0'"


@click.group(name="lisk")
def cli():
    """Lisk commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client, address, show_display):
    """Get Lisk address for specified path."""
    address_n = tools.parse_path(address)
    return lisk.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_key(client, address, show_display):
    """Get Lisk public key for specified path."""
    address_n = tools.parse_path(address)
    res = lisk.get_public_key(client, address_n, show_display)
    output = {"public_key": res.public_key.hex()}
    return output


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@with_client
def sign_tx(client, address, file):
    """Sign Lisk transaction."""
    address_n = tools.parse_path(address)
    transaction = lisk.sign_tx(client, address_n, json.load(file))

    payload = {"signature": transaction.signature.hex()}

    return payload


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("message")
@with_client
def sign_message(client, address, message):
    """Sign message with Lisk address."""
    address_n = tools.parse_path(address)
    res = lisk.sign_message(client, address_n, message)
    output = {
        "message": message,
        "public_key": res.public_key.hex(),
        "signature": res.signature.hex(),
    }
    return output


@cli.command()
@click.argument("pubkey")
@click.argument("signature")
@click.argument("message")
@with_client
def verify_message(client, pubkey, signature, message):
    """Verify message signed with Lisk address."""
    signature = bytes.fromhex(signature)
    pubkey = bytes.fromhex(pubkey)
    return lisk.verify_message(client, pubkey, signature, message)
