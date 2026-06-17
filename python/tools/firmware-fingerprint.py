#!/usr/bin/env python3

# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
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

from typing import BinaryIO, TextIO

import click

from trezorlib._internal import firmware_headers
from trezorlib._internal.slip26 import VENDOR_TEXT_TO_PURPOSE, Purpose, make_label
from trezorlib.firmware.models import Model


@click.command()
@click.argument("filename", type=click.File("rb"))
@click.option("-o", "--output", type=click.File("w"), default="-")
def firmware_fingerprint(filename: BinaryIO, output: TextIO) -> None:
    """Display the labeled fingerprint ("<model>_<purpose>: HEX") of a firmware file."""
    data = filename.read()

    try:
        fw = firmware_headers.parse_image(data)
    except Exception as parse_err:
        try:
            # Try to parse as a new-style PQ boot header.
            digest = firmware_headers.BootloaderV2Image.parse(data).merkle_root()
        except Exception:
            raise click.ClickException(str(parse_err)) from None
        model_int = 0
        purpose = Purpose.FIRMWARE_ROOT_2025
    else:
        if isinstance(fw, firmware_headers.LegacyV2Firmware):
            model = Model.T1B1
        elif isinstance(fw, firmware_headers.CosiSignedMixin):
            try:
                model = Model.from_hw_model(fw.get_header().hw_model)
            except ValueError as e:
                raise click.ClickException(str(e)) from None
        else:
            raise click.ClickException(f"unsupported image type {type(fw).__name__}")

        model_int = int.from_bytes(model.value, "little")
        digest = fw.digest()
        if isinstance(fw, firmware_headers.SecmonImage):
            purpose = Purpose.SECURE_MONITOR
        elif isinstance(fw, firmware_headers.BootloaderImage):
            purpose = Purpose.BOOTLOADER
        elif isinstance(fw, firmware_headers.VendorHeader):
            purpose = Purpose.VENDOR_HEADER
        elif isinstance(fw, firmware_headers.LegacyV2Firmware):
            purpose = Purpose.FIRMWARE
        elif isinstance(fw, firmware_headers.VendorFirmware):
            try:
                # A vendor image may wrap a secmon-only build. Try to parse code
                # as secmon. If it succeeds, the image is secmon-only and the
                # fingerprint relevant for signing is that of the secmon.
                secmon = firmware_headers.SecmonImage.parse(fw.firmware.code)
            except Exception:
                purpose = VENDOR_TEXT_TO_PURPOSE.get(fw.vendor_header.text)
                if purpose is None:
                    raise click.ClickException(
                        f"unsupported vendor header {fw.vendor_header.text!r}"
                    ) from None
            else:
                purpose = Purpose.SECURE_MONITOR
                digest = secmon.digest()
        else:
            raise click.ClickException(f"unsupported image type {type(fw).__name__}")

    click.echo(f"{make_label(model_int, purpose)}: {digest.hex(' ', 2)}", file=output)


if __name__ == "__main__":
    firmware_fingerprint()
