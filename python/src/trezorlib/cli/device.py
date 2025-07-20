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
from __future__ import annotations

import logging
import secrets
import sys
import typing as t

import click
import requests

from .. import authentication, debuglink, device, exceptions, messages, ui
from ..tools import format_path
from . import ChoiceType, with_session

if t.TYPE_CHECKING:
    from ..transport.session import Session
    from . import TrezorConnection

RECOVERY_DEVICE_INPUT_METHOD = {
    "scrambled": messages.RecoveryDeviceInputMethod.ScrambledWords,
    "matrix": messages.RecoveryDeviceInputMethod.Matrix,
}

BACKUP_TYPE = {
    "bip39": messages.BackupType.Bip39,
    "single": messages.BackupType.Slip39_Single_Extendable,
    "shamir": messages.BackupType.Slip39_Basic,
    "advanced": messages.BackupType.Slip39_Advanced,
}

SD_PROTECT_OPERATIONS = {
    "on": messages.SdProtectOperationType.ENABLE,
    "off": messages.SdProtectOperationType.DISABLE,
    "refresh": messages.SdProtectOperationType.REFRESH,
}

LOG = logging.getLogger(__name__)


@click.group(name="device")
def cli() -> None:
    """Device management commands - setup, recover seed, wipe, etc."""


@cli.command()
@click.option(
    "-b",
    "--bootloader",
    help="Wipe device in bootloader mode. This also erases the firmware.",
    is_flag=True,
)
@with_session(seedless=True)
def wipe(session: "Session", bootloader: bool) -> None:
    """Reset device to factory defaults and remove all private data."""
    features = session.features
    if bootloader:
        if not features.bootloader_mode:
            click.echo("Please switch your device to bootloader mode.")
            sys.exit(1)
        else:
            click.echo("Wiping user data and firmware!")
    else:
        if features.bootloader_mode:
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
        device.wipe(session)
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
@click.option("-a", "--academic", is_flag=True)
@click.option("-b", "--needs-backup", is_flag=True)
@click.option("-n", "--no-backup", is_flag=True)
@with_session(seedless=True)
def load(
    session: "Session",
    mnemonic: t.Sequence[str],
    pin: str,
    passphrase_protection: bool,
    label: str,
    ignore_checksum: bool,
    slip0014: bool,
    academic: bool,
    needs_backup: bool,
    no_backup: bool,
) -> None:
    """Upload seed and custom configuration to the device.

    This functionality is only available in debug mode.
    """
    if sum((slip0014, academic, bool(mnemonic))) > 1:
        raise click.ClickException("Cannot use the options -a, -m, and -s together.")

    if slip0014:
        mnemonic = [" ".join(["all"] * 12)]
        if not label:
            label = "SLIP-0014"
    elif academic:
        mnemonic = [
            "academic again academic academic academic academic academic academic academic academic academic academic academic academic academic academic academic pecan provide remember"
        ]
        if not label:
            label = "ACADEMIC"

    try:
        debuglink.load_device(
            session,
            mnemonic=list(mnemonic),
            pin=pin,
            passphrase_protection=passphrase_protection,
            label=label,
            skip_checksum=ignore_checksum,
            needs_backup=needs_backup,
            no_backup=no_backup,
        )
    except exceptions.TrezorFailure as e:
        if e.code == messages.FailureType.UnexpectedMessage:
            raise click.ClickException(
                "Unrecognized message. Make sure your Trezor is using debug firmware."
            )
        else:
            raise


