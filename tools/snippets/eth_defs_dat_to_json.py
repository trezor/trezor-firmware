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

from __future__ import annotations

import json
from pathlib import Path

import click
from eth_defs_refresh_json import dat_to_dict


@click.command()
@click.argument(
    "dat_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=Path),
)
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False, writable=True, allow_dash=True, path_type=Path),
    help="Output JSON file, or '-' for stdout. [default: DAT_FILE with .json suffix]",
)
@click.option(
    "--dev",
    is_flag=True,
    help="Verify against the development signing keys instead of the production ones.",
)
def dat_to_json(dat_file: Path, output: Path | None, dev: bool) -> None:
    """Convert a signed Ethereum/Solana definition DAT_FILE into the JSON
    fixture format used by the tests.

    The signature is verified before decoding; definitions that fail the
    verification are rejected."""
    try:
        converted = dat_to_dict(dat_file.read_bytes(), dev=dev)
    except Exception as e:
        raise click.ClickException(f"{dat_file.name}: {e}") from e
    text = json.dumps(converted, indent=2) + "\n"

    if str(output) == "-":
        click.echo(text, nl=False)
        return

    if output is None:
        output = dat_file.with_suffix(".json")
    output.write_text(text)
    click.echo(f"written: {output}", err=True)


if __name__ == "__main__":
    dat_to_json()
