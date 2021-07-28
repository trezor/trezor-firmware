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

import sys

import click

from .. import debuglink, device, exceptions, messages, ui
from . import ChoiceType, with_client

RECOVERY_TYPE = {
    "scrambled": messages.RecoveryDeviceType.ScrambledWords,
    "matrix": messages.RecoveryDeviceType.Matrix,
}

BACKUP_TYPE = {
    "single": messages.BackupType.Bip39,
    "shamir": messages.BackupType.Slip39_Basic,
    "advanced": messages.BackupType.Slip39_Advanced,
}

SD_PROTECT_OPERATIONS = {
    "enable": messages.SdProtectOperationType.ENABLE,
    "disable": messages.SdProtectOperationType.DISABLE,
    "refresh": messages.SdProtectOperationType.REFRESH,
}


@click.group(name="device")
def cli():
    """Device management commands - setup, recover seed, wipe, etc."""


@cli.command()
@with_client
def self_test(client):
    """Perform a self-test."""
    return debuglink.self_test(client)


@cli.command()
@click.option(
    "-b",
    "--bootloader",
    help="Wipe device in bootloader mode. This also erases the firmware.",
    is_flag=True,
)
@with_client
def wipe(client, bootloader):
    """Reset device to factory defaults and remove all private data."""
    if bootloader:
        if not client.features.bootloader_mode:
            click.echo("Please switch your device to bootloader mode.")
            sys.exit(1)
        else:
            click.echo("Wiping user data and firmware!")
    else:
        if client.features.bootloader_mode:
            click.echo(
                "Your device is in bootloader mode. This operation would also erase firmware."
            )
            click.echo(
                'Specify "--bootloader" if that is what you want, or disconnect and reconnect device in normal mode.'
            )
            click.echo("Aborting.")
            sys.exit(1)
        else:
            click.echo("Wiping user data!")

    try:
        return device.wipe(client)
    except exceptions.TrezorFailure as e:
        click.echo("Action failed: {} {}".format(*e.args))
        sys.exit(3)


@cli.command()
@click.option("-m", "--mnemonic", multiple=True)
@click.option("-p", "--pin", default="")
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-l", "--label", default="")
@click.option("-i", "--ignore-checksum", is_flag=True)
@click.option("-s", "--slip0014", is_flag=True)
@click.option("-b", "--needs-backup", is_flag=True)
@click.option("-n", "--no-backup", is_flag=True)
@with_client
def load(
    client,
    mnemonic,
    pin,
    passphrase_protection,
    label,
    ignore_checksum,
    slip0014,
    needs_backup,
    no_backup,
):
    """Upload seed and custom configuration to the device.

    This functionality is only available in debug mode.
    """
    if slip0014 and mnemonic:
        raise click.ClickException("Cannot use -s and -m together.")

    if slip0014:
        mnemonic = [" ".join(["all"] * 12)]
        if not label:
            label = "SLIP-0014"

    return debuglink.load_device(
        client,
        mnemonic=list(mnemonic),
        pin=pin,
        passphrase_protection=passphrase_protection,
        label=label,
        language="en-US",
        skip_checksum=ignore_checksum,
        needs_backup=needs_backup,
        no_backup=no_backup,
    )


@cli.command()
@click.option("-w", "--words", type=click.Choice(["12", "18", "24"]), default="24")
@click.option("-e", "--expand", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-l", "--label")
@click.option("-u", "--u2f-counter", default=None, type=int)
@click.option(
    "-t", "--type", "rec_type", type=ChoiceType(RECOVERY_TYPE), default="scrambled"
)
@click.option("-d", "--dry-run", is_flag=True)
@with_client
def recover(
    client,
    words,
    expand,
    pin_protection,
    passphrase_protection,
    label,
    u2f_counter,
    rec_type,
    dry_run,
):
    """Start safe recovery workflow."""
    if rec_type == messages.RecoveryDeviceType.ScrambledWords:
        input_callback = ui.mnemonic_words(expand)
    else:
        input_callback = ui.matrix_words
        click.echo(ui.RECOVERY_MATRIX_DESCRIPTION)

    return device.recover(
        client,
        word_count=int(words),
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        u2f_counter=u2f_counter,
        language="en-US",
        input_callback=input_callback,
        type=rec_type,
        dry_run=dry_run,
    )


@cli.command()
@click.option("-e", "--show-entropy", is_flag=True)
@click.option("-t", "--strength", type=click.Choice(["128", "192", "256"]))
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-l", "--label")
@click.option("-u", "--u2f-counter", default=0)
@click.option("-s", "--skip-backup", is_flag=True)
@click.option("-n", "--no-backup", is_flag=True)
@click.option("-b", "--backup-type", type=ChoiceType(BACKUP_TYPE), default="single")
@with_client
def setup(
    client,
    show_entropy,
    strength,
    passphrase_protection,
    pin_protection,
    label,
    u2f_counter,
    skip_backup,
    no_backup,
    backup_type,
):
    """Perform device setup and generate new seed."""
    if strength:
        strength = int(strength)

    if (
        backup_type == messages.BackupType.Slip39_Basic
        and messages.Capability.Shamir not in client.features.capabilities
    ) or (
        backup_type == messages.BackupType.Slip39_Advanced
        and messages.Capability.ShamirGroups not in client.features.capabilities
    ):
        click.echo(
            "WARNING: Your Trezor device does not indicate support for the requested\n"
            "backup type. Traditional single-seed backup may be generated instead."
        )

    return device.reset(
        client,
        display_random=show_entropy,
        strength=strength,
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        language="en-US",
        u2f_counter=u2f_counter,
        skip_backup=skip_backup,
        no_backup=no_backup,
        backup_type=backup_type,
    )


@cli.command()
@with_client
def backup(client):
    """Perform device seed backup."""
    return device.backup(client)


@cli.command()
@click.argument("operation", type=ChoiceType(SD_PROTECT_OPERATIONS))
@with_client
def sd_protect(client, operation):
    """Secure the device with SD card protection.

    When SD card protection is enabled, a randomly generated secret is stored
    on the SD card. During every PIN checking and unlocking operation this
    secret is combined with the entered PIN value to decrypt data stored on
    the device. The SD card will thus be needed every time you unlock the
    device. The options are:

    \b
    enable - Generate SD card secret and use it to protect the PIN and storage.
    disable - Remove SD card secret protection.
    refresh - Replace the current SD card secret with a new one.
    """
    if client.features.model == "1":
        raise click.BadUsage("Trezor One does not support SD card protection.")
    return device.sd_protect(client, operation)


@cli.command()
@click.pass_obj
def reboot_to_bootloader(obj):
    """Reboot device into bootloader mode.

    Currently only supported on Trezor Model One.
    """
    # avoid using @with_client because it closes the session afterwards,
    # which triggers double prompt on device
    with obj.client_context() as client:
        if client.features.model != "1":
            click.echo(
                f"Warning: Rebooting into bootloader not supported on Trezor {client.features.model}"
            )
        return device.reboot_to_bootloader(client)
