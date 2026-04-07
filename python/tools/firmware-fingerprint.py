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

import sys
from typing import BinaryIO, TextIO

import click

from trezorlib._internal import firmware_headers


@click.command()
@click.argument("filename", type=click.File("rb"))
@click.option("-o", "--output", type=click.File("w"), default="-")
def firmware_fingerprint(filename: BinaryIO, output: TextIO) -> None:
    """Display fingerprint of a firmware file."""
    data = filename.read()

    orig_err = None
    try:
        fw = firmware_headers.parse_image(data)
    except Exception as e:
        orig_err = e
    else:
        if isinstance(fw, firmware_headers.VendorFirmware):
            try:
                # try to parse code as secmon
                # if it succeeds, the image is secmon-only and the fingerprint
                # relevant for signing is that of the secmon
                secmon = firmware_headers.SecmonImage.parse(fw.firmware.code)
                click.echo(secmon.digest().hex(), file=output)
                return
            except Exception:
                pass
        click.echo(fw.digest().hex(), file=output)
        return

    try:
        click.echo(
            firmware_headers.BootloaderV2Image.parse(data).merkle_root().hex(),
            file=output,
        )
    except Exception as e:
        if orig_err is not None:
            click.echo(orig_err, err=True)
        else:
            click.echo(e, err=True)
        sys.exit(2)


if __name__ == "__main__":
    firmware_fingerprint()
