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

from .. import monero, tools

PATH_HELP = "BIP-32 path, e.g. m/44'/128'/0'"


@click.group(name="monero")
def cli():
    """Monero commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "-t", "--network-type", type=click.Choice(["0", "1", "2", "3"]), default="0"
)
@click.pass_obj
def get_address(connect, address, show_display, network_type):
    """Get Monero address for specified path."""
    client = connect()
    address_n = tools.parse_path(address)
    network_type = int(network_type)
    return monero.get_address(client, address_n, show_display, network_type)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-t", "--network-type", type=click.Choice(["0", "1", "2", "3"]), default="0"
)
@click.pass_obj
def get_watch_key(connect, address, network_type):
    """Get Monero watch key for specified path."""
    client = connect()
    address_n = tools.parse_path(address)
    network_type = int(network_type)
    res = monero.get_watch_key(client, address_n, network_type)
    output = {"address": res.address.decode(), "watch_key": res.watch_key.hex()}
    return output
