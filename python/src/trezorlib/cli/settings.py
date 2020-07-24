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

from .. import device
from . import ChoiceType, with_client

ROTATION = {"north": 0, "east": 90, "south": 180, "west": 270}


@click.group(name="set")
def cli():
    """Device settings."""


@cli.command()
@click.option("-r", "--remove", is_flag=True)
@with_client
def pin(client, remove):
    """Set, change or remove PIN."""
    return device.change_pin(client, remove)


@cli.command()
@click.option("-r", "--remove", is_flag=True)
@with_client
def wipe_code(client, remove):
    """Set or remove the wipe code.

    The wipe code functions as a "self-destruct PIN". If the wipe code is ever
    entered into any PIN entry dialog, then all private data will be immediately
    removed and the device will be reset to factory defaults.
    """
    return device.change_wipe_code(client, remove)


@cli.command()
# keep the deprecated -l/--label option, make it do nothing
@click.option("-l", "--label", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.argument("label")
@with_client
def label(client, label):
    """Set new device label."""
    return device.apply_settings(client, label=label)


@cli.command()
@click.argument("rotation", type=ChoiceType(ROTATION))
@with_client
def display_rotation(client, rotation):
    """Set display rotation.

    Configure display rotation for Trezor Model T. The options are
    north, east, south or west.
    """
    return device.apply_settings(client, display_rotation=rotation)


@cli.command()
@click.argument("delay", type=str)
@with_client
def auto_lock_delay(client, delay):
    """Set auto-lock delay (in seconds)."""

    if not client.features.pin_protection:
        raise click.ClickException("Set up a PIN first")

    value, unit = delay[:-1], delay[-1:]
    units = {"s": 1, "m": 60, "h": 3600}
    if unit in units:
        seconds = float(value) * units[unit]
    else:
        seconds = float(delay)  # assume seconds if no unit is specified
    return device.apply_settings(client, auto_lock_delay_ms=int(seconds * 1000))


@cli.command()
@click.argument("flags")
@with_client
def flags(client, flags):
    """Set device flags."""
    flags = flags.lower()
    if flags.startswith("0b"):
        flags = int(flags, 2)
    elif flags.startswith("0x"):
        flags = int(flags, 16)
    else:
        flags = int(flags)
    return device.apply_flags(client, flags=flags)


@cli.command()
@click.option("-f", "--filename", default=None)
@with_client
def homescreen(client, filename):
    """Set new homescreen."""
    if filename is None:
        img = b"\x00"
    elif filename.endswith(".toif"):
        img = open(filename, "rb").read()
        if img[:8] != b"TOIf\x90\x00\x90\x00":
            raise click.ClickException("File is not a TOIF file with size of 144x144")
    else:
        from PIL import Image

        im = Image.open(filename)
        if im.size != (128, 64):
            raise click.ClickException("Wrong size of the image")
        im = im.convert("1")
        pix = im.load()
        img = bytearray(1024)
        for j in range(64):
            for i in range(128):
                if pix[i, j]:
                    o = i + j * 128
                    img[o // 8] |= 1 << (7 - o % 8)
        img = bytes(img)
    return device.apply_settings(client, homescreen=img)


@cli.command()
@click.argument("allow", type=click.Choice(("on", "off")))
@with_client
def unsafe_prompts(client, allow):
    """Allow or disallow unsafe prompts.

    This is a power-user feature. With unsafe prompts enabled, Trezor will ask the user
    to confirm possibly dangerous actions instead of rejecting them outright.
    Use with caution.
    """
    allowed = allow == "on"
    return device.apply_settings(client, unsafe_prompts=allowed)


#
# passphrase operations
#


@cli.group()
def passphrase():
    """Enable, disable or configure passphrase protection."""
    # this exists in order to support command aliases for "enable-passphrase"
    # and "disable-passphrase". Otherwise `passphrase` would just take an argument.


@passphrase.command(name="enabled")
@click.option("-f/-F", "--force-on-device/--no-force-on-device", default=None)
@with_client
def passphrase_enable(client, force_on_device: bool):
    """Enable passphrase."""
    return device.apply_settings(
        client, use_passphrase=True, passphrase_always_on_device=force_on_device
    )


@passphrase.command(name="disabled")
@with_client
def passphrase_disable(client):
    """Disable passphrase."""
    return device.apply_settings(client, use_passphrase=False)
