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

from .. import messages, protobuf, tezos, tools
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session

PATH_HELP = "BIP-32 path, e.g. m/44h/1729h/0h"


@click.group(name="tezos")
def cli() -> None:
    """Tezos commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session", address: str, show_display: bool, chunkify: bool
) -> str:
    """Get Tezos address for specified path."""
    address_n = tools.parse_path(address)
    return tezos.get_address(session, address_n, show_display, chunkify)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@with_session
def get_public_key(session: "Session", address: str, show_display: bool) -> str:
    """Get Tezos public key."""
    address_n = tools.parse_path(address)
    return tezos.get_public_key(session, address_n, show_display)


@cli.command()
@click.argument("file", type=click.File("r"))
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-f", "--file", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def sign_tx(
    session: "Session", address: str, file: TextIO, chunkify: bool
) -> messages.TezosSignedTx:
    """Sign Tezos transaction."""
    address_n = tools.parse_path(address)
    msg = protobuf.dict_to_proto(messages.TezosSignTx, json.load(file))
    return tezos.sign_tx(session, address_n, msg, chunkify=chunkify)
