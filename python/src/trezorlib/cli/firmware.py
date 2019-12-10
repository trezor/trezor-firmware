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
import requests

from .. import exceptions, firmware

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


def find_best_firmware_version(
    bootloader_version, requested_version=None, beta=False, bitcoin_only=False
):
    if beta:
        url = "https://beta-wallet.trezor.io/data/firmware/{}/releases.json"
    else:
        url = "https://wallet.trezor.io/data/firmware/{}/releases.json"
    releases = requests.get(url.format(bootloader_version[0])).json()
    if not releases:
        raise click.ClickException("Failed to get list of releases")

    if bitcoin_only:
        releases = [r for r in releases if "url_bitcoinonly" in r]
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

    if bitcoin_only:
        url = release["url_bitcoinonly"]
        fingerprint = release["fingerprint_bitcoinonly"]
    else:
        url = release["url"]
        fingerprint = release["fingerprint"]
    if beta:
        url = "https://beta-wallet.trezor.io/" + url
    else:
        url = "https://wallet.trezor.io/" + url

    return url, fingerprint


@click.command()
# fmt: off
@click.option("-f", "--filename")
@click.option("-u", "--url")
@click.option("-v", "--version")
@click.option("-s", "--skip-check", is_flag=True, help="Do not validate firmware integrity")
@click.option("-n", "--dry-run", is_flag=True, help="Perform all steps but do not actually upload the firmware")
@click.option("--beta", is_flag=True, help="Use firmware from BETA wallet")
@click.option("--bitcoin-only", is_flag=True, help="Use bitcoin-only firmware (if possible)")
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
    bitcoin_only,
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
            url, fp = find_best_firmware_version(
                bootloader_version, version_list, beta, bitcoin_only
            )
            if not fingerprint:
                fingerprint = fp

        try:
            click.echo("Downloading from {}".format(url))
            r = requests.get(url)
            r.raise_for_status()
        except requests.exceptions.HTTPError as err:
            click.echo("Error downloading file: {}".format(err))
            sys.exit(3)

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
            if f.major_version == 1 and f.firmware_present is not False:
                # Trezor One does not send ButtonRequest
                click.echo("Please confirm the action on your Trezor device")
            return firmware.update(client, data)
        except exceptions.Cancelled:
            click.echo("Update aborted on device.")
        except exceptions.TrezorException as e:
            click.echo("Update failed: {}".format(e))
            sys.exit(3)
