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

import os
import sys
import time
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    BinaryIO,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    Union,
)
from urllib.parse import urlparse

import click
import requests

from .. import device, exceptions, firmware, messages, models
from ..firmware import models as fw_models
from ..models import TrezorModel
from . import ChoiceType, with_client

if TYPE_CHECKING:
    from ..client import TrezorClient
    from . import TrezorConnection

MODEL_CHOICE = ChoiceType(
    {
        "T1B1": models.T1B1,
        "T2T1": models.T2T1,
        "T2B1": models.T2B1,
        "T3T1": models.T3T1,
        "T3B1": models.T3B1,
        # aliases
        "1": models.T1B1,
        "one": models.T1B1,
        "t": models.T2T1,
        "r": models.T2B1,
        "safe3": models.T2B1,
        "s3": models.T2B1,
        "safe5": models.T3T1,
        "s5": models.T3T1,
    },
    case_sensitive=False,
)


def _print_version(version: Tuple[int, int, int, int]) -> None:
    major, minor, patch, build = version
    click.echo(f"Firmware version {major}.{minor}.{patch} build {build}")


def _is_bootloader_onev2(client: "TrezorClient") -> bool:
    """Check if bootloader is capable of installing the Trezor One v2 firmware directly.

    This is the case from bootloader version 1.8.0, and also holds for firmware version
    1.8.0 because that installs the appropriate bootloader.
    """
    f = client.features
    version = (f.major_version, f.minor_version, f.patch_version)
    bootloader_onev2 = f.major_version == 1 and version >= (1, 8, 0)
    return bootloader_onev2


def _get_file_name_from_url(url: str) -> str:
    """Parse the name of the file being downloaded from the specific url."""
    full_path = urlparse(url).path
    return os.path.basename(full_path)


def _print_firmware_model(hw_model: Union[bytes, fw_models.Model]) -> None:
    try:
        model_name = fw_models.Model.from_hw_model(hw_model).name
        click.echo(f"{model_name} firmware image.")
        return
    except ValueError:
        pass

    assert isinstance(hw_model, bytes)
    if hw_model.isascii():
        model_name = hw_model.decode("ascii")
        click.echo(f"Unrecognized hardware model: {model_name}")
        return

    click.echo(f"Suspicious hardware model code: {hw_model.hex()} ({hw_model!r})")


def print_firmware_version(fw: "firmware.FirmwareType") -> None:
    """Print out the firmware version and details."""
    if isinstance(fw, firmware.LegacyFirmware):
        if fw.embedded_v2:
            click.echo("Trezor One firmware with embedded v2 image (1.8.0 or later)")
            _print_version(fw.embedded_v2.header.version)
        else:
            click.echo("Trezor One firmware image.")
    elif isinstance(fw, firmware.LegacyV2Firmware):
        click.echo("Trezor One v2 firmware (1.8.0 or later)")
        _print_version(fw.header.version)
    elif isinstance(fw, firmware.VendorFirmware):
        _print_firmware_model(fw.vendor_header.hw_model)
        vendor = fw.vendor_header.text
        vendor_version = "{}.{}".format(*fw.vendor_header.version)
        click.echo(f"Vendor header from {vendor}, version {vendor_version}")
        _print_version(fw.firmware.header.version)


