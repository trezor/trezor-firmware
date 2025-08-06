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

from typing import BinaryIO

import click
from PIL import Image

from trezorlib import toif


@click.group()
def cli():
    """TOIF toolkit."""


@cli.command()
@click.argument("infile", type=click.File("rb"))
@click.argument("outfile", type=click.File("wb"))
def convert(infile: BinaryIO, outfile: BinaryIO) -> None:
    """Convert any image format to/from TOIF or vice-versa.

    \b
    Examples:
      toiftool convert somefile.jpg outfile.toif
      toiftool convert infile.toif outfile.png

    \b
      # ensure gray-scale output TOIF
      mogrify -colorspace gray icon.png
      toiftool convert icon.png icon.toif
    """
    if infile.name.endswith(".toif") or infile.name == "-":
        toi = toif.from_bytes(infile.read())
        im = toi.to_image()
        im.save(outfile)

    elif outfile.name.endswith(".toif") or outfile.name == "-":
        im = Image.open(infile)
        toi = toif.from_image(im)
        outfile.write(toi.to_bytes())

    else:
        raise click.ClickException("At least one of the arguments must end with .toif")


@cli.command()
@click.argument("toif_file", type=click.File("rb"))
def info(toif_file: BinaryIO) -> None:
    """Print information about TOIF file."""
    toif_bytes = toif_file.read()
    toi = toif.from_bytes(toif_bytes)
    click.echo(f"TOIF file: {toif_file.name}")
    click.echo(f"Size: {len(toif_bytes)} bytes")
    w, h = toi.size
    click.echo(f"Dimensions: {w}x{h}")
    click.echo(f"Format: {toi.mode}")


@cli.command()
@click.argument("toif_file", type=click.File("rb"))
def show(toif_file: BinaryIO) -> None:
    """Show TOIF file in a new window."""
    toi = toif.from_bytes(toif_file.read())
    im = toi.to_image()
    im.show()


if __name__ == "__main__":
    cli()
