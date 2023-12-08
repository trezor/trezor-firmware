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

import io
import logging
import secrets
import sys
from logging import DEBUG, ERROR, INFO, WARNING
from typing import TYPE_CHECKING, BinaryIO, Optional, Sequence, Tuple

import click

from .. import debuglink, device, exceptions, messages, ui
from . import ChoiceType, with_client

if TYPE_CHECKING:
    from ..client import TrezorClient
    from ..protobuf import MessageType
    from . import TrezorConnection

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
    "on": messages.SdProtectOperationType.ENABLE,
    "off": messages.SdProtectOperationType.DISABLE,
    "refresh": messages.SdProtectOperationType.REFRESH,
}

LOG = logging.getLogger(__name__)


@click.group(name="device")
def cli() -> None:
    """Device management commands - setup, recover seed, wipe, etc."""


@cli.command()
@with_client
def self_test(client: "TrezorClient") -> str:
    """Perform a factory self-test.

    Only available on PRODTEST firmware.
    """
    return debuglink.self_test(client)


@cli.command()
@click.option(
    "-b",
    "--bootloader",
    help="Wipe device in bootloader mode. This also erases the firmware.",
    is_flag=True,
)
@with_client
def wipe(client: "TrezorClient", bootloader: bool) -> str:
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
    client: "TrezorClient",
    mnemonic: Sequence[str],
    pin: str,
    passphrase_protection: bool,
    label: str,
    ignore_checksum: bool,
    slip0014: bool,
    needs_backup: bool,
    no_backup: bool,
) -> str:
    """Upload seed and custom configuration to the device.

    This functionality is only available in debug mode.
    """
    if slip0014 and mnemonic:
        raise click.ClickException("Cannot use -s and -m together.")

    if slip0014:
        mnemonic = [" ".join(["all"] * 12)]
        if not label:
            label = "SLIP-0014"

    try:
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
    "-t", "--type", "rec_type", type=ChoiceType(RECOVERY_TYPE), default="scrambled"
)
@click.option("-d", "--dry-run", is_flag=True)
@with_client
def recover(
    client: "TrezorClient",
    words: str,
    expand: bool,
    pin_protection: bool,
    passphrase_protection: bool,
    label: Optional[str],
    u2f_counter: int,
    rec_type: messages.RecoveryDeviceType,
    dry_run: bool,
) -> "MessageType":
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
    client: "TrezorClient",
    show_entropy: bool,
    strength: Optional[int],
    passphrase_protection: bool,
    pin_protection: bool,
    label: Optional[str],
    u2f_counter: int,
    skip_backup: bool,
    no_backup: bool,
    backup_type: messages.BackupType,
) -> str:
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
def backup(client: "TrezorClient") -> str:
    """Perform device seed backup."""
    return device.backup(client)


@cli.command()
@click.argument("operation", type=ChoiceType(SD_PROTECT_OPERATIONS))
@with_client
def sd_protect(
    client: "TrezorClient", operation: messages.SdProtectOperationType
) -> str:
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
    if client.features.model == "1":
        raise click.ClickException("Trezor One does not support SD card protection.")
    return device.sd_protect(client, operation)


@cli.command()
@click.pass_obj
def reboot_to_bootloader(obj: "TrezorConnection") -> str:
    """Reboot device into bootloader mode.

    Currently only supported on Trezor Model One.
    """
    # avoid using @with_client because it closes the session afterwards,
    # which triggers double prompt on device
    with obj.client_context() as client:
        return device.reboot_to_bootloader(client)


@cli.command()
@with_client
def tutorial(client: "TrezorClient") -> str:
    """Show on-device tutorial."""
    return device.show_device_tutorial(client)


@cli.command()
@with_client
def unlock_bootloader(client: "TrezorClient") -> str:
    """Unlocks bootloader. Irreversible."""
    return device.unlock_bootloader(client)


@cli.command()
@click.argument("enable", type=ChoiceType({"on": True, "off": False}), required=False)
@click.option(
    "-e",
    "--expiry",
    type=int,
    help="Dialog expiry in seconds.",
)
@with_client
def set_busy(
    client: "TrezorClient", enable: Optional[bool], expiry: Optional[int]
) -> str:
    """Show a "Do not disconnect" dialog."""
    if enable is False:
        return device.set_busy(client, None)

    if expiry is None:
        raise click.ClickException("Missing option '-e' / '--expiry'.")

    if expiry <= 0:
        raise click.ClickException(
            f"Invalid value for '-e' / '--expiry': '{expiry}' is not a positive integer."
        )

    return device.set_busy(client, expiry * 1000)


ROOT_PUBKEY_TS3 = bytes.fromhex(
    "04ca97480ac0d7b1e6efafe518cd433cec2bf8ab9822d76eafd34363b55d63e60"
    "380bff20acc75cde03cffcb50ab6f8ce70c878e37ebc58ff7cca0a83b16b15fa5"
)

