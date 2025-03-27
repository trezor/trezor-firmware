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

import sys
from typing import TYPE_CHECKING

import click

from .. import ble, exceptions
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="ble")
def cli() -> None:
    """BLE commands."""


@cli.command()
@click.option(
    "-a",
    "--all",
    help="Erase all bonds.",
    is_flag=True,
)
@with_client
def unpair(
    client: "TrezorClient",
    all: bool,
) -> None:
    """Erase bond of currently connected device, or all devices (on device side)"""

    try:
        ble.unpair(client, all)
        click.echo("Unpair successful.")
    except exceptions.Cancelled:
        click.echo("Unpair cancelled on device.")
    except exceptions.TrezorException as e:
        click.echo(f"Unpair failed: {e}")
        sys.exit(3)
