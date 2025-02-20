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

from .. import binance, tools
from ..transport.session import Session
from . import with_session

if TYPE_CHECKING:
    from .. import messages


PATH_HELP = "BIP-32 path to key, e.g. m/44h/714h/0h/0/0"


@click.group(name="binance")
def cli() -> None:
    """Binance Chain commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session", address: str, show_display: bool, chunkify: bool
) -> str:
    """Get Binance address for specified path."""
    address_n = tools.parse_path(address)
    return binance.get_address(session, address_n, show_display, chunkify)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_session
def get_public_key(session: "Session", address: str, show_display: bool) -> str:
    """Get Binance public key."""
    address_n = tools.parse_path(address)
    return binance.get_public_key(session, address_n, show_display).hex()


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def sign_tx(
    session: "Session", address: str, file: TextIO, chunkify: bool
) -> "messages.BinanceSignedTx":
    """Sign Binance transaction.

    Transaction must be provided as a JSON file.
    """
    address_n = tools.parse_path(address)
    return binance.sign_tx(session, address_n, json.load(file), chunkify=chunkify)
