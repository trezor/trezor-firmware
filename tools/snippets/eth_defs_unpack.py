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
from __future__ import annotations

import zipfile
from pathlib import Path

import click
import requests

from trezorlib import definitions, merkle_tree

ZIP_FILENAME = "definitions-sparse.zip"

TOPDIRS = ("chain-id", "slip44")


class SparseZipSource(definitions.Source):
    def __init__(self, zip: Path | zipfile.ZipFile) -> None:
        if isinstance(zip, Path):
            self.zip = zipfile.ZipFile(zip)
        else:
            self.zip = zip

        # extract signature
        self.signature = self.read_bytes("signature.dat")
        self.root_hash = self.read_bytes("root.dat")

        # construct a Merkle tree
        entries = []
        for name in self.zip.namelist():
            if name.startswith("chain-id/"):
                entries.append(self.read_bytes(name))
        entries.sort()
        self.merkle_tree = merkle_tree.MerkleTree(entries)

        if self.root_hash != self.merkle_tree.get_root_hash():
            raise ValueError("Failed to reconstruct the correct Merkle tree")

    def read_bytes(self, path: str | Path) -> bytes:
        with self.zip.open(str(path)) as f:
            return f.read()

    def fetch_path(self, *components: str) -> bytes | None:
        path = "/".join(components)
        data = self.read_bytes(path)
        proof = self.merkle_tree.get_proof(data)
        proof_bytes = definitions.ProofFormat.build(proof)
        return data + proof_bytes + self.signature


@click.command()
@click.option(
    "-z",
    "--definitions-zip",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True, path_type=Path),
    help="Local zip file with stored definitions.",
)
@click.argument(
    "outdir",
    type=click.Path(resolve_path=True, file_okay=False, writable=True, path_type=Path),
)
def unpack_definitions(definitions_zip: Path, outdir: Path) -> None:
    """Script that unpacks and completes (insert missing Merkle Tree proofs
    into the definitions) the Ethereum definitions (networks and tokens).

    If no local zip is provided, the latest one will be downloaded from trezor.io.
    """
    if definitions_zip is None:
        result = requests.get(definitions.DEFS_BASE_URL + ZIP_FILENAME)
        result.raise_for_status()
        zip = zipfile.ZipFile(result.raw)
    else:
        zip = zipfile.ZipFile(definitions_zip)

    source = SparseZipSource(zip)

    if not outdir.exists():
        outdir.mkdir()

    for name in zip.namelist():
        if name == "signature.dat" or not name.endswith(".dat"):
            continue

        local_path = outdir / name
        local_path.parent.mkdir(parents=True, exist_ok=True)
        data = source.fetch_path(name)
        assert data is not None, f"Could not read data for: {name}"
        local_path.write_bytes(data)


if __name__ == "__main__":
    unpack_definitions()
