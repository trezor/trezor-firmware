#!/usr/bin/env python3
from __future__ import annotations

import datetime
import io
from pathlib import Path
import os
import subprocess

import click

def get_layout_params(layout: Path, name: str) -> int:
    directory = os.path.dirname(os.path.realpath(__file__))
    with subprocess.Popen(args=["python", Path(directory, "layout_parser.py"), str(layout), name],
                          stdout=subprocess.PIPE) as script:
        return int(script.stdout.read().decode().strip())

@click.command()
@click.argument(
    "layout",
    type=click.Path(dir_okay=False, writable=True, path_type=Path),
    required=True,
)
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
def main(
        layout: Path,
        bin: List[Tuple[Path, str]],
        outfile: Path | None,

) -> None:

    if outfile is None:
        today = datetime.date.today().strftime(r"%Y-%m-%d")
        outfile = Path(f"combined-{today}.bin")

    first_bin = bin[0]
    (name, bin_path) = first_bin

    start_offset = get_layout_params(layout, name+ "_START")

    offset = start_offset
    out_bytes = io.BytesIO()

    for (name, bin_path) in bin:
        bin_start = get_layout_params(layout, name + "_START")
        # zero-pad until next section:
        offset += out_bytes.write(b"\x00" * (bin_start - offset))
        assert offset == bin_start

        # write binary
        offset += out_bytes.write(bin_path.read_bytes())

    # write out contents
    click.echo(f"Writing {outfile} ({offset - start_offset} bytes)")
    outfile.write_bytes(out_bytes.getvalue())


if __name__ == "__main__":
    main()
