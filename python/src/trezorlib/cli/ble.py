# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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
from ..transport.ble import BleProxy
from . import with_session

if TYPE_CHECKING:
    from ..transport.session import Session


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
@with_session(seedless=True)
def unpair(
    session: "Session",
    all: bool,
) -> None:
    """Erase bond of currently connected device, or all devices (on device side)."""

    try:
        ble.unpair(session, all)
        click.echo("Unpair successful.")
    except exceptions.Cancelled:
        click.echo("Unpair cancelled on device.")
    except exceptions.TrezorException as e:
        click.echo(f"Unpair failed: {e}")
        sys.exit(3)


@cli.command()
def connect() -> None:
    """Connect to the device via BLE. Device has to be disconnected beforehand.

    If the device hasn't been paired you also need to have system bluetooth pairing dialog open.
    """
    ble = BleProxy()

    click.echo("Scanning...")
    devices = ble.scan()

    if len(devices) == 0:
        click.echo("No BLE devices found")
        return
    else:
        click.echo(f"Found {len(devices)} BLE device(s)")

    for address, name in devices:
        click.echo(f"Device: {name}, {address}")

    device = devices[0]
    click.echo(f"Connecting to {device[1]}...")
    ble.connect(device[0])
    click.echo("Connected")