def validate_signatures(
    fw: "firmware.FirmwareType", prompt_unsigned: bool = True
) -> None:
    """Check the signatures on the firmware.

    Prints the validity status.
    In case of Trezor One v1 prompts the user (as the signature is missing).
    Exits if the validation fails.
    """
    try:
        fw.verify()
    except firmware.Unsigned:
        if not prompt_unsigned or not isinstance(
            fw, (firmware.LegacyFirmware, firmware.LegacyV2Firmware)
        ):
            click.echo("Firmware is not signed, aborting.")
            sys.exit(4)

        # allow legacy firmware without signatures
        if not click.confirm("No signatures found. Continue?", default=False):
            sys.exit(1)

        if firmware.is_onev2(fw):
            try:
                assert fw.embedded_v2 is not None
                fw.embedded_v2.verify_unsigned()
            except firmware.FirmwareIntegrityError as e:
                click.echo(e)
                click.echo("Firmware validation failed, aborting.")
                sys.exit(4)
        click.echo("Unsigned firmware looking OK.")

    except firmware.FirmwareIntegrityError as e:
        try:
            fw.verify(dev_keys=True)
            click.echo("WARNING: Firmware for development kit only.")
        except firmware.FirmwareIntegrityError:
            click.echo(e)
            click.echo("Firmware validation failed, aborting.")
            sys.exit(4)


def validate_fingerprint(
    fw: "firmware.FirmwareType",
    expected_fingerprint: Optional[str] = None,
) -> None:
    """Determine and validate the firmware fingerprint.

    Prints the fingerprint.
    Exits if the validation fails.
    """
    fingerprint = fw.digest().hex()
    click.echo(f"Firmware fingerprint: {fingerprint}")
    if firmware.is_onev2(fw):
        assert fw.embedded_v2 is not None
        fingerprint_onev2 = fw.embedded_v2.digest().hex()
        click.echo(f"Embedded v2 image fingerprint: {fingerprint_onev2}")
    if expected_fingerprint and fingerprint != expected_fingerprint:
        click.echo(f"Expected fingerprint: {expected_fingerprint}")
        click.echo("Fingerprints do not match, aborting.")
        sys.exit(5)


def check_device_match(
    fw: "firmware.FirmwareType", model: TrezorModel, bootloader_onev2: bool
) -> None:
    """Validate if the device and firmware are compatible.

    Prints error message and exits if the validation fails.
    """
    if (model is not models.T1B1) != isinstance(fw, firmware.VendorFirmware):
        click.echo("Firmware does not match your device, aborting.")
        sys.exit(3)

    if (
        bootloader_onev2
        and isinstance(fw, firmware.LegacyFirmware)
        and not fw.embedded_v2
    ):
        click.echo("Firmware is too old for your device. Aborting.")
        sys.exit(3)
    elif not bootloader_onev2 and isinstance(fw, firmware.LegacyV2Firmware):
        click.echo("You need to upgrade to bootloader 1.8.0 first.")
        sys.exit(3)


def get_all_firmware_releases(
    model: TrezorModel, bitcoin_only: bool, beta: bool
) -> List[Dict[str, Any]]:
    """Get sorted list of all releases suitable for inputted parameters"""
    url = f"https://data.trezor.io/firmware/{model.internal_name.lower()}/releases.json"
    req = requests.get(url)
    req.raise_for_status()
    releases = req.json()
    if not releases:
        raise click.ClickException("Failed to get list of releases")

    if bitcoin_only:
        releases = [r for r in releases if "url_bitcoinonly" in r]

    # filter releases according to channel field
    releases_stable = [
        r for r in releases if "channel" not in r or r["channel"] == "stable"
    ]
    releases_beta = [r for r in releases if "channel" in r and r["channel"] == "beta"]
    if beta:
        releases = releases_stable + releases_beta
    else:
        releases = releases_stable

    releases.sort(key=lambda r: r["version"], reverse=True)

    return releases


def get_url_and_fingerprint_from_release(
    release: dict,
    bitcoin_only: bool,
) -> Tuple[str, str]:
    """Get appropriate url and fingerprint from release dictionary."""
    if bitcoin_only:
        url = release["url_bitcoinonly"]
        fingerprint = release["fingerprint_bitcoinonly"]
    else:
        url = release["url"]
        fingerprint = release["fingerprint"]

    url_prefix = "data/"
    if not url.startswith(url_prefix):
        click.echo(f"Unsupported URL found: {url}")
        sys.exit(1)
    final_url = "https://data.trezor.io/" + url[len(url_prefix) :]

    return final_url, fingerprint


