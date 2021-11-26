#!/usr/bin/env python3

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

import sys
from typing import BinaryIO, TextIO

import click

from trezorlib import firmware
from trezorlib._internal import firmware_headers


@click.command()
@click.argument("filename", type=click.File("rb"))
@click.option("-o", "--output", type=click.File("w"), default="-")
def firmware_fingerprint(filename: BinaryIO, output: TextIO) -> None:
    """Display fingerprint of a firmware file."""
    data = filename.read()

    try:
        version, fw = firmware.parse(data)

        # Unsigned production builds for Trezor T do not have valid code hashes.
        # Use the internal module which recomputes them first.
        if version == firmware.FirmwareFormat.TREZOR_T:
            fingerprint = firmware_headers.FirmwareImage(fw).digest()
        else:
            fingerprint = firmware.digest(version, fw)
    except Exception as e:
        click.echo(e, err=True)
        sys.exit(2)

    click.echo(fingerprint.hex(), file=output)


if __name__ == "__main__":
    firmware_fingerprint()
