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

import click

from .. import solana, tools
from . import with_client

PATH_HELP = "BIP-32 path, e.g. m/44'/501'/0'/0'"


@click.group(name="solana")
def cli():
    """Solana commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client, address, show_display):
    """Get Solana address for specified path."""
    address_n = tools.parse_path(address)
    return solana.get_address(client, address_n, show_display)


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True,
              expose_value=False)
@with_client
def sign_tx(client, address, file):
    """Sign Solana transaction."""
    address_n = tools.parse_path(address)
    msg = solana.sign_tx(client, address_n, open(file, 'r').read())

    return {"signature": msg.signature.hex()}