@cli.command()
@click.option("-w", "--words", type=click.Choice(["12", "18", "24"]), default="24")
@click.option("-e", "--expand", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-l", "--label")
@click.option("-u", "--u2f-counter", default=None, type=int)
@click.option(
    "-i",
    "--input_method",
    "-t",
    "--type",
    type=ChoiceType(RECOVERY_DEVICE_INPUT_METHOD),
    default="scrambled",
)
@click.option("-d", "--dry-run", is_flag=True)
@click.option("-b", "--unlock-repeated-backup", is_flag=True)
@with_session(seedless=True)
def recover(
    session: "Session",
    words: str,
    expand: bool,
    pin_protection: bool,
    passphrase_protection: bool,
    label: str | None,
    u2f_counter: int,
    input_method: messages.RecoveryDeviceInputMethod,
    dry_run: bool,
    unlock_repeated_backup: bool,
) -> None:
    """Start safe recovery workflow."""
    if input_method == messages.RecoveryDeviceInputMethod.ScrambledWords:
        input_callback = ui.mnemonic_words(expand)
    else:
        input_callback = ui.matrix_words
        click.echo(ui.RECOVERY_MATRIX_DESCRIPTION)

    if dry_run and unlock_repeated_backup:
        raise click.ClickException("Cannot use -d and -b together.")

    type = None
    if dry_run:
        type = messages.RecoveryType.DryRun
    if unlock_repeated_backup:
        type = messages.RecoveryType.UnlockRepeatedBackup

    device.recover(
        session,
        word_count=int(words),
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        u2f_counter=u2f_counter,
        input_callback=input_callback,
        input_method=input_method,
        type=type,
    )


@cli.command()
@click.option("-t", "--strength", type=click.Choice(["128", "192", "256"]))
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-l", "--label")
@click.option("-u", "--u2f-counter", default=0)
@click.option("-s", "--skip-backup", is_flag=True)
@click.option("-n", "--no-backup", is_flag=True)
@click.option("-b", "--backup-type", type=ChoiceType(BACKUP_TYPE))
@click.option("-e", "--entropy-check-count", type=click.IntRange(0))
@with_session(seedless=True)
def setup(
    session: "Session",
    strength: int | None,
    passphrase_protection: bool,
    pin_protection: bool,
    label: str | None,
    u2f_counter: int,
    skip_backup: bool,
    no_backup: bool,
    backup_type: messages.BackupType | None,
    entropy_check_count: int | None,
) -> None:
    """Perform device setup and generate new seed."""
    if strength:
        strength = int(strength)

    BT = messages.BackupType

    if (
        backup_type
        in (BT.Slip39_Single_Extendable, BT.Slip39_Basic, BT.Slip39_Basic_Extendable)
        and messages.Capability.Shamir not in session.features.capabilities
    ) or (
        backup_type in (BT.Slip39_Advanced, BT.Slip39_Advanced_Extendable)
        and messages.Capability.ShamirGroups not in session.features.capabilities
    ):
        click.echo(
            "WARNING: Your Trezor device does not indicate support for the requested\n"
            "backup type. Traditional BIP39 backup may be generated instead."
        )

    path_xpubs = device.setup(
        session,
        strength=strength,
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        u2f_counter=u2f_counter,
        skip_backup=skip_backup,
        no_backup=no_backup,
        backup_type=backup_type,
        entropy_check_count=entropy_check_count,
    )

    if path_xpubs:
        click.echo("XPUBs for the generated seed")
        for path, xpub in path_xpubs:
            click.echo(f"{format_path(path)}: {xpub}")


@cli.command()
@click.option("-t", "--group-threshold", type=int)
@click.option("-g", "--group", "groups", type=(int, int), multiple=True, metavar="T N")
@with_session(seedless=True)
def backup(
    session: "Session",
    group_threshold: int | None = None,
    groups: t.Sequence[tuple[int, int]] = (),
) -> None:
    """Perform device seed backup."""

    device.backup(session, group_threshold, groups)


@cli.command()
@click.argument("operation", type=ChoiceType(SD_PROTECT_OPERATIONS))
@with_session(seedless=True)
def sd_protect(session: "Session", operation: messages.SdProtectOperationType) -> None:
    """Secure the device with SD card protection.

    When SD card protection is enabled, a randomly generated secret is stored
    on the SD card. During every PIN checking and unlocking operation this
    secret is combined with the entered PIN value to decrypt data stored on
    the device. The SD card will thus be needed every time you unlock the
    device. The options are:

    \b
    on - Generate SD card secret and use it to protect the PIN and storage.
    off - Remove SD card secret protection.
    refresh - Replace the current SD card secret with a new one.
    """
    if session.features.model == "1":
        raise click.ClickException("Trezor One does not support SD card protection.")
    device.sd_protect(session, operation)


@cli.command()
@click.pass_obj
def reboot_to_bootloader(obj: "TrezorConnection") -> None:
    """Reboot device into bootloader mode."""
    # avoid using @with_session because it closes the session afterwards,
    # which triggers double prompt on device
    with obj.client_context() as client:
        device.reboot_to_bootloader(client.get_seedless_session())


@cli.command()
@with_session(seedless=True)
def tutorial(session: "Session") -> None:
    """Show on-device tutorial."""
    device.show_device_tutorial(session)


@cli.command()
@with_session(seedless=True)
def unlock_bootloader(session: "Session") -> None:
    """Unlocks bootloader. Irreversible."""
    device.unlock_bootloader(session)


@cli.command()
@click.argument("enable", type=ChoiceType({"on": True, "off": False}), required=False)
@click.option(
    "-e",
    "--expiry",
    type=int,
    help="Dialog expiry in seconds.",
)
@with_session(seedless=True)
def set_busy(session: "Session", enable: bool | None, expiry: int | None) -> None:
    """Show a "Do not disconnect" dialog."""
    if enable is False:
        device.set_busy(session, None)

    if expiry is None:
        raise click.ClickException("Missing option '-e' / '--expiry'.")

    if expiry <= 0:
        raise click.ClickException(
            f"Invalid value for '-e' / '--expiry': '{expiry}' is not a positive integer."
        )

    device.set_busy(session, expiry * 1000)


PUBKEY_WHITELIST_URL_TEMPLATE = (
    "https://data.trezor.io/firmware/{model}/authenticity.json"
)


@cli.command()
@click.argument("hex_challenge", required=False)
@click.option("-R", "--root", type=click.File("rb"), help="Custom root certificate.")
@click.option(
    "-r", "--raw", is_flag=True, help="Print raw cryptographic data and exit."
)
@click.option(
    "-s",
    "--skip-whitelist",
    is_flag=True,
    help="Do not check intermediate certificates against the whitelist.",
)
@with_session(seedless=True)
def authenticate(
    session: "Session",
    hex_challenge: str | None,
    root: t.BinaryIO | None,
    raw: bool | None,
    skip_whitelist: bool | None,
) -> None:
    """Verify the authenticity of the device.

    Use the --raw option to get the raw challenge, signature, and certificate data.

    Otherwise, trezorctl will attempt to decode the signatures and check their
    authenticity. By default, it will also check the public keys against a whitelist
    downloaded from Trezor servers. You can skip this check with the --skip-whitelist
    option.
    """
    if hex_challenge is None:
        hex_challenge = secrets.token_hex(32)

    challenge = bytes.fromhex(hex_challenge)

    if raw:
        msg = device.authenticate(session, challenge)

        click.echo(f"Challenge: {hex_challenge}")
        click.echo(f"Signature of challenge: {msg.signature.hex()}")
        click.echo(f"Device certificate: {msg.certificates[0].hex()}")
        for cert in msg.certificates[1:]:
            click.echo(f"CA certificate: {cert.hex()}")
        return

    if root is not None:
        root_bytes = root.read()
    else:
        root_bytes = None

    class ColoredFormatter(logging.Formatter):
        LEVELS = {
            logging.ERROR: click.style("ERROR", fg="red"),
            logging.WARNING: click.style("WARNING", fg="yellow"),
            logging.INFO: click.style("INFO", fg="blue"),
            logging.DEBUG: click.style("OK", fg="green"),
        }

        def format(self, record: logging.LogRecord) -> str:
            prefix = self.LEVELS[record.levelno]
            bold_args = tuple(
                click.style(str(arg), bold=True) for arg in record.args or ()
            )
            return f"[{prefix}] {record.msg}" % bold_args

    handler = logging.StreamHandler()
    handler.setFormatter(ColoredFormatter())
    authentication.LOG.addHandler(handler)
    authentication.LOG.setLevel(logging.DEBUG)

    if skip_whitelist:
        whitelist = None
    else:
        whitelist_json = requests.get(
            PUBKEY_WHITELIST_URL_TEMPLATE.format(
                model=session.model.internal_name.lower()
            )
        ).json()
        whitelist = [bytes.fromhex(pk) for pk in whitelist_json["ca_pubkeys"]]

    try:
        authentication.authenticate_device(
            session, challenge, root_pubkey=root_bytes, whitelist=whitelist
        )
    except authentication.DeviceNotAuthentic:
        click.echo("Device is not authentic.")
        sys.exit(5)