def find_specified_firmware_version(
    model: TrezorModel,
    version: str,
    beta: bool,
    bitcoin_only: bool,
) -> Tuple[str, str]:
    """Get the url from which to download the firmware and its expected fingerprint.

    If the specified version is not found, exits with a failure.
    """
    want_version = [int(x) for x in version.split(".")]
    releases = get_all_firmware_releases(model, bitcoin_only, beta)
    for release in releases:
        if release["version"] == want_version:
            return get_url_and_fingerprint_from_release(release, bitcoin_only)

    click.echo(f"Version {version} for {model.internal_name} could not be found.")
    sys.exit(1)


def _should_use_bitcoin_only(features: messages.Features) -> bool:
    # in bootloader, decide by unit indicator
    # TODO determine by fw vendor if installed?
    if features.bootloader_mode:
        return bool(features.unit_btconly)

    # in firmware, check whether current firmware is bitcoin-only
    if messages.Capability.Bitcoin_like not in features.capabilities:
        return True

    # universal firmware by default
    return False


def find_best_firmware_version(
    client: "TrezorClient",
    version: Optional[str],
    beta: bool,
    bitcoin_only: Optional[bool],
) -> Tuple[str, str]:
    """Get the url from which to download the firmware and its expected fingerprint.

    When the version (X.Y.Z) is specified, checks for that specific release.
    Otherwise takes the latest one.

    If the specified version is not found, prints the closest available version
    (higher than the specified one, if existing).
    """
    if bitcoin_only is None:
        bitcoin_only = _should_use_bitcoin_only(client.features)

    def version_str(version: Iterable[int]) -> str:
        return ".".join(map(str, version))

    f = client.features

    releases = get_all_firmware_releases(client.model, bitcoin_only, beta)
    highest_version = releases[0]["version"]

    if version:
        want_version = [int(x) for x in version.split(".")]
        if len(want_version) != 3:
            click.echo("Please use the 'X.Y.Z' version format.")
        if want_version[0] != f.major_version:
            click.echo(
                f"Warning: Trezor {client.model.name} firmware version should be "
                f"{f.major_version}.X.Y (requested: {version})"
            )
    else:
        want_version = highest_version
        click.echo(f"Best available version: {version_str(want_version)}")

    # Identifying the release we will install
    # It may happen that the different version will need to be installed first
    confirm_different_version = False
    while True:
        # The want_version can be changed below, need to redefine it
        want_version_str = version_str(want_version)
        try:
            release = next(r for r in releases if r["version"] == want_version)
        except StopIteration:
            click.echo(f"Version {want_version_str} not found for your device.")

            # look for versions starting with the lowest
            for release in reversed(releases):
                closest_version = release["version"]
                if closest_version > want_version:
                    # stop at first that is higher than the requested
                    break
            else:
                raise click.ClickException("No versions were found!")
            # if there was no break, the newest is used
            click.echo(f"Closest available version: {version_str(closest_version)}")
            if not beta and want_version > highest_version:
                click.echo("Hint: specify --beta to look for a beta release.")
            sys.exit(1)

        # It can be impossible to update from a very old version directly
        #   to the newer one, in that case update to the minimal
        #   compatible version first
        # Choosing the version key to compare based on (not) being in BL mode
        client_version = [f.major_version, f.minor_version, f.patch_version]
        if f.bootloader_mode:
            key_to_compare = "min_bootloader_version"
        else:
            key_to_compare = "min_firmware_version"

        if key_to_compare in release and release[key_to_compare] > client_version:
            need_version = release["min_firmware_version"]
            need_version_str = version_str(need_version)
            click.echo(
                f"Version {need_version_str} is required before upgrading to {want_version_str}."
            )
            want_version = need_version
            confirm_different_version = True
        else:
            break

    if confirm_different_version:
        installing_different = f"Installing version {want_version_str} instead."
        if version is None:
            click.echo(installing_different)
        else:
            ok = click.confirm(installing_different + " Continue?", default=True)
            if not ok:
                sys.exit(1)

    return get_url_and_fingerprint_from_release(release, bitcoin_only)


