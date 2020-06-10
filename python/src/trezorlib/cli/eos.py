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

from .. import eos, tools
from . import with_client

PATH_HELP = "BIP-32 path, e.g. m/44'/194'/0'/0/0"


@click.group(name="eos")
def cli():
    """EOS commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_key(client, address, show_display):
    """Get Eos public key in base58 encoding."""
    address_n = tools.parse_path(address)
    res = eos.get_public_key(client, address_n, show_display)
    return "WIF: {}\nRaw: {}".format(res.wif_public_key, res.raw_public_key.hex())


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@with_client
def sign_transaction(client, address, file):
    """Sign EOS transaction."""
    tx_json = json.load(file)

    address_n = tools.parse_path(address)
    return eos.sign_tx(client, address_n, tx_json["transaction"], tx_json["chain_id"])
