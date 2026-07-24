#!/usr/bin/env python3
from __future__ import annotations

import typing as t
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import click
from construct import SizeofError
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import mldsa

from trezorlib.merkle_tree import MerkleTree, evaluate_proof
from trezorlib.root_packet import RootPacket, RootPacketAuth
from trezorlib.trezorapp import AppHeader, AppImage

# Genesis of the root-packet timestamp: 2026-06-14 12:00 UTC.
# The firmware only requires the stored timestamp to be non-zero; the epoch itself is a
# tooling convention, so adjust here if a different reference is desired.
TIMESTAMP_GENESIS = datetime(2026, 6, 14, 12, 0, 0, tzinfo=timezone.utc)

# Hardcoded dummy development seeds (32 bytes each) for deterministic ML-DSA-44 key
# generation (FIPS 204 key generation is seeded by a 32-byte value). NOT for production.
DEV_SIGNING_SEEDS = (
    b"\x71" * 32,
    b"\x72" * 32,
)


class AppInfo:
    def __init__(self, path: Path, digest: bytes, app_ring: int) -> None:
        if not path.exists() or not path.is_file():
            raise ValueError("Invalid path.")
        if len(digest) != 32:
            raise ValueError("Invalid digest length.")
        if app_ring < 0 or app_ring > 2:
            raise ValueError("Invalid app ring.")

        self.path = path
        self.digest = digest
        self.app_ring = app_ring


def _fixed_header_size() -> int:
    """Size of the fixed header fields.

    Excludes the trailing ``reserved_3`` padding, whose length depends on
    ``header_size`` itself (so ``AppHeader.SUBCON.sizeof()`` can't be used).
    """
    size = 0
    for subcon in getattr(AppHeader.SUBCON, "subcons", ()):
        try:
            size += subcon.sizeof()
        except SizeofError:
            continue
    return size


def _get_files_iterator(*file_paths: Path) -> t.Iterator[tuple[Path, bytes]]:
    for path in file_paths:
        with path.open("rb") as f:
            yield path, f.read()


def _get_app_paths(
    dir: Path,
    extensions: t.Sequence[str] | None = None,
) -> list[Path]:
    if extensions is None:
        extensions = [".tapp"]
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


def _get_app_digest(raw_app: bytes) -> bytes:
    app = AppImage.parse(raw_app)
    return app.header_hash()


@click.group()
def cli() -> None:
    """Trezor app tooling."""


@cli.command()
@click.argument(
    "directory",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "-o",
    "--out-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=Path),
    is_flag=False,
    flag_value=".",
    default=None,
    help="Write the built RootPacket(s) to a file(s) in the given directory.",
)
def build_rootpackets(directory: Path, out_dir: Path | None) -> None:
    app_paths = _get_app_paths(dir=directory)
    if not app_paths:
        raise click.ClickException(f"No .tapp files found in {directory}")
    print_apps(*app_paths)
    apps = _get_app_info_list(*app_paths)

    tree_0 = _get_tree(_filter_apps(apps, 0), app_ring=0)
    tree_1 = _get_tree(_filter_apps(apps, 1), app_ring=1)
    tree_2 = _get_tree(_filter_apps(apps, 2), app_ring=2)

    if tree_0 is not None:
        out_file: Path | None = None

        if out_dir:
            out_file = out_dir / "rootpacket_0.tmr"

        _create_proofs(_filter_apps(apps, 0), tree_0, store=out_dir is not None)

        _create_rootpacket(
            ring_mask=1,
            root_rings=[tree_0.get_root_hash()],
            out_file=out_file,
        )
    if tree_1 or tree_2:
        root_1, root_2 = b"\x00" * 32, b"\x00" * 32
        if tree_1:
            root_1 = tree_1.get_root_hash()
            _create_proofs(_filter_apps(apps, 1), tree_1, store=out_dir is not None)

        if tree_2:
            root_2 = tree_2.get_root_hash()
            _create_proofs(_filter_apps(apps, 2), tree_2, store=out_dir is not None)

        out_file: Path | None = None
        if out_dir:
            out_file = out_dir / "rootpacket_12.tmr"

        _create_rootpacket(
            ring_mask=6,
            root_rings=[root_1, root_2],
            out_file=out_file,
        )


def _create_rootpacket(
    ring_mask: int, root_rings: list[bytes], out_file: Path | None
) -> None:
    rp = RootPacket(
        auth=RootPacketAuth(
            ring_mask=ring_mask,
            sigmask=3,
            timestamp=0,
            root_rings=root_rings,
        ),
        signature_0=b"\x00" * 2420,
        signature_1=b"\x00" * 2420,
    )
    rp_bytes = rp.build()
    print("\nRoot packet raw_bytes:")
    print(rp_bytes.hex())
    _print_root_packet(rp)

    if out_file is not None:
        out_file.write_bytes(rp_bytes)
        print(f"\nRootPacket written to {out_file}")