def download_firmware_data(url: str) -> bytes:
    try:
        click.echo(f"Downloading from {url}")
        r = requests.get(url)
        r.raise_for_status()
        return r.content
    except requests.exceptions.HTTPError as err:
        click.echo(f"Error downloading file: {err}")
        sys.exit(3)


def validate_firmware(
    firmware_data: bytes,
    fingerprint: Optional[str] = None,
    model: Optional[TrezorModel] = None,
    bootloader_onev2: Optional[bool] = None,
    verify_only: bool = False,
) -> None:
    """Validate the firmware through multiple tests.

    - parsing it properly
    - containing valid signatures and fingerprint (when chosen)
    - being compatible with the device (when chosen)
    """
    try:
        fw = firmware.parse(firmware_data)
    except Exception as e:
        click.echo(e)
        sys.exit(2)

    print_firmware_version(fw)
    if not fw.model():
        click.echo("Cannot validate firmware for unrecognized model.")
        if not verify_only:
            click.echo("(Hint: use --skip-check to skip validation.)")
        sys.exit(3)

    validate_fingerprint(fw, fingerprint)
    validate_signatures(fw, prompt_unsigned=not verify_only)

    if model is not None and bootloader_onev2 is not None:
        check_device_match(fw, model, bootloader_onev2)
        click.echo("Firmware is appropriate for your device.")


def extract_embedded_fw(
    firmware_data: bytes,
    bootloader_onev2: bool,
) -> bytes:
    """Modify the firmware data for sending into Trezor, if necessary."""
    # special handling for embedded_v2-OneV2 format:
    # for bootloader < 1.8, keep the embedding
    # for bootloader 1.8.0 and up, strip the old OneV1 header
    if (
        bootloader_onev2
        and firmware_data[:4] == b"TRZR"
        and firmware_data[256 : 256 + 4] == b"TRZF"
    ):
        click.echo("Extracting embedded_v2 firmware image.")
        return firmware_data[256:]

    return firmware_data


def upload_firmware_into_device(
    client: "TrezorClient",
    firmware_data: bytes,
) -> None:
    """Perform the final act of loading the firmware into Trezor."""
    f = client.features
    try:
        if f.major_version == 1 and f.firmware_present is not False:
            # Trezor One does not send ButtonRequest
            click.echo("Please confirm the action on your Trezor device")

        click.echo("Uploading...\r", nl=False)
        with click.progressbar(
            label="Uploading", length=len(firmware_data), show_eta=False
        ) as bar:
            firmware.update(client, firmware_data, bar.update)
    except exceptions.Cancelled:
        click.echo("Update aborted on device.")
    except exceptions.TrezorException as e:
        click.echo(f"Update failed: {e}")
        sys.exit(3)


def _is_strict_update(client: "TrezorClient", firmware_data: bytes) -> bool:
    """Check if the firmware is from the same vendor and the
    firmware is newer than the currently installed firmware.
    """
    try:
        fw = firmware.parse(firmware_data)
    except Exception as e:
        click.echo(e)
        sys.exit(2)

    if not isinstance(fw, firmware.VendorFirmware):
        return False

    f = client.features
    cur_version = (f.major_version, f.minor_version, f.patch_version, 0)

    return (
        fw.vendor_header.text == f.fw_vendor
        and fw.firmware.header.version > cur_version
        and fw.vendor_header.trust.is_full_trust()
    )


def _get_firmware_header_size(firmware_data: bytes) -> int:
    """Returns size of vendor and image headers"""
    try:
        fw = firmware.parse(firmware_data)
    except Exception as e:
        click.echo(e)
        sys.exit(2)

    if isinstance(fw, firmware.VendorFirmware):
        return fw.firmware.header.header_len + fw.vendor_header.header_len

    return 0


