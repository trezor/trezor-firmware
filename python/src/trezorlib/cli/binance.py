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

from .. import binance, tools

PATH_HELP = "BIP-32 path to key, e.g. m/44'/714'/0'/0/0"


@click.group(name="binance")
def cli():
    """Binance Chain commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_address(connect, address, show_display):
    """Get Binance address for specified path."""
    client = connect()
    address_n = tools.parse_path(address)

    return binance.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_public_key(connect, address, show_display):
    """Get Binance public key."""
    client = connect()
    address_n = tools.parse_path(address)

    return binance.get_public_key(client, address_n, show_display).hex()


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.pass_obj
def sign_tx(connect, address, file):
    """Sign Binance transaction"""
    client = connect()
    address_n = tools.parse_path(address)

    return binance.sign_tx(client, address_n, json.load(file))
