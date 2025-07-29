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

from typing import TYPE_CHECKING, Dict

import click

from .. import messages, monero, tools
from . import ChoiceType, with_session

if TYPE_CHECKING:
    from ..transport.session import Session

PATH_HELP = "BIP-32 path, e.g. m/44h/128h/0h"


@click.group(name="monero")
def cli() -> None:
    """Monero commands."""


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "-t",
    "--network-type",
    type=ChoiceType({m.name: m for m in messages.MoneroNetworkType}),
    default=messages.MoneroNetworkType.MAINNET,
)
@click.option("-C", "--chunkify", is_flag=True)
@with_session
def get_address(
    session: "Session",
    address: str,
    show_display: bool,
    network_type: messages.MoneroNetworkType,
    chunkify: bool,
) -> bytes:
    """Get Monero address for specified path."""
    address_n = tools.parse_path(address)
    return monero.get_address(session, address_n, show_display, network_type, chunkify)


@cli.command()
@click.option("-n", "--address", required=True, help=PATH_HELP)
@click.option(
    "-t",
    "--network-type",
    type=ChoiceType({m.name: m for m in messages.MoneroNetworkType}),
    default=messages.MoneroNetworkType.MAINNET,
)
@with_session
def get_watch_key(
    session: "Session", address: str, network_type: messages.MoneroNetworkType
) -> Dict[str, str]:
    """Get Monero watch key for specified path."""
    address_n = tools.parse_path(address)
    res = monero.get_watch_key(session, address_n, network_type)
    # TODO: could be made required in MoneroWatchKey
    assert res.address is not None
    assert res.watch_key is not None
    return {"address": res.address.decode(), "watch_key": res.watch_key.hex()}
