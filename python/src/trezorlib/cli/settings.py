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

from .. import device, firmware, messages, toif
from . import ChoiceType, with_client

try:
    from PIL import Image
except ImportError:
    Image = None


ROTATION = {"north": 0, "east": 90, "south": 180, "west": 270}
SAFETY_LEVELS = {
    "strict": messages.SafetyCheckLevel.Strict,
    "prompt": messages.SafetyCheckLevel.Prompt,
}


def image_to_t1(filename: str) -> bytes:
    if Image is None:
        raise click.ClickException(
            "Image library is missing. Please install via 'pip install Pillow'."
        )

    if filename.endswith(".toif"):
        raise click.ClickException("TOIF images not supported on Trezor One")

    try:
        image = Image.open(filename)
    except Exception as e:
        raise click.ClickException("Failed to load image") from e

    if image.size != (128, 64):
        raise click.ClickException("Wrong size of the image - should be 128x64")

    image = image.convert("1")
    return image.tobytes("raw", "1")


def image_to_tt(filename: str) -> bytes:
    if filename.endswith(".toif"):
        try:
            toif_image = toif.load(filename)
        except Exception as e:
            raise click.ClickException("TOIF file is corrupted") from e

    elif Image is None:
        raise click.ClickException(
            "Image library is missing. Please install via 'pip install Pillow'."
        )

    else:
        try:
            image = Image.open(filename)
            toif_image = toif.from_image(image)
        except Exception as e:
            raise click.ClickException(
                "Failed to convert image to Trezor format"
            ) from e

    if toif_image.size != (144, 144):
        raise click.ClickException("Wrong size of image - should be 144x144")

    if toif_image.mode != firmware.ToifMode.full_color:
        raise click.ClickException("Wrong image mode - should be full_color")

    return toif_image.to_bytes()


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
@click.argument("filename")
@click.option(
    "-f", "--filename", "_ignore", is_flag=True, hidden=True, expose_value=False
)
@with_client
def homescreen(client, filename):
    """Set new homescreen.

    To revert to default homescreen, use 'trezorctl set homescreen default'
    """
    if filename == "default":
        img = b""
    else:
        # use Click's facility to validate the path for us
        param = click.Path(dir_okay=False, readable=True, exists=True)
        param.convert(filename, None, None)
        if client.features.model == "1":
            img = image_to_t1(filename)
        else:
            img = image_to_tt(filename)

    return device.apply_settings(client, homescreen=img)


@cli.command()
@click.argument("level", type=ChoiceType(SAFETY_LEVELS))
@with_client
def safety_checks(client, level):
    """Set safety check level.

    Set to "strict" to get the full Trezor security.

    Set to "prompt" if you want to be able to allow potentially unsafe actions, such as
    mismatching coin keys or extreme fees.

    This is a power-user feature. Use with caution.
    """
    return device.apply_settings(client, safety_checks=level)


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
