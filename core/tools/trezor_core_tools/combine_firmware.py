#!/usr/bin/env python3
from __future__ import annotations

import datetime
import io
import sys
from pathlib import Path

import click

from .layout_parser import find_all_values


@click.command()
@click.argument("model")
@click.argument(
    "outfile",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=False,
)
@click.option(
    "--bin",
    "-b",
    type=(str, click.Path(exists=True, dir_okay=False, readable=True, path_type=Path)),
    multiple=True,
)
def main(model: str, bin: list[tuple[str, Path]], outfile: Path | None) -> None:
    """Create a combined.bin file from components.

    MODEL is the internal model name (e.g. T1B1, T2T1, T2B1).

    BIN is a list of tuples with the type and path to the binary file. The usual types
    are:

    \b
     * BOARDLOADER
     * BOOTLOADER
     * FIRMWARE

    For example:

    \b
    $ combine_firmware T3T1 -b boardloader build/boardloader.bin -b bootloader build/bootloader.bin -b firmware build/firmware.bin
    """
    if outfile is None:
        today = datetime.date.today().strftime(r"%Y-%m-%d")
        outfile = Path(f"combined-{today}.bin")

    offset = 0
    out_buf = io.BytesIO()

    all_values = find_all_values(model)

    def find_value(name: str) -> int:
        value_name = f"{name.upper()}_START"
        if value_name not in all_values:
            click.echo(f"ERROR: component {name} not found in layout for model {model}")
            click.echo("Try one of: boardloader, bootloader, firmware")
            sys.exit(1)
        return all_values[value_name]

    for name, bin_path in bin:
        bin_start = find_value(name)

        if not offset:
            # initialize offset
            offset = bin_start
        else:
            # pad until next section
            offset += out_buf.write(b"\x00" * (bin_start - offset))
        assert offset == bin_start

        # write binary
        offset += out_buf.write(bin_path.read_bytes())

    # write out contents
    out_bytes = out_buf.getvalue()
    click.echo(f"Writing {outfile} ({len(out_bytes)} bytes)")
    outfile.write_bytes(out_bytes)


if __name__ == "__main__":
    main()
