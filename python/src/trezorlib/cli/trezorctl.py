#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) 2012-2017 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2017 Pavol Rusnak <stick@satoshilabs.com>
# Copyright (C) 2016-2017 Jochen Hoenicke <hoenicke@gmail.com>
# Copyright (C) 2017      mruddy
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

import base64
import json
import os
import re
import sys
from decimal import Decimal

import click
import requests

from trezorlib import (
    binance,
    btc,
    cardano,
    coins,
    cosi,
    debuglink,
    device,
    eos,
    ethereum,
    exceptions,
    firmware,
    lisk,
    log,
    messages as proto,
    misc,
    monero,
    nem,
    protobuf,
    ripple,
    stellar,
    tezos,
    tools,
    ui,
)
from trezorlib.client import TrezorClient
from trezorlib.transport import enumerate_devices, get_transport

try:
    import rlp
    import web3

    ETHEREUM_SIGN_TX = True
except Exception:
    ETHEREUM_SIGN_TX = False


class ChoiceType(click.Choice):
    def __init__(self, typemap):
        super(ChoiceType, self).__init__(typemap.keys())
        self.typemap = typemap

    def convert(self, value, param, ctx):
        value = super(ChoiceType, self).convert(value, param, ctx)
        return self.typemap[value]


CHOICE_PASSPHRASE_SOURCE_TYPE = ChoiceType(
    {
        "ask": proto.PassphraseSourceType.ASK,
        "device": proto.PassphraseSourceType.DEVICE,
        "host": proto.PassphraseSourceType.HOST,
    }
)


CHOICE_DISPLAY_ROTATION_TYPE = ChoiceType(
    {"north": 0, "east": 90, "south": 180, "west": 270}
)


CHOICE_RECOVERY_DEVICE_TYPE = ChoiceType(
    {
        "scrambled": proto.RecoveryDeviceType.ScrambledWords,
        "matrix": proto.RecoveryDeviceType.Matrix,
    }
)

CHOICE_INPUT_SCRIPT_TYPE = ChoiceType(
    {
        "address": proto.InputScriptType.SPENDADDRESS,
        "segwit": proto.InputScriptType.SPENDWITNESS,
        "p2shsegwit": proto.InputScriptType.SPENDP2SHWITNESS,
    }
)

CHOICE_OUTPUT_SCRIPT_TYPE = ChoiceType(
    {
        "address": proto.OutputScriptType.PAYTOADDRESS,
        "segwit": proto.OutputScriptType.PAYTOWITNESS,
        "p2shsegwit": proto.OutputScriptType.PAYTOP2SHWITNESS,
    }
)

CHOICE_RESET_DEVICE_TYPE = ChoiceType(
    {
        "single": proto.BackupType.Bip39,
        "shamir": proto.BackupType.Slip39_Basic,
        "advanced": proto.BackupType.Slip39_Advanced,
    }
)


class UnderscoreAgnosticGroup(click.Group):
    """Command group that normalizes dashes and underscores.

    Click 7.0 silently switched all underscore_commands to dash-commands.
    This implementation of `click.Group` responds to underscore_commands by invoking
    the respective dash-command.
    """

    def get_command(self, ctx, cmd_name):
        cmd = super().get_command(ctx, cmd_name)
        if cmd is None:
            cmd = super().get_command(ctx, cmd_name.replace("_", "-"))
        return cmd


def enable_logging():
    log.enable_debug_output()
    log.OMITTED_MESSAGES.add(proto.Features)


@click.command(cls=UnderscoreAgnosticGroup, context_settings={"max_content_width": 400})
@click.option(
    "-p",
    "--path",
    help="Select device by specific path.",
    default=os.environ.get("TREZOR_PATH"),
)
@click.option("-v", "--verbose", is_flag=True, help="Show communication messages.")
@click.option(
    "-j", "--json", "is_json", is_flag=True, help="Print result as JSON object"
)
@click.pass_context
def cli(ctx, path, verbose, is_json):
    if verbose:
        enable_logging()

    def get_device():
        try:
            device = get_transport(path, prefix_search=False)
        except Exception:
            try:
                device = get_transport(path, prefix_search=True)
            except Exception:
                click.echo("Failed to find a Trezor device.")
                if path is not None:
                    click.echo("Using path: {}".format(path))
                sys.exit(1)
        return TrezorClient(transport=device, ui=ui.ClickUI())

    ctx.obj = get_device


@cli.resultcallback()
def print_result(res, path, verbose, is_json):
    if is_json:
        if isinstance(res, protobuf.MessageType):
            click.echo(json.dumps({res.__class__.__name__: res.__dict__}))
        else:
            click.echo(json.dumps(res, sort_keys=True, indent=4))
    else:
        if isinstance(res, list):
            for line in res:
                click.echo(line)
        elif isinstance(res, dict):
            for k, v in res.items():
                if isinstance(v, dict):
                    for kk, vv in v.items():
                        click.echo("%s.%s: %s" % (k, kk, vv))
                else:
                    click.echo("%s: %s" % (k, v))
        elif isinstance(res, protobuf.MessageType):
            click.echo(protobuf.format_message(res))
        else:
            click.echo(res)


#
# Common functions
#


@cli.command(name="list", help="List connected Trezor devices.")
def ls():
    return enumerate_devices()


@cli.command(help="Show version of trezorctl/trezorlib.")
def version():
    from trezorlib import __version__ as VERSION

    return VERSION


#
# Basic device functions
#


