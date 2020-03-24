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

from .. import cosi, tools
from . import with_client

PATH_HELP = "BIP-32 path, e.g. m/44'/0'/0'/0/0"


@click.group(name="cosi")
def cli():
    """CoSi (Cothority / collective signing) commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("data")
@with_client
def commit(client, address, data):
    """Ask device to commit to CoSi signing."""
    address_n = tools.parse_path(address)
    return cosi.commit(client, address_n, bytes.fromhex(data))


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.argument("data")
@click.argument("global_commitment")
@click.argument("global_pubkey")
@with_client
def sign(client, address, data, global_commitment, global_pubkey):
    """Ask device to sign using CoSi."""
    address_n = tools.parse_path(address)
    return cosi.sign(
        client,
        address_n,
        bytes.fromhex(data),
        bytes.fromhex(global_commitment),
        bytes.fromhex(global_pubkey),
    )
