#!/usr/bin/env python3
from __future__ import annotations

import typing as t
from hashlib import sha256
from pathlib import Path

import click

from trezorlib.merkle_tree import MerkleTree
from trezorlib.root_packet import RootPacket
from trezorlib.trezorapp import AppHeader, AppImage

if t.TYPE_CHECKING:
    from buffer_types import AnyBytes


def _get_files_iterator(*file_paths: Path) -> t.Iterator[tuple[Path, bytes]]:
    for path in file_paths:
        with path.open("rb") as f:
            yield path, f.read()


def _get_app_paths(
    dir: Path,
    extensions: t.Sequence[str] | None = None,
) -> list[Path]:
    if extensions is None:
        extensions = [".py"]
    app_paths: list[Path] = []
    for path in sorted(dir.iterdir()):
        if path.is_file():
            if path.suffix in extensions:
                app_paths.append(path)
    return app_paths


def print_apps(*app_paths: Path) -> None:
    name_width = max(len(str(path)) for path in app_paths)

    print("-" * name_width)
    for path, data in _get_files_iterator(*app_paths):
        size = f"{len(data):,}".replace(",", " ")
        print(
            f"{str(path):<{name_width}}{size:>10} bytes {_get_app_digest(data)[:8].hex()}"
        )
    print("-" * name_width + "\n")


def _get_app_dict(*app_paths: Path) -> dict[bytes, str]:
    app_dict: dict[bytes, str] = {}

    for path, data in _get_files_iterator(*app_paths):
        app_dict[_get_app_digest(data)] = path.stem
    return app_dict


def _get_app_digest(app: AnyBytes) -> bytes:
    return sha256(app).digest()


def _print_app_tree(app_dict: dict[bytes, str], tree: MerkleTree) -> None:
    name_width = max(len(str(name)) for name in app_dict.values())
    print(f"Root hash: {tree.get_root_hash().hex()}\n")
    for hash, name in app_dict.items():
        _print_proof(
            name,
            hash,
            tree.get_proof(hash),
            name_width=name_width,
        )


def _print_proof(
    name: str, hash: bytes, proof: t.Iterable[bytes], name_width: int = 0
) -> None:

    print(f"{name:<{name_width + 1}} {hash[:8].hex()} {[p[:4].hex() for p in proof]}")


@click.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
def cli(directory: Path) -> None:
    app_paths = _get_app_paths(dir=directory)
    print_apps(*app_paths)

    app_dict = _get_app_dict(*app_paths)
    app_tree = MerkleTree(app_dict.keys())

    _print_app_tree(app_dict, app_tree)
    rp0 = RootPacket(
        ring_mask=1,
        timestamp=0x78563412,
        sigmask=3,
        root_rings=[app_tree.get_root_hash()],
        signature_0=b"\x11" * 2420,
        signature_1=b"\x22" * 2420,
    )
    rp_0_bytes = rp0.build()
    print("\n\nRootPacket:")
    print(rp_0_bytes.hex())


@click.command()
def generate_apps() -> None:
    default_magic = 0x415A5254
    header = AppHeader(
        magic=default_magic,
        header_size=2,
        id="",
        name="str",
        vendor="",
        model="TTTT",
        version=(1, 2, 3, 4),
        sdk_version=(5, 6, 7, 8),
        abi_version=-5,
        target_architecture=5,
        app_ring=1,
        code_size=1,
        data_size=1,
        chunk_hash=b"\x00",
        chunk_size=1024,
    )
    app_image = AppImage(header=header, payload=b"\x00")
    print(app_image)


if __name__ == "__main__":
    cli()