@click.group(name="firmware")
def cli() -> None:
    """Firmware commands."""


@cli.command()
# fmt: off
@click.argument("filename", type=click.File("rb"))
@click.option("-c", "--check-device", is_flag=True, help="Validate device compatibility")
@click.option("--fingerprint", help="Expected firmware fingerprint in hex")
@click.pass_obj
# fmt: on
def verify(
    obj: "TrezorConnection",
    filename: BinaryIO,
    check_device: bool,
    fingerprint: Optional[str],
) -> None:
    """Verify the integrity of the firmware data stored in a file.

    By default the device is not checked and does not need to be connected.
    Its validation must be specified.

    In case of validation failure exits with the appropriate exit code.
    """
    # Deciding if to take the device into account
    bootloader_onev2: Optional[bool]
    model: Optional[TrezorModel]
    if check_device:
        with obj.client_context() as client:
            bootloader_onev2 = _is_bootloader_onev2(client)
            model = client.model
    else:
        bootloader_onev2 = None
        model = None

    firmware_data = filename.read()
    validate_firmware(
        firmware_data=firmware_data,
        fingerprint=fingerprint,
        bootloader_onev2=bootloader_onev2,
        model=model,
        verify_only=True,
    )


@cli.command()
# fmt: off
@click.option("-o", "--output", type=click.File("wb"), help="Output file to save firmware data to")
@click.option("-v", "--version", help="Which version to download")
@click.option("-m", "--model", type=MODEL_CHOICE, help="Which model to download firmware for")
@click.option("-s", "--skip-check", is_flag=True, help="Do not validate firmware integrity")
@click.option("--beta", is_flag=True, help="Use firmware from BETA channel")
@click.option("--bitcoin-only/--universal", is_flag=True, default=None, help="Download bitcoin-only or universal firmware (defaults to universal)")
@click.option("--fingerprint", help="Expected firmware fingerprint in hex")
@click.pass_obj
# fmt: on
def download(
    obj: "TrezorConnection",
    output: Optional[BinaryIO],
    model: Optional[TrezorModel],
    version: Optional[str],
    skip_check: bool,
    fingerprint: Optional[str],
    beta: bool,
    bitcoin_only: Optional[bool],
) -> None:
    """Download and save the firmware image.

    Validation is done by default, can be omitted by "-s" or "--skip-check".
    When fingerprint or output file are not set, take them from SL servers.
    """
    # When a version is specified, we do not even need the client connection
    #   (and we will not be checking device when validating)
    if model and version:
        url, fp = find_specified_firmware_version(
            model, version, beta, bool(bitcoin_only)
        )
        bootloader_onev2 = None
    else:
        with obj.client_context() as client:
            url, fp = find_best_firmware_version(
                client=client, version=version, beta=beta, bitcoin_only=bitcoin_only
            )
            bootloader_onev2 = _is_bootloader_onev2(client)
            if model is not None and model != client.model:
                click.echo("Warning: ignoring --model option.")
            model = client.model

    firmware_data = download_firmware_data(url)

    if not fingerprint:
        fingerprint = fp

    if not skip_check:
        validate_firmware(
            firmware_data=firmware_data,
            fingerprint=fingerprint,
            bootloader_onev2=bootloader_onev2,
            model=model,
        )

    if not output:
        output = open(_get_file_name_from_url(url), "wb")
    output.write(firmware_data)
    output.close()
    click.echo(f"Firmware saved under {output.name}.")


