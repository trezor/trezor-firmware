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
import zipfile
from typing import TYPE_CHECKING, BinaryIO

import click

from .. import ble, exceptions
from ..transport.ble import BleProxy
from . import with_client

if TYPE_CHECKING:
    from ..client import TrezorClient


@click.group(name="ble")
def cli() -> None:
    """BLE commands."""


@cli.command()
# fmt: off
@click.argument("package", type=click.File("rb"))
# fmt: on
@with_client
def update(
    client: "TrezorClient",
    package: BinaryIO,
) -> None:
    """Upload new BLE firmware to device."""

    with zipfile.ZipFile(package) as archive:
        binfile = archive.read("ble_firmware.bin")
        datfile = archive.read("ble_firmware.dat")

        """Perform the final act of loading the firmware into Trezor."""
        try:
            click.echo("Uploading...\r", nl=False)
            with click.progressbar(
                label="Uploading", length=len(binfile), show_eta=False
            ) as bar:
                ble.update(client, datfile, binfile, bar.update)
                click.echo("Update successful.")
        except exceptions.Cancelled:
            click.echo("Update aborted on device.")
        except exceptions.TrezorException as e:
            click.echo(f"Update failed: {e}")
            sys.exit(3)


@cli.command()
def connect() -> None:
    """Connect to the device via BLE."""
    ble = BleProxy()
    devices = [d for d in ble.lookup() if d.connected]

    if len(devices) == 0:
        click.echo("Scanning...")
        devices = ble.scan()

    if len(devices) == 0:
        click.echo("No BLE devices found")
        return
    else:
        click.echo("Found %d BLE device(s)" % len(devices))

    for device in devices:
        click.echo(f"Device: {device.name}, {device.address}")

    device = devices[0]
    click.echo(f"Connecting to {device.name}...")
    ble.connect(device.address)
    click.echo("Connected")