def _create_proofs(apps: list[AppInfo], tree: MerkleTree, store: bool = False) -> None:
    for app in apps:
        try:
            proof = tree.get_proof(app.digest)
            _print_proof(str(app.path), app.digest, proof)
            if store:
                out_file = _change_suffix(app.path, ".proof")
                out_file.write_bytes(b"".join(proof))

        except KeyError:
            print(
                f"App {app.path} (app_ring {app.app_ring}) not found in the merkle tree. App hash: {app.digest}."
            )


def _print_proof(
    name: str, hash: bytes, proof: t.Iterable[bytes], name_width: int = 0
) -> None:
    leaf_hash = sha256(b"\x00" + hash).digest()
    print(
        f"{name:<{name_width + 1}} {hash[:8].hex()} -> {leaf_hash[:4].hex()} {[p[:4].hex() for p in proof]}"
    )


def _get_tree(apps: list[AppInfo], app_ring: int) -> MerkleTree | None:
    if not apps or len(apps) == 0:
        return None
    for app in apps:
        if app.app_ring != app_ring:
            raise ValueError("Param `apps` contains an app with unexpected app_ring.")
    app_tree = MerkleTree([app.digest for app in apps])
    return app_tree


def _filter_apps(apps: list[AppInfo], app_ring: int):
    return [app for app in apps if app.app_ring == app_ring]


def _get_app_info_list(
    *app_paths: Path,
) -> list[AppInfo]:
    app_info_list: list[AppInfo] = []
    for path, data in _get_files_iterator(*app_paths):
        app = AppImage.parse(data)
        app_ring = app.header.app_ring
        digest = app.header_hash()
        app_info_list.append(AppInfo(path, digest, app_ring))
    return app_info_list


@cli.command()
@click.option(
    "-o",
    "--out-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=Path),
    is_flag=False,
    flag_value=".",
    default=None,
    help="Write the built AppImage(s) to the given dir.",
)
@click.option(
    "-t",
    "--test",
    type=int,
    default=1,
    help="Generate given number of test apps.",
)
@click.option(
    "-r",
    "--app-ring",
    type=int,
    default=1,
    help="App ring of the generated apps.",
)
def generate_apps(out_dir: Path | None, test: int, app_ring: int) -> None:

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)

    n_digits = len(str(test - 1))
    for i in range(test):
        idx_str = f"{i:0{n_digits}}"
        app_image = _generate_app_image(
            app_ring=app_ring,
            id=f"mock_app_{idx_str}",
            name=f"Best testing app number {idx_str}",
        )
        print(app_image)
        if out_dir is not None:
            out_file = out_dir / (f"app_r{app_ring}_{idx_str}.tapp")
            out_file.write_bytes(app_image.build())
            print(f"AppImage written to {out_file}")


def _generate_app_image(
    app_ring: int,
    id: str,
    name: str = "dummy_app",
    payload: bytes = b"\xde\xad\xbe\xef",
) -> AppImage:
    header = AppHeader(
        magic=b"TRZA",
        header_size=_fixed_header_size(),
        id=id,
        name=name,
        vendor="",
        model="T3W1",
        version=(1, 2, 3, 4),
        sdk_version=(5, 6, 7, 8),
        abi_version=5,
        target_arch=5,
        app_ring=app_ring,
        code_size=1,
        data_size=1,
        chunk_hash=b"\x00" * 32,
        chunk_size=1024,
        curves=[],
        paths=[],
    )
    return AppImage(header=header, payload=payload)


def _print_root_packet(rp: RootPacket) -> None:
    auth = rp.auth
    print("RootPacket:")
    print(f"  ring_mask:   {auth.ring_mask:#04x}")
    print(f"  timestamp:   {auth.timestamp} ({auth.timestamp:#010x})")
    print(f"  sigmask:     {auth.sigmask:#04x}")
    for index, root in auth.rings.items():
        print(f"  ring[{index}]:     {root.hex()}")
    print(f"  signature_0: {rp.signature_0[:8].hex()}… ({len(rp.signature_0)} bytes)")
    print(f"  signature_1: {rp.signature_1[:8].hex()}… ({len(rp.signature_1)} bytes)")
    print(f"  digest:      {rp.digest().hex()}")


def _suffixed_path(path: Path, suffix: str) -> Path:
    """`foo.tmr` -> `foo-<suffix>.tmr`."""
    return path.with_stem(path.stem + f"-{suffix}")


def _change_suffix(path: Path, suffix: str) -> Path:
    return path.with_suffix(suffix)


