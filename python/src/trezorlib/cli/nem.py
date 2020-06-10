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
import requests

from .. import nem, tools
from . import with_client

PATH_HELP = "BIP-32 path, e.g. m/44'/134'/0'/0'"


@click.group(name="nem")
def cli():
    """NEM commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-N", "--network", type=int, default=0x68)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_address(client, address, network, show_display):
    """Get NEM address for specified path."""
    address_n = tools.parse_path(address)
    return nem.get_address(client, address_n, network, show_display)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction in NIS (RequestPrepareAnnounce) format",
)
@click.option("-b", "--broadcast", help="NIS to announce transaction to")
@with_client
def sign_tx(client, address, file, broadcast):
    """Sign (and optionally broadcast) NEM transaction."""
    address_n = tools.parse_path(address)
    transaction = nem.sign_tx(client, address_n, json.load(file))

    payload = {"data": transaction.data.hex(), "signature": transaction.signature.hex()}

    if broadcast:
        return requests.post(
            "{}/transaction/announce".format(broadcast), json=payload
        ).json()
    else:
        return payload
