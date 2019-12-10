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

from .. import cardano, tools

PATH_HELP = "BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"


@click.group(name="cardano")
def cli():
    """Cardano commands."""


@cli.command()
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.option("-N", "--network", type=int, default=1)
@click.pass_obj
def sign_tx(connect, file, network):
    """Sign Cardano transaction."""
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


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_address(connect, address, show_display):
    """Get Cardano address."""
    client = connect()
    address_n = tools.parse_path(address)

    return cardano.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.pass_obj
def get_public_key(connect, address):
    """Get Cardano public key."""
    client = connect()
    address_n = tools.parse_path(address)

    return cardano.get_public_key(client, address_n)
