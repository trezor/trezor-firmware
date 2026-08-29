#!/usr/bin/env python3
"""Check a binary for insecure PRNG mock markers."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import click

MCU_MARKER = b"<PRNG-MCU>"
OPTIGA_MARKER = b"<PRNG-Optiga>"
TROPIC_MARKER = b"<PRNG-Tropic>"

MODEL_MARKERS = {
    "T2T1": (MCU_MARKER,),
    "T2B1": (MCU_MARKER, OPTIGA_MARKER),
    "T3B1": (MCU_MARKER, OPTIGA_MARKER),
    "T3T1": (MCU_MARKER, OPTIGA_MARKER),
    "T3W1": (MCU_MARKER, OPTIGA_MARKER, TROPIC_MARKER),
}


def find_markers(path: Path, markers: Iterable[bytes]) -> set[bytes]:
    data = path.read_bytes()
    return {marker for marker in markers if marker in data}


def format_markers(markers: Iterable[bytes]) -> str:
    return ", ".join(marker.decode("ascii") for marker in sorted(markers))


@click.command()
@click.option(
    "--present",
    is_flag=True,
    help="Require the PRNG markers expected for the selected model.",
)
@click.option(
    "--absent",
    is_flag=True,
    help="Require that no insecure PRNG marker is present.",
)
@click.option(
    "-m",
    "--model",
    type=click.Choice(sorted(MODEL_MARKERS)),
    help="Firmware model, required with --present.",
)
@click.argument(
    "filename",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def main(present: bool, absent: bool, model: str | None, filename: Path) -> None:
    if present == absent:
        raise click.UsageError("provide exactly one of --present or --absent")
    if present:
        if model is None:
            raise click.UsageError("--model is required with --present")
        markers = MODEL_MARKERS[model]
    else:
        markers = (b"<PRNG-",)

    found = find_markers(filename, markers)

    if present:
        missing = set(markers) - found
        if missing:
            formatted = format_markers(missing)
            click.echo(
                f"{filename}: missing insecure PRNG marker(s): {formatted}",
                err=True,
            )
            raise click.exceptions.Exit(1)
    elif found:
        formatted = format_markers(found)
        click.echo(
            f"{filename}: contains insecure PRNG marker(s): {formatted}", err=True
        )
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    main()