TS3_CA_WHITELIST = [
    bytes.fromhex(x)
    for x in (
        "04b12efa295ad825a534b7c0bf276e93ad116434426763fa87bfa8a2f12e726906dcf566813f62eba8f8795f94dba0391c53682809cbbd7e4ba01d960b4f1c68f1",
        "04cb87d4c5d0fd5854e829f4c1b666e49a86c25c88a904c0feb66f1338faed0d7760010d7ea1a6474cbcfe1143bd4b5397a4e8b7fe86899113caecf42a984b0c0f",
        "0450c45878b2c6403a5a16e97a8957dc3ea36919bce9321b357f6e7ebe6257ee54102a2c2fa5cefed1dabc498fc76dc0bcf3c3a8a415eac7cc32e7c18185f25b0d",
        "0454d310d88d55d3044d80fcdbce9a63bf3118545fae71f6eca303272dcc4d25cf775ae3c18ae9f41b2cf29377bc4696fc79c8824a6fd6b9ca5fb6805ed6557aab",
        "04e94bf05586a8e7a3e9aba32662a439be5f378da372219c8ee7cf8b4684dbfbd7ba88ed920c06f9f26deab9077654647738df8cf70898fea1c3aaf2ef086fc578",
        "048c6c104bd7cc59cd5c5717533786a72ab59685bd13937f5542820e90f6ac6945e520e19d1d627a8e81ef5a94ef87de7a6a0d778e7dc9d389db877a5f9b629dd8",
    )
]

DEV_ROOT_PUBKEY_TS3 = bytes.fromhex(
    "047f77368dea2d4d61e989f474a56723c3212dacf8a808d8795595ef38441427c"
    "4389bc454f02089d7f08b873005e4c28d432468997871c0bf286fd3861e21e96a"
)


def _require_cryptography() -> None:
    try:
        import cryptography  # noqa: I900

        version = [int(x) for x in cryptography.__version__.split(".")]
        if version[0] < 41:
            click.echo(
                "You need to upgrade the 'cryptography' library to verify the signature."
            )
            click.echo("You can do so by running:")
            click.echo("  pip3 install --upgrade cryptography")
            sys.exit(1)

    except ImportError:
        click.echo(
            "You need to install the 'cryptography' library to verify the signature."
        )
        click.echo("You can do so by running:")
        click.echo("  pip3 install cryptography")
        sys.exit(1)


