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

from typing import TYPE_CHECKING, Optional, cast

import click

from .. import device, firmware, messages, toif
from . import AliasedGroup, ChoiceType, with_client

if TYPE_CHECKING:
    from ..client import TrezorClient

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

ROTATION = {"north": 0, "east": 90, "south": 180, "west": 270}
SAFETY_LEVELS = {
    "strict": messages.SafetyCheckLevel.Strict,
    "prompt": messages.SafetyCheckLevel.PromptTemporarily,
}


def image_to_t1(filename: str) -> bytes:
    if not PIL_AVAILABLE:
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

    elif not PIL_AVAILABLE:
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


def _should_remove(enable: Optional[bool], remove: bool) -> bool:
    """Helper to decide whether to remove something or not.

    Needed for backwards compatibility purposes, so we can support
    both positive (enable) and negative (remove) args.
    """
    if remove and enable:
        raise click.ClickException("Argument and option contradict each other")

    if remove or enable is False:
        return True

    return False


@click.group(name="set")
def cli() -> None:
    """Device settings."""


@cli.command()
@click.option("-r", "--remove", is_flag=True, hidden=True)
@click.argument("enable", type=ChoiceType({"on": True, "off": False}), required=False)
@with_client
def pin(client: "TrezorClient", enable: Optional[bool], remove: bool) -> str:
    """Set, change or remove PIN."""
    # Remove argument is there for backwards compatibility
    return device.change_pin(client, remove=_should_remove(enable, remove))


@cli.command()
@click.option("-r", "--remove", is_flag=True, hidden=True)
@click.argument("enable", type=ChoiceType({"on": True, "off": False}), required=False)
@with_client
def wipe_code(client: "TrezorClient", enable: Optional[bool], remove: bool) -> str:
    """Set or remove the wipe code.

    The wipe code functions as a "self-destruct PIN". If the wipe code is ever
    entered into any PIN entry dialog, then all private data will be immediately
    removed and the device will be reset to factory defaults.
    """
    # Remove argument is there for backwards compatibility
    return device.change_wipe_code(client, remove=_should_remove(enable, remove))


@cli.command()
# keep the deprecated -l/--label option, make it do nothing
@click.option("-l", "--label", "_ignore", is_flag=True, hidden=True, expose_value=False)
@click.argument("label")
@with_client
def label(client: "TrezorClient", label: str) -> str:
    """Set new device label."""
    return device.apply_settings(client, label=label)


@cli.command()
@click.argument("rotation", type=ChoiceType(ROTATION))
@with_client
def display_rotation(client: "TrezorClient", rotation: int) -> str:
    """Set display rotation.

    Configure display rotation for Trezor Model T. The options are
    north, east, south or west.
    """
    return device.apply_settings(client, display_rotation=rotation)


@cli.command()
@click.argument("delay", type=str)
@with_client
def auto_lock_delay(client: "TrezorClient", delay: str) -> str:
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
def flags(client: "TrezorClient", flags: str) -> str:
    """Set device flags."""
    if flags.lower().startswith("0b"):
        flags_int = int(flags, 2)
    elif flags.lower().startswith("0x"):
        flags_int = int(flags, 16)
    else:
        flags_int = int(flags)
    return device.apply_flags(client, flags=flags_int)


@cli.command()
@click.argument("filename")
@click.option(
    "-f", "--filename", "_ignore", is_flag=True, hidden=True, expose_value=False
)
@with_client
def homescreen(client: "TrezorClient", filename: str) -> str:
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
@click.option(
    "--always", is_flag=True, help='Persist the "prompt" setting across Trezor reboots.'
)
@click.argument("level", type=ChoiceType(SAFETY_LEVELS))
@with_client
def safety_checks(
    client: "TrezorClient", always: bool, level: messages.SafetyCheckLevel
) -> str:
    """Set safety check level.

    Set to "strict" to get the full Trezor security (default setting).

    Set to "prompt" if you want to be able to allow potentially unsafe actions, such as
    mismatching coin keys or extreme fees.

    This is a power-user feature. Use with caution.
    """
    if always and level == messages.SafetyCheckLevel.PromptTemporarily:
        level = messages.SafetyCheckLevel.PromptAlways
    return device.apply_settings(client, safety_checks=level)


@cli.command()
@click.argument("enable", type=ChoiceType({"on": True, "off": False}))
@with_client
def experimental_features(client: "TrezorClient", enable: bool) -> str:
    """Enable or disable experimental message types.

    This is a developer feature. Use with caution.
    """
    return device.apply_settings(client, experimental_features=enable)


#
# passphrase operations
#


# Using special class AliasedGroup, so we can support multiple commands
# to invoke the same function to keep backwards compatibility
@cli.command(cls=AliasedGroup, name="passphrase")
def passphrase_main() -> None:
    """Enable, disable or configure passphrase protection."""
    # this exists in order to support command aliases for "enable-passphrase"
    # and "disable-passphrase". Otherwise `passphrase` would just take an argument.


# Cast for type-checking purposes
passphrase = cast(AliasedGroup, passphrase_main)


@passphrase.command(name="on")
@click.option("-f/-F", "--force-on-device/--no-force-on-device", default=None)
@with_client
def passphrase_on(client: "TrezorClient", force_on_device: Optional[bool]) -> str:
    """Enable passphrase."""
    return device.apply_settings(
        client, use_passphrase=True, passphrase_always_on_device=force_on_device
    )


@passphrase.command(name="off")
@with_client
def passphrase_off(client: "TrezorClient") -> str:
    """Disable passphrase."""
    return device.apply_settings(client, use_passphrase=False)


# Registering the aliases for backwards compatibility
# (these are not shown in --help docs)
passphrase.aliases = {
    "enabled": passphrase_on,
    "disabled": passphrase_off,
}
