#!/usr/bin/env python3
"""
Prints a table of artifacts produced by build-docker.sh
"""

from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Artifact:
    path: Path
    filename: str
    model: str
    fingerprint: str
    sha256: str

    @staticmethod
    def header() -> list[str]:
        return ["Filename", "Fingerprint", "SHA-256"]

    def cells(self) -> list[str]:
        return [self.filename, self.fingerprint, self.sha256]


def guess_model(dirpath: Path) -> str | None:
    modeldir = dirpath.parent.name
    for prefix in ["core-", "legacy-"]:
        if modeldir.startswith(prefix):
            model = modeldir.removeprefix(prefix)[:4]
            if re.fullmatch(r"[A-Z0-9]{4}", model):
                return model
    return None


def get_artifact(model: str, dirpath: Path, filenames: list[str]) -> Artifact | None:
    fingerprints = [f for f in filenames if f.endswith(".fingerprint")]
    if len(fingerprints) != 1:
        return None

    fingerprint_file = dirpath / fingerprints[0]
    bin_file = fingerprint_file.with_suffix("")
    if not bin_file.suffix == ".bin":
        return None
    if not bin_file.is_file():
        return None

    digest = hashlib.sha256(bin_file.read_bytes()).hexdigest()

    fullnames = [
        f
        for f in filenames
        if f.startswith(f"{bin_file.with_suffix('').name}-{model}-")
        and f.endswith(".bin")
    ]
    if len(fullnames) > 1:
        raise RuntimeError(f"Ambiguous files: {' '.join(fullnames)}")
    if len(fullnames) == 1:
        fullname_bin_file = dirpath / fullnames[0]
        fullname_digest = hashlib.sha256(fullname_bin_file.read_bytes()).hexdigest()
        if digest != fullname_digest:
            raise RuntimeError(f"Files not identical: {bin_file}, {fullname_bin_file}")
        bin_file = fullname_bin_file

    fingerprint = fingerprint_file.read_text().strip()
    return Artifact(
        path=bin_file,
        filename=bin_file.name,
        model=model,
        fingerprint=fingerprint,
        sha256=digest,
    )


def walk_dir(artifact_dir: Path) -> dict[str, list[Artifact]]:
    result = {}
    # oops, Path.walk() is 3.12+
    for dirpath, _, filenames in artifact_dir.walk():  # type: ignore [Cannot access attribute]
        model = guess_model(dirpath)
        if not model:
            continue

        artifact = get_artifact(model, dirpath, filenames)
        if not artifact:
            continue

        result.setdefault(model, []).append(artifact)
    return result


def artifact_order(artifact: Artifact) -> tuple[int, int]:
    ORDER = ("prodtest", "boardloader", "bootloader", "secmon", "firmware")
    fname = artifact.filename
    index = next(
        (ix for ix, pfx in enumerate(ORDER) if fname.startswith(pfx)), len(ORDER)
    )
    return (index, int("-btconly" in fname or "-bitcoinonly" in fname))


def justify(table: list[list[str]]) -> list[list[str]]:
    widths = [max(len(row[i]) for row in table) for i in range(len(table[0]))]
    return [[cell.ljust(widths[i]) for i, cell in enumerate(row)] for row in table]


def print_plain(artifacts: list[Artifact], title: str | None) -> None:
    rows = [Artifact.header()] + [a.cells() for a in artifacts]
    if title:
        print(f"== {title} ==")
    for row in justify(rows):
        print(" ".join(row))


def print_markdown(artifacts: list[Artifact], title: str | None) -> None:
    def fmt(i: int, text: str) -> str:
        return text if i == 0 else f"`{text}`"

    rows = [[fmt(i, cell) for i, cell in enumerate(a.cells())] for a in artifacts]
    rows.insert(0, Artifact.header())
    rows = justify(rows)
    rows.insert(1, [":" + "-" * (len(cell) - 1) for cell in rows[0]])
    if title:
        print(f"### {title}\n")
    for row in rows:
        print(f"| {' | '.join(row)} |")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-m",
        "--markdown",
        action="store_true",
        help="use markdown instead of plain text",
    )
    parser.add_argument("artifact_dir", nargs="?", default=".")
    args = parser.parse_args()

    all_artifacts = walk_dir(Path(args.artifact_dir))
    single_model = len(all_artifacts) == 1
    for model in sorted(all_artifacts.keys()):
        artifacts = all_artifacts[model]
        artifacts.sort(key=artifact_order)
        title = None if single_model else model
        if args.markdown:
            print_markdown(artifacts, title)
        else:
            print_plain(artifacts, title)
        print()


if __name__ == "__main__":
    main()
