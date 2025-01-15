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
        manifest = archive.read("manifest.json")
        mainfest_data = json.loads(manifest.decode("utf-8"))["manifest"]

        for k in mainfest_data.keys():

            binfile = archive.read(mainfest_data[k]["bin_file"])
            datfile = archive.read(mainfest_data[k]["dat_file"])

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


@with_client
def disconnect_device(client: "TrezorClient") -> None:
    """Disconnect from device side."""
    try:
        ble.disconnect(client)
    except exceptions.Cancelled:
        click.echo("Disconnect aborted on device.")
    except exceptions.TrezorException as e:
        click.echo(f"Disconnect failed: {e}")
        sys.exit(3)


@cli.command()
@click.option("--device", is_flag=True, help="Disconnect from device side.")
def disconnect(device: bool) -> None:

    if device:
        disconnect_device()
    else:
        ble_proxy = BleProxy()
        devices = [d for d in ble_proxy.lookup() if d.connected]
        if len(devices) == 0:
            click.echo("No BLE devices found")
            return
        ble_proxy.connect(devices[0].address)
        ble_proxy.disconnect()


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
        click.echo(f"Erase bonds failed: {e}")
        sys.exit(3)


@cli.command()
@with_client
def unpair(
    client: "TrezorClient",
) -> None:
    """Erase bond of currently connected device. (on device side)"""

    try:
        ble.unpair(client)
        click.echo("Unpair successful.")
    except exceptions.Cancelled:
        click.echo("Unapair aborted on device.")
    except exceptions.TrezorException as e:
        click.echo(f"Unpair failed: {e}")
        sys.exit(3)