@cli.command(help="Send ping message.")
@click.argument("message")
@click.option("-b", "--button-protection", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.pass_obj
def ping(connect, message, button_protection, pin_protection, passphrase_protection):
    return connect().ping(
        message,
        button_protection=button_protection,
        pin_protection=pin_protection,
        passphrase_protection=passphrase_protection,
    )


@cli.command(help="Clear session (remove cached PIN, passphrase, etc.).")
@click.pass_obj
def clear_session(connect):
    return connect().clear_session()


@cli.command(help="Get example entropy.")
@click.argument("size", type=int)
@click.pass_obj
def get_entropy(connect, size):
    return misc.get_entropy(connect(), size).hex()


@cli.command(help="Retrieve device features and settings.")
@click.pass_obj
def get_features(connect):
    return connect().features


#
# Device management functions
#


@cli.command(help="Change new PIN or remove existing.")
@click.option("-r", "--remove", is_flag=True)
@click.pass_obj
def change_pin(connect, remove):
    return device.change_pin(connect(), remove)


@cli.command(help="Enable passphrase.")
@click.pass_obj
def enable_passphrase(connect):
    return device.apply_settings(connect(), use_passphrase=True)


@cli.command(help="Disable passphrase.")
@click.pass_obj
def disable_passphrase(connect):
    return device.apply_settings(connect(), use_passphrase=False)


@cli.command(help="Set new device label.")
@click.option("-l", "--label")
@click.pass_obj
def set_label(connect, label):
    return device.apply_settings(connect(), label=label)


@cli.command()
@click.argument("source", type=CHOICE_PASSPHRASE_SOURCE_TYPE)
@click.pass_obj
def set_passphrase_source(connect, source):
    """Set passphrase source.

    Configure how to enter passphrase on Trezor Model T. The options are:

    \b
    ask - always ask where to enter passphrase
    device - always enter passphrase on device
    host - always enter passphrase on host
    """
    return device.apply_settings(connect(), passphrase_source=source)


@cli.command()
@click.argument("rotation", type=CHOICE_DISPLAY_ROTATION_TYPE)
@click.pass_obj
def set_display_rotation(connect, rotation):
    """Set display rotation.

    Configure display rotation for Trezor Model T. The options are
    north, east, south or west.
    """
    return device.apply_settings(connect(), display_rotation=rotation)


@cli.command(help="Set auto-lock delay (in seconds).")
@click.argument("delay", type=str)
@click.pass_obj
def set_auto_lock_delay(connect, delay):
    value, unit = delay[:-1], delay[-1:]
    units = {"s": 1, "m": 60, "h": 3600}
    if unit in units:
        seconds = float(value) * units[unit]
    else:
        seconds = float(delay)  # assume seconds if no unit is specified
    return device.apply_settings(connect(), auto_lock_delay_ms=int(seconds * 1000))


@cli.command(help="Set device flags.")
@click.argument("flags")
@click.pass_obj
def set_flags(connect, flags):
    flags = flags.lower()
    if flags.startswith("0b"):
        flags = int(flags, 2)
    elif flags.startswith("0x"):
        flags = int(flags, 16)
    else:
        flags = int(flags)
    return device.apply_flags(connect(), flags=flags)


@cli.command(help="Set new homescreen.")
@click.option("-f", "--filename", default=None)
@click.pass_obj
def set_homescreen(connect, filename):
    if filename is None:
        img = b"\x00"
    elif filename.endswith(".toif"):
        img = open(filename, "rb").read()
        if img[:8] != b"TOIf\x90\x00\x90\x00":
            raise tools.CallException(
                proto.FailureType.DataError,
                "File is not a TOIF file with size of 144x144",
            )
    else:
        from PIL import Image

        im = Image.open(filename)
        if im.size != (128, 64):
            raise tools.CallException(
                proto.FailureType.DataError, "Wrong size of the image"
            )
        im = im.convert("1")
        pix = im.load()
        img = bytearray(1024)
        for j in range(64):
            for i in range(128):
                if pix[i, j]:
                    o = i + j * 128
                    img[o // 8] |= 1 << (7 - o % 8)
        img = bytes(img)
    return device.apply_settings(connect(), homescreen=img)


@cli.command(help="Set U2F counter.")
@click.argument("counter", type=int)
@click.pass_obj
def set_u2f_counter(connect, counter):
    return device.set_u2f_counter(connect(), counter)


@cli.command(help="Reset device to factory defaults and remove all private data.")
@click.option(
    "-b",
    "--bootloader",
    help="Wipe device in bootloader mode. This also erases the firmware.",
    is_flag=True,
)
@click.pass_obj
def wipe_device(connect, bootloader):
    client = connect()
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
        return device.wipe(connect())
    except tools.CallException as e:
        click.echo("Action failed: {} {}".format(*e.args))
        sys.exit(3)


@cli.command(help="Load custom configuration to the device.")
@click.option("-m", "--mnemonic", multiple=True)
@click.option("-e", "--expand", is_flag=True)
@click.option("-x", "--xprv")
@click.option("-p", "--pin", default="")
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-l", "--label", default="")
@click.option("-i", "--ignore-checksum", is_flag=True)
@click.option("-s", "--slip0014", is_flag=True)
@click.pass_obj
def load_device(
    connect,
    mnemonic,
    expand,
    xprv,
    pin,
    passphrase_protection,
    label,
    ignore_checksum,
    slip0014,
):
    n_args = sum(bool(a) for a in (mnemonic, xprv, slip0014))
    if n_args == 0:
        raise click.ClickException("Please provide a mnemonic or xprv")
    if n_args > 1:
        raise click.ClickException("Cannot use mnemonic and xprv together")

    client = connect()

    if xprv:
        return debuglink.load_device_by_xprv(
            client, xprv, pin, passphrase_protection, label, "english"
        )

    if slip0014:
        mnemonic = [" ".join(["all"] * 12)]

    return debuglink.load_device_by_mnemonic(
        client,
        list(mnemonic),
        pin,
        passphrase_protection,
        label,
        "english",
        ignore_checksum,
    )


@cli.command(help="Start safe recovery workflow.")
@click.option("-w", "--words", type=click.Choice(["12", "18", "24"]), default="24")
@click.option("-e", "--expand", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-l", "--label")
@click.option(
    "-t", "--type", "rec_type", type=CHOICE_RECOVERY_DEVICE_TYPE, default="scrambled"
)
@click.option("-d", "--dry-run", is_flag=True)
@click.pass_obj
def recovery_device(
    connect,
    words,
    expand,
    pin_protection,
    passphrase_protection,
    label,
    rec_type,
    dry_run,
):
    if rec_type == proto.RecoveryDeviceType.ScrambledWords:
        input_callback = ui.mnemonic_words(expand)
    else:
        input_callback = ui.matrix_words
        click.echo(ui.RECOVERY_MATRIX_DESCRIPTION)

    return device.recover(
        connect(),
        word_count=int(words),
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        language="english",
        input_callback=input_callback,
        type=rec_type,
        dry_run=dry_run,
    )


@cli.command(help="Perform device setup and generate new seed.")
@click.option("-e", "--show-entropy", is_flag=True)
@click.option("-t", "--strength", type=click.Choice(["128", "192", "256"]))
@click.option("-r", "--passphrase-protection", is_flag=True)
@click.option("-p", "--pin-protection", is_flag=True)
@click.option("-l", "--label")
@click.option("-u", "--u2f-counter", default=0)
@click.option("-s", "--skip-backup", is_flag=True)
@click.option("-n", "--no-backup", is_flag=True)
@click.option("-b", "--backup-type", type=CHOICE_RESET_DEVICE_TYPE, default="single")
@click.pass_obj
def reset_device(
    connect,
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
    if strength:
        strength = int(strength)

    client = connect()
    if client.features.model == "1" and backup_type != proto.BackupType.Bip39:
        click.echo(
            "WARNING: Trezor One currently does not support Shamir backup.\n"
            "Traditional single-seed backup will be generated instead."
        )

    return device.reset(
        client,
        display_random=show_entropy,
        strength=strength,
        passphrase_protection=passphrase_protection,
        pin_protection=pin_protection,
        label=label,
        language="english",
        u2f_counter=u2f_counter,
        skip_backup=skip_backup,
        no_backup=no_backup,
        backup_type=backup_type,
    )


@cli.command(help="Perform device seed backup.")
@click.pass_obj
def backup_device(connect):
    return device.backup(connect())


#
# Firmware update
#


ALLOWED_FIRMWARE_FORMATS = {
    1: (firmware.FirmwareFormat.TREZOR_ONE, firmware.FirmwareFormat.TREZOR_ONE_V2),
    2: (firmware.FirmwareFormat.TREZOR_T,),
}


def _print_version(version):
    vstr = "Firmware version {major}.{minor}.{patch} build {build}".format(**version)
    click.echo(vstr)


def validate_firmware(version, fw, expected_fingerprint=None):
    if version == firmware.FirmwareFormat.TREZOR_ONE:
        if fw.embedded_onev2:
            click.echo("Trezor One firmware with embedded v2 image (1.8.0 or later)")
            _print_version(fw.embedded_onev2.firmware_header.version)
        else:
            click.echo("Trezor One firmware image.")
    elif version == firmware.FirmwareFormat.TREZOR_ONE_V2:
        click.echo("Trezor One v2 firmware (1.8.0 or later)")
        _print_version(fw.firmware_header.version)
    elif version == firmware.FirmwareFormat.TREZOR_T:
        click.echo("Trezor T firmware image.")
        vendor = fw.vendor_header.vendor_string
        vendor_version = "{major}.{minor}".format(**fw.vendor_header.version)
        click.echo("Vendor header from {}, version {}".format(vendor, vendor_version))
        _print_version(fw.firmware_header.version)

    try:
        firmware.validate(version, fw, allow_unsigned=False)
        click.echo("Signatures are valid.")
    except firmware.Unsigned:
        if not click.confirm("No signatures found. Continue?", default=False):
            sys.exit(1)
        try:
            firmware.validate(version, fw, allow_unsigned=True)
            click.echo("Unsigned firmware looking OK.")
        except firmware.FirmwareIntegrityError as e:
            click.echo(e)
            click.echo("Firmware validation failed, aborting.")
            sys.exit(4)
    except firmware.FirmwareIntegrityError as e:
        click.echo(e)
        click.echo("Firmware validation failed, aborting.")
        sys.exit(4)

    fingerprint = firmware.digest(version, fw).hex()
    click.echo("Firmware fingerprint: {}".format(fingerprint))
    if expected_fingerprint and fingerprint != expected_fingerprint:
        click.echo("Expected fingerprint: {}".format(expected_fingerprint))
        click.echo("Fingerprints do not match, aborting.")
        sys.exit(5)


def find_best_firmware_version(bootloader_version, requested_version=None, beta=False):
    if beta:
        url = "https://beta-wallet.trezor.io/data/firmware/{}/releases.json"
    else:
        url = "https://wallet.trezor.io/data/firmware/{}/releases.json"
    releases = requests.get(url.format(bootloader_version[0])).json()
    if not releases:
        raise click.ClickException("Failed to get list of releases")

    releases.sort(key=lambda r: r["version"], reverse=True)

    def version_str(version):
        return ".".join(map(str, version))

    want_version = requested_version

    if want_version is None:
        want_version = releases[0]["version"]
        click.echo("Best available version: {}".format(version_str(want_version)))

    confirm_different_version = False
    while True:
        want_version_str = version_str(want_version)
        try:
            release = next(r for r in releases if r["version"] == want_version)
        except StopIteration:
            click.echo("Version {} not found.".format(want_version_str))
            sys.exit(1)

        if (
            "min_bootloader_version" in release
            and release["min_bootloader_version"] > bootloader_version
        ):
            need_version_str = version_str(release["min_firmware_version"])
            click.echo(
                "Version {} is required before upgrading to {}.".format(
                    need_version_str, want_version_str
                )
            )
            want_version = release["min_firmware_version"]
            confirm_different_version = True
        else:
            break

    if confirm_different_version:
        installing_different = "Installing version {} instead.".format(want_version_str)
        if requested_version is None:
            click.echo(installing_different)
        else:
            ok = click.confirm(installing_different + " Continue?", default=True)
            if not ok:
                sys.exit(1)

    if beta:
        url = "https://beta-wallet.trezor.io/" + release["url"]
    else:
        url = "https://wallet.trezor.io/" + release["url"]
    if url.endswith(".hex"):
        url = url[:-4]

    return url, release["fingerprint"]


@cli.command()
# fmt: off
@click.option("-f", "--filename")
@click.option("-u", "--url")
@click.option("-v", "--version")
@click.option("-s", "--skip-check", is_flag=True, help="Do not validate firmware integrity")
@click.option("-n", "--dry-run", is_flag=True, help="Perform all steps but do not actually upload the firmware")
@click.option("--beta", is_flag=True, help="Use firmware from BETA wallet")
@click.option("--raw", is_flag=True, help="Push raw data to Trezor")
@click.option("--fingerprint", help="Expected firmware fingerprint in hex")
@click.option("--skip-vendor-header", help="Skip vendor header validation on Trezor T")
# fmt: on
@click.pass_obj
def firmware_update(
    connect,
    filename,
    url,
    version,
    skip_check,
    fingerprint,
    skip_vendor_header,
    raw,
    dry_run,
    beta,
):
    """Upload new firmware to device.

    Device must be in bootloader mode.

    You can specify a filename or URL from which the firmware can be downloaded.
    You can also explicitly specify a firmware version that you want.
    Otherwise, trezorctl will attempt to find latest available version
    from wallet.trezor.io.

    If you provide a fingerprint via the --fingerprint option, it will be checked
    against downloaded firmware fingerprint. Otherwise fingerprint is checked
    against wallet.trezor.io information, if available.

    If you are customizing Model T bootloader and providing your own vendor header,
    you can use --skip-vendor-header to ignore vendor header signatures.
    """
    if sum(bool(x) for x in (filename, url, version)) > 1:
        click.echo("You can use only one of: filename, url, version.")
        sys.exit(1)

    client = connect()
    if not dry_run and not client.features.bootloader_mode:
        click.echo("Please switch your device to bootloader mode.")
        sys.exit(1)

    f = client.features
    bootloader_onev2 = f.major_version == 1 and f.minor_version >= 8

    if filename:
        data = open(filename, "rb").read()
    else:
        if not url:
            bootloader_version = [f.major_version, f.minor_version, f.patch_version]
            version_list = [int(x) for x in version.split(".")] if version else None
            url, fp = find_best_firmware_version(bootloader_version, version_list, beta)
            if not fingerprint:
                fingerprint = fp

        click.echo("Downloading from {}".format(url))
        r = requests.get(url)
        data = r.content

    if not raw and not skip_check:
        try:
            version, fw = firmware.parse(data)
        except Exception as e:
            click.echo(e)
            sys.exit(2)

        validate_firmware(version, fw, fingerprint)
        if (
            bootloader_onev2
            and version == firmware.FirmwareFormat.TREZOR_ONE
            and not fw.embedded_onev2
        ):
            click.echo("Firmware is too old for your device. Aborting.")
            sys.exit(3)
        elif not bootloader_onev2 and version == firmware.FirmwareFormat.TREZOR_ONE_V2:
            click.echo("You need to upgrade to bootloader 1.8.0 first.")
            sys.exit(3)

        if f.major_version not in ALLOWED_FIRMWARE_FORMATS:
            click.echo("trezorctl doesn't know your device version. Aborting.")
            sys.exit(3)
        elif version not in ALLOWED_FIRMWARE_FORMATS[f.major_version]:
            click.echo("Firmware does not match your device, aborting.")
            sys.exit(3)

    if not raw:
        # special handling for embedded-OneV2 format:
        # for bootloader < 1.8, keep the embedding
        # for bootloader 1.8.0 and up, strip the old OneV1 header
        if bootloader_onev2 and data[:4] == b"TRZR" and data[256 : 256 + 4] == b"TRZF":
            click.echo("Extracting embedded firmware image (fingerprint may change).")
            data = data[256:]

    if dry_run:
        click.echo("Dry run. Not uploading firmware to device.")
    else:
        try:
            if f.major_version == 1 and f.firmware_present:
                # Trezor One does not send ButtonRequest
                click.echo("Please confirm action on your Trezor device")
            return firmware.update(client, data)
        except exceptions.Cancelled:
            click.echo("Update aborted on device.")
        except exceptions.TrezorException as e:
            click.echo("Update failed: {}".format(e))
            sys.exit(3)


@cli.command(help="Perform a self-test.")
@click.pass_obj
def self_test(connect):
    return debuglink.self_test(connect())


@cli.command()
def usb_reset():
    """Perform USB reset on a stuck device.

    This can fix LIBUSB_ERROR_PIPE and similar errors when connecting to a device
    in a messed state.
    """
    from trezorlib.transport.webusb import WebUsbTransport

    WebUsbTransport.enumerate(usb_reset=True)


#
# Basic coin functions
#


@cli.command(help="Get address for specified path.")
@click.option("-c", "--coin", default="Bitcoin")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.option("-t", "--script-type", type=CHOICE_INPUT_SCRIPT_TYPE, default="address")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_address(connect, coin, address, script_type, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return btc.get_address(
        client, coin, address_n, show_display, script_type=script_type
    )


@cli.command(help="Get public node of given path.")
@click.option("-c", "--coin", default="Bitcoin")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'")
@click.option("-e", "--curve")
@click.option("-t", "--script-type", type=CHOICE_INPUT_SCRIPT_TYPE, default="address")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def get_public_node(connect, coin, address, curve, script_type, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    result = btc.get_public_node(
        client,
        address_n,
        ecdsa_curve_name=curve,
        show_display=show_display,
        coin_name=coin,
        script_type=script_type,
    )
    return {
        "node": {
            "depth": result.node.depth,
            "fingerprint": "%08x" % result.node.fingerprint,
            "child_num": result.node.child_num,
            "chain_code": result.node.chain_code.hex(),
            "public_key": result.node.public_key.hex(),
        },
        "xpub": result.xpub,
    }


#
# Signing options
#


@cli.command(help="Sign transaction.")
@click.option("-c", "--coin", default="Bitcoin")
@click.argument("json_file", type=click.File(), required=False)
@click.pass_obj
def sign_tx(connect, coin, json_file):
    client = connect()

    # XXX this is the future code of this function
    if json_file is not None:
        data = json.load(json_file)
        coin = data["coin_name"]
        details = protobuf.dict_to_proto(proto.SignTx, data["details"])
        inputs = [protobuf.dict_to_proto(proto.TxInputType, i) for i in data["inputs"]]
        outputs = [
            protobuf.dict_to_proto(proto.TxOutputType, output)
            for output in data["outputs"]
        ]
        prev_txes = {
            bytes.fromhex(txid): protobuf.dict_to_proto(proto.TransactionType, tx)
            for txid, tx in data["prev_txes"].items()
        }

        _, serialized_tx = btc.sign_tx(
            client, coin, inputs, outputs, details, prev_txes
        )

        client.close()

        click.echo()
        click.echo("Signed Transaction:")
        click.echo(serialized_tx.hex())
        return

    # XXX ALL THE REST is legacy code and will be dropped
    click.echo("Warning: interactive sign-tx mode is deprecated.", err=True)
    click.echo(
        "Instead, you should format your transaction data as JSON and "
        "supply the file as an argument to sign-tx"
    )
    if coin in coins.tx_api:
        coin_data = coins.by_name[coin]
        txapi = coins.tx_api[coin]
    else:
        click.echo('Coin "%s" is not recognized.' % coin, err=True)
        click.echo(
            "Supported coin types: %s" % ", ".join(coins.tx_api.keys()), err=True
        )
        sys.exit(1)

    def default_script_type(address_n):
        script_type = "address"

        if address_n is None:
            pass
        elif address_n[0] == tools.H_(49):
            script_type = "p2shsegwit"

        return script_type

    def outpoint(s):
        txid, vout = s.split(":")
        return bytes.fromhex(txid), int(vout)

    inputs = []
    txes = {}
    while True:
        click.echo()
        prev = click.prompt(
            "Previous output to spend (txid:vout)", type=outpoint, default=""
        )
        if not prev:
            break
        prev_hash, prev_index = prev
        address_n = click.prompt("BIP-32 path to derive the key", type=tools.parse_path)
        try:
            tx = txapi[prev_hash]
            txes[prev_hash] = tx
            amount = tx.bin_outputs[prev_index].amount
            click.echo("Prefilling input amount: {}".format(amount))
        except Exception as e:
            print(e)
            click.echo("Failed to fetch transation. This might bite you later.")
            amount = click.prompt("Input amount (satoshis)", type=int, default=0)
        sequence = click.prompt(
            "Sequence Number to use (RBF opt-in enabled by default)",
            type=int,
            default=0xFFFFFFFD,
        )
        script_type = click.prompt(
            "Input type",
            type=CHOICE_INPUT_SCRIPT_TYPE,
            default=default_script_type(address_n),
        )
        script_type = (
            script_type
            if isinstance(script_type, int)
            else CHOICE_INPUT_SCRIPT_TYPE.typemap[script_type]
        )

        new_input = proto.TxInputType(
            address_n=address_n,
            prev_hash=prev_hash,
            prev_index=prev_index,
            amount=amount,
            script_type=script_type,
            sequence=sequence,
        )
        if coin_data["bip115"]:
            prev_output = txapi.get_tx(prev_hash.hex()).bin_outputs[prev_index]
            new_input.prev_block_hash_bip115 = prev_output.block_hash
            new_input.prev_block_height_bip115 = prev_output.block_height

        inputs.append(new_input)

    if coin_data["bip115"]:
        current_block_height = txapi.current_height()
        # Zencash recommendation for the better protection
        block_height = current_block_height - 300
        block_hash = txapi.get_block_hash(block_height)
        # Blockhash passed in reverse order
        block_hash = block_hash[::-1]
    else:
        block_height = None
        block_hash = None

    outputs = []
    while True:
        click.echo()
        address = click.prompt("Output address (for non-change output)", default="")
        if address:
            address_n = None
        else:
            address = None
            address_n = click.prompt(
                "BIP-32 path (for change output)", type=tools.parse_path, default=""
            )
            if not address_n:
                break
        amount = click.prompt("Amount to spend (satoshis)", type=int)
        script_type = click.prompt(
            "Output type",
            type=CHOICE_OUTPUT_SCRIPT_TYPE,
            default=default_script_type(address_n),
        )
        script_type = (
            script_type
            if isinstance(script_type, int)
            else CHOICE_OUTPUT_SCRIPT_TYPE.typemap[script_type]
        )
        outputs.append(
            proto.TxOutputType(
                address_n=address_n,
                address=address,
                amount=amount,
                script_type=script_type,
                block_hash_bip115=block_hash,
                block_height_bip115=block_height,
            )
        )

    signtx = proto.SignTx()
    signtx.version = click.prompt("Transaction version", type=int, default=2)
    signtx.lock_time = click.prompt("Transaction locktime", type=int, default=0)
    if coin == "Capricoin":
        signtx.timestamp = click.prompt("Transaction timestamp", type=int)

    _, serialized_tx = btc.sign_tx(
        client, coin, inputs, outputs, details=signtx, prev_txes=txes
    )

    client.close()

    click.echo()
    click.echo("Signed Transaction:")
    click.echo(serialized_tx.hex())
    click.echo()
    click.echo("Use the following form to broadcast it to the network:")
    click.echo(txapi.pushtx_url)


#
# Message functions
#


@cli.command(help="Sign message using address of given path.")
@click.option("-c", "--coin", default="Bitcoin")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.option(
    "-t",
    "--script-type",
    type=click.Choice(["address", "segwit", "p2shsegwit"]),
    default="address",
)
@click.argument("message")
@click.pass_obj
def sign_message(connect, coin, address, message, script_type):
    client = connect()
    address_n = tools.parse_path(address)
    typemap = {
        "address": proto.InputScriptType.SPENDADDRESS,
        "segwit": proto.InputScriptType.SPENDWITNESS,
        "p2shsegwit": proto.InputScriptType.SPENDP2SHWITNESS,
    }
    script_type = typemap[script_type]
    res = btc.sign_message(client, coin, address_n, message, script_type)
    return {
        "message": message,
        "address": res.address,
        "signature": base64.b64encode(res.signature),
    }


@cli.command(help="Verify message.")
@click.option("-c", "--coin", default="Bitcoin")
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def verify_message(connect, coin, address, signature, message):
    signature = base64.b64decode(signature)
    return btc.verify_message(connect(), coin, address, signature, message)


@cli.command(help="Sign message with Ethereum address.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/60'/0'/0/0"
)
@click.argument("message")
@click.pass_obj
def ethereum_sign_message(connect, address, message):
    client = connect()
    address_n = tools.parse_path(address)
    ret = ethereum.sign_message(client, address_n, message)
    output = {
        "message": message,
        "address": ret.address,
        "signature": "0x%s" % ret.signature.hex(),
    }
    return output


def ethereum_decode_hex(value):
    if value.startswith("0x") or value.startswith("0X"):
        return bytes.fromhex(value[2:])
    else:
        return bytes.fromhex(value)


@cli.command(help="Verify message signed with Ethereum address.")
@click.argument("address")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def ethereum_verify_message(connect, address, signature, message):
    signature = ethereum_decode_hex(signature)
    return ethereum.verify_message(connect(), address, signature, message)


@cli.command(help="Encrypt value by given key and path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def encrypt_keyvalue(connect, address, key, value):
    client = connect()
    address_n = tools.parse_path(address)
    res = misc.encrypt_keyvalue(client, address_n, key, value.encode())
    return res.hex()


@cli.command(help="Decrypt value by given key and path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/10016'/0")
@click.argument("key")
@click.argument("value")
@click.pass_obj
def decrypt_keyvalue(connect, address, key, value):
    client = connect()
    address_n = tools.parse_path(address)
    return misc.decrypt_keyvalue(client, address_n, key, bytes.fromhex(value))


# @cli.command(help='Encrypt message.')
# @click.option('-c', '--coin', default='Bitcoin')
# @click.option('-d', '--display-only', is_flag=True)
# @click.option('-n', '--address', required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0")
# @click.argument('pubkey')
# @click.argument('message')
# @click.pass_obj
# def encrypt_message(connect, coin, display_only, address, pubkey, message):
#     client = connect()
#     pubkey = bytes.fromhex(pubkey)
#     address_n = tools.parse_path(address)
#     res = client.encrypt_message(pubkey, message, display_only, coin, address_n)
#     return {
#         'nonce': res.nonce.hex(),
#         'message': res.message.hex(),
#         'hmac': res.hmac.hex(),
#         'payload': base64.b64encode(res.nonce + res.message + res.hmac),
#     }


# @cli.command(help='Decrypt message.')
# @click.option('-n', '--address', required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0")
# @click.argument('payload')
# @click.pass_obj
# def decrypt_message(connect, address, payload):
#     client = connect()
#     address_n = tools.parse_path(address)
#     payload = base64.b64decode(payload)
#     nonce, message, msg_hmac = payload[:33], payload[33:-8], payload[-8:]
#     return client.decrypt_message(address_n, nonce, message, msg_hmac)


#
# Ethereum functions
#


@cli.command(help="Get Ethereum address in hex encoding.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/60'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def ethereum_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return ethereum.get_address(client, address_n, show_display)


@cli.command(help="Get Ethereum public node of given path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/60'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def ethereum_get_public_node(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    result = ethereum.get_public_node(client, address_n, show_display=show_display)
    return {
        "node": {
            "depth": result.node.depth,
            "fingerprint": "%08x" % result.node.fingerprint,
            "child_num": result.node.child_num,
            "chain_code": result.node.chain_code.hex(),
            "public_key": result.node.public_key.hex(),
        },
        "xpub": result.xpub,
    }


# fmt: off
ETHER_UNITS = {
    'wei':          1,
    'kwei':         1000,
    'babbage':      1000,
    'femtoether':   1000,
    'mwei':         1000000,
    'lovelace':     1000000,
    'picoether':    1000000,
    'gwei':         1000000000,
    'shannon':      1000000000,
    'nanoether':    1000000000,
    'nano':         1000000000,
    'szabo':        1000000000000,
    'microether':   1000000000000,
    'micro':        1000000000000,
    'finney':       1000000000000000,
    'milliether':   1000000000000000,
    'milli':        1000000000000000,
    'ether':        1000000000000000000,
    'eth':          1000000000000000000,
}
# fmt: on


def ethereum_amount_to_int(ctx, param, value):
    if value is None:
        return None
    if value.isdigit():
        return int(value)
    try:
        number, unit = re.match(r"^(\d+(?:.\d+)?)([a-z]+)", value).groups()
        scale = ETHER_UNITS[unit]
        decoded_number = Decimal(number)
        return int(decoded_number * scale)

    except Exception:
        import traceback

        traceback.print_exc()
        raise click.BadParameter("Amount not understood")


def ethereum_list_units(ctx, param, value):
    if not value or ctx.resilient_parsing:
        return
    maxlen = max(len(k) for k in ETHER_UNITS.keys()) + 1
    for unit, scale in ETHER_UNITS.items():
        click.echo("{:{maxlen}}:  {}".format(unit, scale, maxlen=maxlen))
    ctx.exit()


def ethereum_erc20_contract(w3, token_address, to_address, amount):
    min_abi = [
        {
            "name": "transfer",
            "type": "function",
            "constant": False,
            "inputs": [
                {"name": "_to", "type": "address"},
                {"name": "_value", "type": "uint256"},
            ],
            "outputs": [{"name": "", "type": "bool"}],
        }
    ]
    contract = w3.eth.contract(address=token_address, abi=min_abi)
    return contract.encodeABI("transfer", [to_address, amount])


@cli.command()
@click.option(
    "-c", "--chain-id", type=int, default=1, help="EIP-155 chain id (replay protection)"
)
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to source address, e.g., m/44'/60'/0'/0/0",
)
@click.option(
    "-g", "--gas-limit", type=int, help="Gas limit (required for offline signing)"
)
@click.option(
    "-t",
    "--gas-price",
    help="Gas price (required for offline signing)",
    callback=ethereum_amount_to_int,
)
@click.option(
    "-i", "--nonce", type=int, help="Transaction counter (required for offline signing)"
)
@click.option("-d", "--data", help="Data as hex string, e.g. 0x12345678")
@click.option("-p", "--publish", is_flag=True, help="Publish transaction via RPC")
@click.option("-x", "--tx-type", type=int, help="TX type (used only for Wanchain)")
@click.option("-t", "--token", help="ERC20 token address")
@click.option(
    "--list-units",
    is_flag=True,
    help="List known currency units and exit.",
    is_eager=True,
    callback=ethereum_list_units,
    expose_value=False,
)
@click.argument("to_address")
@click.argument("amount", callback=ethereum_amount_to_int)
@click.pass_obj
def ethereum_sign_tx(
    connect,
    chain_id,
    address,
    amount,
    gas_limit,
    gas_price,
    nonce,
    data,
    publish,
    to_address,
    tx_type,
    token,
):
    """Sign (and optionally publish) Ethereum transaction.

    Use TO_ADDRESS as destination address, or set to "" for contract creation.

    Specify a contract address with the --token option to send an ERC20 token.

    You can specify AMOUNT and gas price either as a number of wei,
    or you can use a unit suffix.

    Use the --list-units option to show all known currency units.
    ERC20 token amounts are specified in eth/wei, custom units are not supported.

    If any of gas price, gas limit and nonce is not specified, this command will
    try to connect to an ethereum node and auto-fill these values. You can configure
    the connection with WEB3_PROVIDER_URI environment variable.
    """
    if not ETHEREUM_SIGN_TX:
        click.echo("Ethereum requirements not installed.")
        click.echo("Please run:")
        click.echo()
        click.echo("  pip install web3 rlp")
        sys.exit(1)

    w3 = web3.Web3()
    if (
        gas_price is None or gas_limit is None or nonce is None or publish
    ) and not w3.isConnected():
        click.echo("Failed to connect to Ethereum node.")
        click.echo(
            "If you want to sign offline, make sure you provide --gas-price, "
            "--gas-limit and --nonce arguments"
        )
        sys.exit(1)

    if data is not None and token is not None:
        click.echo("Can't send tokens and custom data at the same time")
        sys.exit(1)

    client = connect()
    address_n = tools.parse_path(address)
    from_address = ethereum.get_address(client, address_n)

    if token:
        data = ethereum_erc20_contract(w3, token, to_address, amount)
        to_address = token
        amount = 0

    if data:
        data = ethereum_decode_hex(data)
    else:
        data = b""

    if gas_price is None:
        gas_price = w3.eth.gasPrice

    if gas_limit is None:
        gas_limit = w3.eth.estimateGas(
            {
                "to": to_address,
                "from": from_address,
                "value": amount,
                "data": "0x%s" % data.hex(),
            }
        )

    if nonce is None:
        nonce = w3.eth.getTransactionCount(from_address)

    sig = ethereum.sign_tx(
        client,
        n=address_n,
        tx_type=tx_type,
        nonce=nonce,
        gas_price=gas_price,
        gas_limit=gas_limit,
        to=to_address,
        value=amount,
        data=data,
        chain_id=chain_id,
    )

    to = ethereum_decode_hex(to_address)
    if tx_type is None:
        transaction = rlp.encode((nonce, gas_price, gas_limit, to, amount, data) + sig)
    else:
        transaction = rlp.encode(
            (tx_type, nonce, gas_price, gas_limit, to, amount, data) + sig
        )
    tx_hex = "0x%s" % transaction.hex()

    if publish:
        tx_hash = w3.eth.sendRawTransaction(tx_hex).hex()
        return "Transaction published with ID: %s" % tx_hash
    else:
        return "Signed raw transaction:\n%s" % tx_hex


#
# EOS functions
#


@cli.command(help="Get Eos public key in base58 encoding.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/194'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def eos_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    res = eos.get_public_key(client, address_n, show_display)
    return "WIF: {}\nRaw: {}".format(res.wif_public_key, res.raw_public_key.hex())


@cli.command(help="Init sign (and optionally publish) EOS transaction. ")
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to source address, e.g., m/44'/194'/0'/0/0",
)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.pass_obj
def eos_sign_transaction(connect, address, file):
    client = connect()

    tx_json = json.load(file)

    address_n = tools.parse_path(address)
    return eos.sign_tx(client, address_n, tx_json["transaction"], tx_json["chain_id"])


#
# ADA functions
#


@cli.command(help="Sign Cardano transaction.")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.option("-N", "--network", type=int, default=1)
@click.pass_obj
def cardano_sign_tx(connect, file, network):
    client = connect()

    transaction = json.load(file)

    inputs = [cardano.create_input(input) for input in transaction["inputs"]]
    outputs = [cardano.create_output(output) for output in transaction["outputs"]]
    transactions = transaction["transactions"]

    signed_transaction = cardano.sign_tx(client, inputs, outputs, transactions, network)

    return {
        "tx_hash": signed_transaction.tx_hash.hex(),
        "tx_body": signed_transaction.tx_body.hex(),
    }


@cli.command(help="Get Cardano address.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def cardano_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)

    return cardano.get_address(client, address_n, show_display)


@cli.command(help="Get Cardano public key.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/1815'/0'/0/0"
)
@click.pass_obj
def cardano_get_public_key(connect, address):
    client = connect()
    address_n = tools.parse_path(address)

    return cardano.get_public_key(client, address_n)


#
# NEM functions
#


@cli.command(help="Get NEM address for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/43'/0'")
@click.option("-N", "--network", type=int, default=0x68)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def nem_get_address(connect, address, network, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return nem.get_address(client, address_n, network, show_display)


@cli.command(help="Sign (and optionally broadcast) NEM transaction.")
@click.option("-n", "--address", help="BIP-32 path to signing key")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction in NIS (RequestPrepareAnnounce) format",
)
@click.option("-b", "--broadcast", help="NIS to announce transaction to")
@click.pass_obj
def nem_sign_tx(connect, address, file, broadcast):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = nem.sign_tx(client, address_n, json.load(file))

    payload = {"data": transaction.data.hex(), "signature": transaction.signature.hex()}

    if broadcast:
        return requests.post(
            "{}/transaction/announce".format(broadcast), json=payload
        ).json()
    else:
        return payload


#
# Lisk functions
#


@cli.command(help="Get Lisk address for specified path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/134'/0'/0'"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def lisk_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return lisk.get_address(client, address_n, show_display)


@cli.command(help="Get Lisk public key for specified path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/134'/0'/0'"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def lisk_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    res = lisk.get_public_key(client, address_n, show_display)
    output = {"public_key": res.public_key.hex()}
    return output


@cli.command(help="Sign Lisk transaction.")
@click.option(
    "-n",
    "--address",
    required=True,
    help="BIP-32 path to signing key, e.g. m/44'/134'/0'/0'",
)
@click.option(
    "-f", "--file", type=click.File("r"), default="-", help="Transaction in JSON format"
)
# @click.option('-b', '--broadcast', help='Broadcast Lisk transaction')
@click.pass_obj
def lisk_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)
    transaction = lisk.sign_tx(client, address_n, json.load(file))

    payload = {"signature": transaction.signature.hex()}

    return payload


@cli.command(help="Sign message with Lisk address.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/134'/0'/0'"
)
@click.argument("message")
@click.pass_obj
def lisk_sign_message(connect, address, message):
    client = connect()
    address_n = client.expand_path(address)
    res = lisk.sign_message(client, address_n, message)
    output = {
        "message": message,
        "public_key": res.public_key.hex(),
        "signature": res.signature.hex(),
    }
    return output


@cli.command(help="Verify message signed with Lisk address.")
@click.argument("pubkey")
@click.argument("signature")
@click.argument("message")
@click.pass_obj
def lisk_verify_message(connect, pubkey, signature, message):
    signature = bytes.fromhex(signature)
    pubkey = bytes.fromhex(pubkey)
    return lisk.verify_message(connect(), pubkey, signature, message)


#
# Monero functions
#


@cli.command(help="Get Monero address for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/128'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.option(
    "-t", "--network-type", type=click.Choice(["0", "1", "2", "3"]), default="0"
)
@click.pass_obj
def monero_get_address(connect, address, show_display, network_type):
    client = connect()
    address_n = tools.parse_path(address)
    network_type = int(network_type)
    return monero.get_address(client, address_n, show_display, network_type)


@cli.command(help="Get Monero watch key for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/128'/0'")
@click.option(
    "-t", "--network-type", type=click.Choice(["0", "1", "2", "3"]), default="0"
)
@click.pass_obj
def monero_get_watch_key(connect, address, network_type):
    client = connect()
    address_n = tools.parse_path(address)
    network_type = int(network_type)
    res = monero.get_watch_key(client, address_n, network_type)
    output = {"address": res.address.decode(), "watch_key": res.watch_key.hex()}
    return output


#
# CoSi functions
#


@cli.command(help="Ask device to commit to CoSi signing.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.argument("data")
@click.pass_obj
def cosi_commit(connect, address, data):
    client = connect()
    address_n = tools.parse_path(address)
    return cosi.commit(client, address_n, bytes.fromhex(data))


@cli.command(help="Ask device to sign using CoSi.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/0'/0'/0/0"
)
@click.argument("data")
@click.argument("global_commitment")
@click.argument("global_pubkey")
@click.pass_obj
def cosi_sign(connect, address, data, global_commitment, global_pubkey):
    client = connect()
    address_n = tools.parse_path(address)
    return cosi.sign(
        client,
        address_n,
        bytes.fromhex(data),
        bytes.fromhex(global_commitment),
        bytes.fromhex(global_pubkey),
    )


#
# Stellar functions
#
@cli.command(help="Get Stellar public address")
@click.option(
    "-n",
    "--address",
    required=False,
    help="BIP32 path. Always use hardened paths and the m/44'/148'/ prefix",
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def stellar_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return stellar.get_address(client, address_n, show_display)


@cli.command(help="Sign a base64-encoded transaction envelope")
@click.option(
    "-n",
    "--address",
    required=False,
    help="BIP32 path. Always use hardened paths and the m/44'/148'/ prefix",
    default=stellar.DEFAULT_BIP32_PATH,
)
@click.option(
    "-n",
    "--network-passphrase",
    default=stellar.DEFAULT_NETWORK_PASSPHRASE,
    required=False,
    help="Network passphrase (blank for public network). Testnet is: 'Test SDF Network ; September 2015'",
)
@click.argument("b64envelope")
@click.pass_obj
def stellar_sign_transaction(connect, b64envelope, address, network_passphrase):
    client = connect()
    address_n = tools.parse_path(address)
    tx, operations = stellar.parse_transaction_bytes(base64.b64decode(b64envelope))
    resp = stellar.sign_tx(client, tx, operations, address_n, network_passphrase)

    return base64.b64encode(resp.signature)


#
# Ripple functions
#
@cli.command(help="Get Ripple address")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/144'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def ripple_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return ripple.get_address(client, address_n, show_display)


@cli.command(help="Sign Ripple transaction")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/144'/0'/0/0"
)
@click.option(
    "-f", "--file", type=click.File("r"), default="-", help="Transaction in JSON format"
)
@click.pass_obj
def ripple_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)
    msg = ripple.create_sign_tx_msg(json.load(file))

    result = ripple.sign_tx(client, address_n, msg)
    click.echo("Signature:")
    click.echo(result.signature.hex())
    click.echo()
    click.echo("Serialized tx including the signature:")
    click.echo(result.serialized_tx.hex())


#
# Tezos functions
#
@cli.command(help="Get Tezos address for specified path.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/1729'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def tezos_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return tezos.get_address(client, address_n, show_display)


@cli.command(help="Get Tezos public key.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/1729'/0'")
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def tezos_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)
    return tezos.get_public_key(client, address_n, show_display)


@cli.command(help="Sign Tezos transaction.")
@click.option("-n", "--address", required=True, help="BIP-32 path, e.g. m/44'/1729'/0'")
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    default="-",
    help="Transaction in JSON format (byte fields should be hexlified)",
)
@click.pass_obj
def tezos_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)
    msg = protobuf.dict_to_proto(proto.TezosSignTx, json.load(file))
    return tezos.sign_tx(client, address_n, msg)


#
# Binance functions
#


@cli.command(help="Get Binance address for specified path.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/714'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def binance_get_address(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)

    return binance.get_address(client, address_n, show_display)


@cli.command(help="Get Binance public key.")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/714'/0'/0/0"
)
@click.option("-d", "--show-display", is_flag=True)
@click.pass_obj
def binance_get_public_key(connect, address, show_display):
    client = connect()
    address_n = tools.parse_path(address)

    return binance.get_public_key(client, address_n, show_display).hex()


@cli.command(help="Sign Binance transaction")
@click.option(
    "-n", "--address", required=True, help="BIP-32 path to key, e.g. m/44'/714'/0'/0/0"
)
@click.option(
    "-f",
    "--file",
    type=click.File("r"),
    required=True,
    help="Transaction in JSON format",
)
@click.pass_obj
def binance_sign_tx(connect, address, file):
    client = connect()
    address_n = tools.parse_path(address)

    return binance.sign_tx(client, address_n, json.load(file))


#
# Main
#


if __name__ == "__main__":
    cli()  # pylint: disable=E1120
