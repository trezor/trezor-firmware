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

from .. import messages, protobuf, tron, tools

PATH_HELP = "BIP-32 path, e.g. m/44'/195'/0'/0/0"


@click.group(name="tron")
def cli():
    """Tron commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_address(connect, address, show_display):
    """Get Tron address for specified path."""
    client = connect()
    address_n = tools.parse_path(address)
    return tron.get_address(client, address_n, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction file in JSON format (byte fields should be hexlified)",
)
@click.option(
    "-a",
    "--data",
    help="Transaction text in JSON format (byte fields should be hexlified)",
)
@click.pass_obj
def sign_tx(connect, address, file, data):
    """Sign Tron transaction."""
    client = connect()
    address_n = tools.parse_path(address)
    msg = json.load(file) if not data else json.loads(data)
    msg_proto = protobuf.dict_to_proto(messages.TronSignTx, msg)

    return tron.sign_tx(client, address_n, msg_proto)
