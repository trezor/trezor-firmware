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

from .. import ble, exceptions, tealblue
from ..transport.ble import lookup_device, scan_device
from . import with_ble, with_client

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
@with_ble
def connect() -> None:
    """Connect to the device via BLE."""
    adapter = tealblue.TealBlue().find_adapter()

    devices = lookup_device(adapter)

    devices = [d for d in devices if d.connected]

    if len(devices) == 0:
        print("Scanning...")
        devices = scan_device(adapter, devices)

    if len(devices) == 0:
        print("No BLE devices found")
        return
    else:
        print("Found %d BLE device(s)" % len(devices))

    for device in devices:
        print(f"Device: {device.name}, {device.address}")

    device = devices[0]
    print(f"Connecting to {device.name}...")
    device.connect()
    print("Connected")


@cli.command()
@click.option("--device", is_flag=True, help="Disconnect from device side.")
@with_client
def disconnect(client: "TrezorClient", device: bool) -> None:

    if device:
        ble.disconnect(client)
    else:
        """Connect to the device via BLE."""
        adapter = tealblue.TealBlue().find_adapter()

        devices = lookup_device(adapter)

        devices = [d for d in devices if d.connected]

        if len(devices) == 0:
            print("No device is connected")

        for d in devices:
            d.disconnect()
            print(f"Device {d.name}, {d.address}, disconnected.")


@cli.command()
@with_client
def erase_bonds(
    client: "TrezorClient",
) -> None:
    """Erase BLE bonds on device."""

    try:
        ble.erase_bonds(client)
        click.echo("Erase successful.")
    except exceptions.Cancelled:
        click.echo("Erase aborted on device.")
    except exceptions.TrezorException as e:
        click.echo(f"Update failed: {e}")
        sys.exit(3)
