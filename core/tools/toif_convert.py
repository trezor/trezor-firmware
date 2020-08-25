#!/usr/bin/env python3

import click
from PIL import Image

from trezorlib import toif


@click.command()
@click.argument("infile", type=click.File("rb"))
@click.argument("outfile", type=click.File("wb"))
def toif_convert(infile, outfile):
    """Convert any image format to/from TOIF or vice-versa.

    \b
    Examples:
      toif_convert.py somefile.jpg outfile.toif
      toif_convert.py infile.toif outfile.png
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


if __name__ == "__main__":
    toif_convert()