@cli.command()
# fmt: off
@click.option("-f", "--filename", type=click.File("rb"), help="File containing firmware data")
@click.option("-u", "--url", help="Where to get the firmware from - full link")
@click.option("-v", "--version", help="Which version to download")
@click.option("-s", "--skip-check", is_flag=True, help="Do not validate firmware integrity")
@click.option("-n", "--dry-run", is_flag=True, help="Perform all steps but do not actually upload the firmware")
@click.option("-l", "--language", help="Language code, blob, or URL")
@click.option("--beta", is_flag=True, help="Use firmware from BETA channel")
@click.option("--bitcoin-only/--universal", is_flag=True, default=None, help="Download bitcoin-only or universal firmware (defaults to universal)")
@click.option("--raw", is_flag=True, help="Push raw firmware data to Trezor")
@click.option("--fingerprint", help="Expected firmware fingerprint in hex")
# fmt: on
@click.pass_obj
def update(
    obj: "TrezorConnection",
    filename: Optional[BinaryIO],
    url: Optional[str],
    version: Optional[str],
    skip_check: bool,
    fingerprint: Optional[str],
    raw: bool,
    dry_run: bool,
    beta: bool,
    bitcoin_only: Optional[bool],
    language: Optional[str],
) -> None:
    """Upload new firmware to device.

    You can specify a filename or URL from which the firmware can be downloaded.
    You can also explicitly specify a firmware version that you want.
    Otherwise, trezorctl will attempt to find latest available version
    from data.trezor.io.

    If you provide a fingerprint via the --fingerprint option, it will be checked
    against downloaded firmware fingerprint. Otherwise fingerprint is checked
    against data.trezor.io information, if available.
    """
    with obj.client_context() as client:
        if sum(bool(x) for x in (filename, url, version)) > 1:
            click.echo("You can use only one of: filename, url, version.")
            sys.exit(1)

        language_data = b""
        if language is not None:
            if client.features.bootloader_mode:
                click.echo("Language data cannot be uploaded in bootloader mode.")
                sys.exit(1)

            assert language is not None
            try:
                language_data = Path(language).read_bytes()
            except Exception:
                try:
                    language_data = requests.get(language).content
                except Exception:
                    raise click.ClickException(
                        f"Failed to load translations from {language}"
                    ) from None

        if filename:
            firmware_data = filename.read()
        else:
            if not url:
                url, fp = find_best_firmware_version(
                    client=client, version=version, beta=beta, bitcoin_only=bitcoin_only
                )
                if not fingerprint:
                    fingerprint = fp

            firmware_data = download_firmware_data(url)

        if not raw and not skip_check:
            validate_firmware(
                firmware_data=firmware_data,
                fingerprint=fingerprint,
                bootloader_onev2=_is_bootloader_onev2(client),
                model=client.model,
            )

            if not raw:
                firmware_data = extract_embedded_fw(
                    firmware_data=firmware_data,
                    bootloader_onev2=_is_bootloader_onev2(client),
                )

        if dry_run:
            click.echo("Dry run. Not uploading firmware to device.")
            return

        if not client.features.bootloader_mode:
            if _is_strict_update(client, firmware_data):
                header_size = _get_firmware_header_size(firmware_data)
                device.reboot_to_bootloader(
                    client,
                    boot_command=messages.BootCommand.INSTALL_UPGRADE,
                    firmware_header=firmware_data[:header_size],
                    language_data=language_data,
                )
            else:
                if language_data:
                    click.echo(
                        "WARNING: Seamless installation not possible, language data will not be uploaded."
                    )
                device.reboot_to_bootloader(client)

            click.echo("Waiting for bootloader...")
            while True:
                time.sleep(0.5)
                try:
                    obj.get_transport()
                    break
                except Exception:
                    pass

    with obj.client_context() as client:
        if not client.features.bootloader_mode:
            click.echo("Please switch your device to bootloader mode.")
            sys.exit(1)

        upload_firmware_into_device(client=client, firmware_data=firmware_data)


@cli.command()
@click.argument("hex_challenge", required=False)
@with_client
def get_hash(client: "TrezorClient", hex_challenge: Optional[str]) -> str:
    """Get a hash of the installed firmware combined with the optional challenge."""
    challenge = bytes.fromhex(hex_challenge) if hex_challenge else None
    return firmware.get_hash(client, challenge).hex()