class Certificate:
    def __init__(self, cert_bytes: bytes) -> None:
        from cryptography import x509  # noqa: I900

        self.cert_bytes = cert_bytes
        self.cert = x509.load_der_x509_certificate(cert_bytes)

    def __str__(self) -> str:
        return self.cert.subject.rfc4514_string()

    def public_key(self) -> bytes:
        from cryptography.hazmat.primitives import serialization  # noqa: I900

        return self.cert.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )

    def verify(self, signature: bytes, message: bytes) -> None:
        from cryptography.hazmat.primitives import hashes  # noqa: I900
        from cryptography.hazmat.primitives.asymmetric import ec  # noqa: I900

        cert_pubkey = self.cert.public_key()
        assert isinstance(cert_pubkey, ec.EllipticCurvePublicKey)
        cert_pubkey.verify(
            self.fix_signature(signature),
            message,
            ec.ECDSA(hashes.SHA256()),
        )

    def verify_by(self, pubkey_bytes: bytes) -> None:
        from cryptography.hazmat.primitives.asymmetric import ec  # noqa: I900

        pubkey = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), pubkey_bytes
        )

        algo_params = self.cert.signature_algorithm_parameters
        assert isinstance(algo_params, ec.ECDSA)
        pubkey.verify(
            self.fix_signature(self.cert.signature),
            self.cert.tbs_certificate_bytes,
            algo_params,
        )

    def verify_issued_by(self, issuer: "Certificate") -> None:
        self.verify_by(issuer.public_key())

    @staticmethod
    def _decode_signature_permissive(sig_bytes: bytes) -> Tuple[int, int]:
        if len(sig_bytes) > 73:
            raise ValueError("Invalid DER signature: too long.")

        reader = io.BytesIO(sig_bytes)
        tag = reader.read(1)
        if tag != b"\x30":
            raise ValueError("Invalid DER signature: not a sequence.")
        length = reader.read(1)[0]
        if length != len(sig_bytes) - 2:
            raise ValueError("Invalid DER signature: invalid length.")

        def read_int() -> int:
            tag = reader.read(1)
            if tag != b"\x02":
                raise ValueError("Invalid DER signature: not an integer.")
            length = reader.read(1)[0]
            if length > 33:
                raise ValueError("Invalid DER signature: integer too long.")
            return int.from_bytes(reader.read(length), "big")

        r = read_int()
        s = read_int()
        if reader.tell() != len(sig_bytes):
            raise ValueError("Invalid DER signature: trailing data.")
        return r, s

    @staticmethod
    def fix_signature(sig_bytes: bytes) -> bytes:
        from cryptography.hazmat.primitives.asymmetric import utils  # noqa: I900

        r, s = Certificate._decode_signature_permissive(sig_bytes)
        reencoded = utils.encode_dss_signature(r, s)
        if reencoded != sig_bytes:
            LOG.info(
                "Re-encoding malformed signature: %s -> %s",
                sig_bytes.hex(),
                reencoded.hex(),
            )
        return reencoded


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
@with_client
def authenticate(
    client: "TrezorClient",
    hex_challenge: Optional[str],
    root: Optional[BinaryIO],
    raw: Optional[bool],
    skip_whitelist: Optional[bool],
) -> None:
    """Verify the authenticity of the device.

    Use the --raw option to get the raw challenge, signature, and certificate data.

    Otherwise, trezorctl will attempt to decode the signatures and check their
    authenticity. By default, it will also check the public keys against a built-in
    whitelist, and in the future also against a whitelist downloaded from Trezor
    servers. You can skip this check with the --skip-whitelist option.

    \b
    When not using --raw, 'cryptography' library is required. You can install it via:
      pip3 install cryptography
    """
    if hex_challenge is None:
        hex_challenge = secrets.token_hex(32)

    challenge = bytes.fromhex(hex_challenge)
    msg = device.authenticate(client, challenge)

    if raw:
        click.echo(f"Challenge: {hex_challenge}")
        click.echo(f"Signature of challenge: {msg.signature.hex()}")
        click.echo(f"Device certificate: {msg.certificates[0].hex()}")
        for cert in msg.certificates[1:]:
            click.echo(f"CA certificate: {cert.hex()}")
        return

    _require_cryptography()

    worst_level = DEBUG

    def print_step(level: int, text: str) -> None:
        nonlocal worst_level

        worst_level = max(worst_level, level)
        if level == ERROR:
            level_str = click.style("ERROR", fg="red")
        elif level == WARNING:
            level_str = click.style("WARNING", fg="yellow")
        elif level == INFO:
            level_str = click.style("INFO", fg="blue")
        elif level == DEBUG:
            level_str = click.style("OK", fg="green")
        else:
            raise RuntimeError("Invalid log level")

        click.echo(f"[{level_str}] {text}")

    from cryptography import exceptions  # noqa: I900

    CHALLENGE_HEADER = b"AuthenticateDevice:"
    challenge_bytes = (
        len(CHALLENGE_HEADER).to_bytes(1, "big")
        + CHALLENGE_HEADER
        + len(challenge).to_bytes(1, "big")
        + challenge
    )

    try:
        first_cert = Certificate(msg.certificates[0])
    except Exception:
        print_step(ERROR, "Failed to parse device certificate.")
        sys.exit(5)

    try:
        first_cert.verify(msg.signature, challenge_bytes)
    except exceptions.InvalidSignature:
        print_step(ERROR, "Challenge verification failed.")
    else:
        print_step(DEBUG, "Challenge verified successfully.")

    for issuer in msg.certificates[1:]:
        try:
            cert = Certificate(issuer)
        except Exception:
            print_step(ERROR, "Failed to parse CA certificate.")
            continue

        if skip_whitelist:
            print_step(INFO, "Skipping public key whitelist check.")
        else:
            if cert.public_key() not in TS3_CA_WHITELIST:
                print_step(WARNING, f"CA certificate not in whitelist: {cert}")

        try:
            first_cert.verify_issued_by(cert)
        except exceptions.InvalidSignature:
            print_step(ERROR, f"Certificate verification failed: {cert}")
            continue
        else:
            print_step(DEBUG, f"Certificate verified successfully: {cert}")

        first_cert = cert

    roots = [
        (DEBUG, "Trezor Company", ROOT_PUBKEY_TS3),
        (ERROR, "TESTING ENVIRONMENT. DO NOT USE THIS DEVICE", DEV_ROOT_PUBKEY_TS3),
    ]
    if root is not None:
        try:
            root_cert = Certificate(root.read())
            roots.append(
                (INFO, "the specified root certificate", root_cert.public_key())
            )
        except Exception:
            print_step(ERROR, "Failed to parse provided root certificate.")

    for level, issuer, pubkey in roots:
        try:
            first_cert.verify_by(pubkey)
            print_step(level, f"Certificate issued by {issuer}: {first_cert}")
            break
        except Exception:
            continue

    if worst_level >= ERROR:
        sys.exit(2)
    elif worst_level >= WARNING:
        sys.exit(1)
