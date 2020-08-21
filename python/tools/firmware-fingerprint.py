#!/usr/bin/env python3

import sys
import click

from trezorlib import firmware


@click.command()
@click.argument("filename", type=click.File("rb"))
@click.option("-o", "--output", type=click.File("w"), default="-")
def firmware_fingerprint(filename, output):
    """Display fingerprint of a firmware file."""
    data = filename.read()

    try:
        version, fw = firmware.parse(data)
    except Exception as e:
        click.echo(e, err=True)
        sys.exit(2)

    fingerprint = firmware.digest(version, fw).hex()
    click.echo(fingerprint, file=output)


if __name__ == "__main__":
    firmware_fingerprint()
