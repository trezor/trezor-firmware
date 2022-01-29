# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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
from typing import TYPE_CHECKING, TextIO

import click

from .. import eos, tools
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient
    from .. import messages

PATH_HELP = "BIP-32 path, e.g. m/44'/194'/0'/0/0"


@click.group(name="eos")
def cli() -> None:
    """EOS commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_client
def get_public_key(client: "TrezorClient", address: str, show_display: bool) -> str:
    """Get Eos public key in base58 encoding."""
    address_n = tools.parse_path(address)
    res = eos.get_public_key(client, address_n, show_display)
    return f"WIF: {res.wif_public_key}\nRaw: {res.raw_public_key.hex()}"


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@with_client
def sign_transaction(
    client: "TrezorClient", address: str, file: TextIO
) -> "messages.EosSignedTx":
    """Sign EOS transaction."""
    tx_json = json.load(file)

    address_n = tools.parse_path(address)
    return eos.sign_tx(client, address_n, tx_json["transaction"], tx_json["chain_id"])