@cli.command(name="show")
@click.argument(
    "rootpacket",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def show(rootpacket: Path) -> None:
    """Parse a RootPacket from a file and print it structured."""
    rp = RootPacket.parse(rootpacket.read_bytes())
    _print_root_packet(rp)


@cli.command()
@click.argument(
    "rootpacket",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def timestamp(rootpacket: Path) -> None:
    """Stamp a RootPacket with the current time (seconds since genesis)."""
    rp = RootPacket.parse(rootpacket.read_bytes())
    _print_root_packet(rp)

    time_now = datetime.now(timezone.utc)
    # Signed offset (in seconds) from the genesis; may be negative before the genesis.
    time_signed = int((time_now - TIMESTAMP_GENESIS).total_seconds())
    print(f"\nCurrent time (human):   {time_now.isoformat()}")
    print(
        f"Current time (genesis): {time_signed} seconds since {TIMESTAMP_GENESIS.isoformat()}"
    )

    # The on-device field is a uint32, so store the two's-complement of the signed value.
    rp.auth.timestamp = time_signed & 0xFFFFFFFF

    out_file = _suffixed_path(rootpacket, "timestamped")
    out_file.write_bytes(rp.build())
    print(f"\nTimestamped RootPacket written to {out_file}")


@cli.command()
@click.argument(
    "rootpacket",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def sign(rootpacket: Path) -> None:
    """Sign a (timestamped) RootPacket with the two dev ML-DSA-44 keys."""
    rp = RootPacket.parse(rootpacket.read_bytes())
    _print_root_packet(rp)

    keys = [mldsa.MLDSA44PrivateKey.from_seed_bytes(seed) for seed in DEV_SIGNING_SEEDS]

    rp.auth.sigmask = 0b11
    digest = rp.digest()

    rp.signature_0 = keys[0].sign(digest)
    rp.signature_1 = keys[1].sign(digest)

    out_file = _suffixed_path(rootpacket, "signed")
    out_file.write_bytes(rp.build())
    print(f"\nSigned RootPacket (digest {digest.hex()}) written to {out_file}")


@cli.command()
@click.argument(
    "rootpacket",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def verify(rootpacket: Path) -> None:
    """Verify a signed RootPacket against the dev ML-DSA-44 keys."""
    rp = RootPacket.parse(rootpacket.read_bytes())
    _print_root_packet(rp)

    public_keys = [
        mldsa.MLDSA44PrivateKey.from_seed_bytes(seed).public_key()
        for seed in DEV_SIGNING_SEEDS
    ]
    digest = rp.digest()
    signatures = [rp.signature_0, rp.signature_1]

    print()
    checked = 0
    failed = 0
    for slot, (pubkey, signature) in enumerate(zip(public_keys, signatures)):
        if not rp.auth.sigmask & (1 << slot):
            print(f"  signature_{slot}: skipped (sigmask bit {slot} clear)")
            continue
        checked += 1
        try:
            pubkey.verify(signature, digest)
            print(f"  signature_{slot}: OK (dev key {slot})")
        except InvalidSignature:
            print(f"  signature_{slot}: FAILED")
            failed += 1

    if checked == 0:
        raise click.ClickException(
            f"sigmask {rp.auth.sigmask:#04x} selects no signatures"
        )
    if failed:
        raise click.ClickException(
            f"{failed} of {checked} signature(s) failed to verify"
        )
    print(f"\nAll {checked} selected signature(s) verify.")


@cli.command(name="verify-app")
@click.argument(
    "app",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "proof",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.argument(
    "rootpacket",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def verify_app(app: Path, proof: Path, rootpacket: Path) -> None:
    """Verify an app's Merkle proof against the root stored in a RootPacket.

    Parses the app to obtain its digest and ring, evaluates the Merkle proof, and
    checks that the reconstructed root matches the RootPacket root for that ring.
    """
    app_image = AppImage.parse(app.read_bytes())
    digest = app_image.header_hash()
    app_ring = app_image.header.app_ring

    proof_bytes = proof.read_bytes()
    if len(proof_bytes) % 32 != 0:
        raise click.ClickException(
            f"Proof length {len(proof_bytes)} is not a multiple of 32 bytes"
        )
    proof_entries = [proof_bytes[i : i + 32] for i in range(0, len(proof_bytes), 32)]

    rp = RootPacket.parse(rootpacket.read_bytes())

    print(f"App:      {app}")
    print(f"  digest:   {digest.hex()}")
    print(f"  app_ring: {app_ring}")
    print(f"  proof:    {[p[:4].hex() for p in proof_entries]}")

    if not rp.auth.has_ring(app_ring):
        raise click.ClickException(
            f"RootPacket (mask {rp.auth.ring_mask:#04x}) has no root for ring {app_ring}"
        )
    expected_root = rp.auth.ring(app_ring)
    computed_root = evaluate_proof(digest, proof_entries)

    print(f"\n  expected root (ring {app_ring}): {expected_root.hex()}")
    print(f"  computed root:          {computed_root.hex()}")

    if computed_root != expected_root:
        raise click.ClickException("Merkle proof does NOT match the RootPacket root")
    print("\nApp verified: Merkle proof matches the RootPacket root.")


if __name__ == "__main__":
    cli()
