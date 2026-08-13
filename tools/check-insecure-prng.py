#!/usr/bin/env python3
"""Check a binary for insecure PRNG mock markers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import click

MCU_TAG = b"<PRNG-MCU>"
OPTIGA_TAG = b"<PRNG-Optiga>"
TROPIC_TAG = b"<PRNG-Tropic>"

MODEL_TAGS = {
    "T2T1": (MCU_TAG,),
    "T2B1": (MCU_TAG, OPTIGA_TAG),
    "T3B1": (MCU_TAG, OPTIGA_TAG),
    "T3T1": (MCU_TAG, OPTIGA_TAG),
    "T3W1": (MCU_TAG, OPTIGA_TAG, TROPIC_TAG),
}

CHUNK_SIZE = 1024 * 1024


def contains_any(path: Path, markers: Iterable[bytes]) -> set[bytes]:
    markers = tuple(markers)
    found: set[bytes] = set()
    overlap_size = max(len(marker) for marker in markers) - 1
    previous = b""

    with path.open("rb") as binary:
        while chunk := binary.read(CHUNK_SIZE):
            data = previous + chunk
            found.update(marker for marker in markers if marker in data)
            if len(found) == len(markers):
                break
            previous = data[-overlap_size:]

    return found


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
    type=click.Choice(sorted(MODEL_TAGS)),
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
        markers = MODEL_TAGS[model]
    else:
        markers = (b"<PRNG-",)
    found = contains_any(filename, markers)

    if present:
        missing = set(markers) - found
        if missing:
            formatted = ", ".join(marker.decode() for marker in sorted(missing))
            click.echo(
                f"{filename}: missing insecure PRNG marker(s): {formatted}",
                err=True,
            )
            raise click.exceptions.Exit(1)
    elif found:
        click.echo(f"{filename}: contains insecure PRNG marker: <PRNG-", err=True)
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    main()
    