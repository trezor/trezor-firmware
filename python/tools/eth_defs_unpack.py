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

import pathlib
import click

from trezorlib import ethereum


@click.command()
@click.option(
    "-z", "--definitions-zip",
    type=click.Path(
        exists=True, dir_okay=False, resolve_path=True, path_type=pathlib.Path
    ),
    default=f"./{ethereum.DEFS_ZIP_FILENAME}",
    help="Zip file with stored definitions. Zip file could be obtained using command"
    f"`trezorctl ethereum download-definitions`. Defaults to \"./{ethereum.DEFS_ZIP_FILENAME}\"."
)
@click.option(
    "-o",
    "--outdir",
    type=click.Path(
        resolve_path=True, file_okay=False, writable=True, path_type=pathlib.Path
    ),
    default="./",
    help="Directory path where the definitions will be unpacked. Zip file contains top level"
    f"dir \"{ethereum.DEFS_ZIP_TOPLEVEL_DIR}\" and this will be unpacked to desired \"outdir\""
    "path. Any colliding directories will be overwritten! Defaults to \"./\".",
)
def unpack_definitions(
    definitions_zip: pathlib.Path,
    outdir: pathlib.Path,
) -> None:
    """Script that unpacks and completes (insert missing Merkle Tree proofs
    into the definitions) the Ethereum definitions (networks and tokens).
    """
    all_defs = ethereum.get_all_completed_definitions_from_zip(definitions_zip)

    for path, definition in all_defs.items():
        if not definition:
            continue

        filepath = outdir / path
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, mode="wb+") as f:
            f.write(definition)


if __name__ == "__main__":
    unpack_definitions()
