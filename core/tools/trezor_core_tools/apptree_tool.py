import base64
import hashlib
import json
import typing as t
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

import click
from cryptography.hazmat.primitives.asymmetric import mldsa

from trezorlib.extapp import AppHeader, AppImage
from trezorlib.merkle_tree import MerkleTree
from trezorlib.root_packet import RootPacket, RootPacketAuth


@click.group()
def cli() -> None:
    """Trezor app tooling."""


# Rings sharing a single RootPacket, as (ring_mask, rings, base name).
ROOT_PACKET_GROUPS: tuple[tuple[int, tuple[int, ...]], ...] = (
    (1, (0,)),  # Rootpacket 0
    (6, (1, 2)),  # Rootpacket 1,2
)

# Hardcoded dummy development seeds (32 bytes each) for deterministic ML-DSA-44 key
# generation (FIPS 204 key generation is seeded by a 32-byte value). NOT for production.
DEV_SIGNING_SEEDS = (
    b"\x71" * 32,
    b"\x72" * 32,
)

ROOT_PACKET_DIR = "root-packets"
INDEX_FILENAME = "index.v1.json"
APP_EXT = "tapp"
APP_LANGUAGES = ("en", "cs", "de", "es", "fr", "id", "pt")


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


def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def base64_decode(base64_str: str) -> bytes:
    return base64.b64decode(base64_str)


def dict_as_json_str(dict: dict[str, t.Any]) -> str:
    return json.dumps(dict, indent=2)


def parse_bytes_to_appimage(app_bytes: bytes) -> AppImage:
    app_image = AppImage.parse(app_bytes, strict=True)
    return app_image


def parse_appimage_to_bytes(app_image: AppImage) -> bytes:
    app_bytes = app_image.build()
    return app_bytes


def parse_appimage_to_json(app_image: AppImage) -> str:
    chunks = app_image.chunks()
    chunks_base64 = [base64_encode(chunk) for chunk, _ in chunks]
    chunk_hashes_hex = [hash.hex() for _, hash in chunks]

    header = app_image.header
    header_base64 = base64_encode(app_image.header_bytes())

    output_dict = {
        "magic": header.magic.decode("ascii"),
        "header_size": header.header_size,
        "id": header.id,
        "name": header.name,
        "vendor": header.vendor,
        "model": header.model,
        "version": format_version_tuple_to_str(header.version),
        "sdk_version": format_version_tuple_to_str(header.sdk_version),
        "abi_version": header.abi_version,
        "target_arch": get_target_arch(header.target_arch),
        "app_ring": header.app_ring,
        "language": get_language(header.language),
        "code_size": header.code_size,
        "data_size": header.data_size,
        "chunk_hash": header.chunk_hash.hex(),
        "chunk_size": header.chunk_size,
        "curves": header.curves,
        "paths": header.paths,
        "ipc_buffer_size": header.ipc_buffer_size,
        "header": header_base64,
        "chunk_hashes": chunk_hashes_hex,
        "chunks": chunks_base64,
    }
    return dict_as_json_str(output_dict)


def parse_rootpacket_to_json(rootpacket: RootPacket) -> str:

    root_rings_hex = [root_ring.hex() for root_ring in rootpacket.auth.root_rings]
    rootpacket_base64 = base64_encode(rootpacket.build())
    output_dict = {
        "timestamp": f"{rootpacket.auth.timestamp} ({datetime.fromtimestamp(rootpacket.auth.timestamp, tz=timezone.utc)})",
        "chain_timestamp": f"{rootpacket.auth.chain_timestamp} ({datetime.fromtimestamp(rootpacket.auth.chain_timestamp, tz=timezone.utc)})",
        "ring_mask": f"{rootpacket.auth.ring_mask:08b}",
        "root_rings": root_rings_hex,
        "sigmask": f"{rootpacket.sigmask:08b}",
        "root_packet": rootpacket_base64,
    }
    return dict_as_json_str(output_dict)


def create_main_index(out_dir: Path) -> None:
    dirs: list[Path] = []
    for dir in sorted(out_dir.iterdir()):
        if dir.is_dir() and dir.name != ROOT_PACKET_DIR:
            dirs.append(dir)

    apps = {d.name: f"{d.name}/{INDEX_FILENAME}" for d in dirs}
    output_dict = {"apps": apps}

    main_index = dict_as_json_str(output_dict)
    main_index_file = out_dir / INDEX_FILENAME
    main_index_file.write_text(main_index)


def create_app_indices(out_dir: Path) -> None:
    app_dirs: list[Path] = []
    for dir in sorted(out_dir.iterdir()):
        if dir.is_dir() and dir.name != ROOT_PACKET_DIR:
            app_dirs.append(dir)

    for dir in app_dirs:
        releases: defaultdict[tuple, list[dict]] = defaultdict(list)
        for file in dir.glob(f"*/*{APP_EXT}"):
            if file.is_file():
                with open(file, "rb") as f:
                    app_json = json.load(f)
                    assert app_json["id"] == str(dir.relative_to(out_dir))
                    app_description = {
                        "abi": {
                            "platform": app_json["target_arch"],
                            "version": app_json["abi_version"],
                        },
                        "model": app_json["model"],
                        "language": app_json["language"],
                        "ring": app_json["app_ring"],
                        "file": str(file.relative_to(dir)),
                        "sha256": hashlib.file_digest(f, "sha256").hexdigest(),
                        "fingerprint": sha256(
                            base64_decode(app_json["header"])
                        ).hexdigest(),
                        "rootPacket": get_serialized_rootpacket(
                            out_dir, dir, ring=app_json["app_ring"]
                        ),
                    }
                    releases[
                        (tuple(app_json["version"]), tuple(app_json["sdk_version"]))
                    ].append(app_description)

        out_releases = [
            {"version": version, "sdkVersion": sdk_version, "builds": builds}
            for (version, sdk_version), builds in sorted(releases.items())
        ]
        output_dict = {"id": str(dir.relative_to(out_dir)), "releases": out_releases}
        index = dict_as_json_str(output_dict)
        index_file = dir / INDEX_FILENAME
        index_file.write_text(index)


def get_serialized_rootpacket(out_dir: Path, index_dir: Path, ring: int) -> str:
    rp_dir = out_dir / ROOT_PACKET_DIR
    rps: list[Path] = []
    for f in rp_dir.iterdir():
        if f.is_file():
            rps.append(f)
    if ring == 0:
        return [
            str(r.relative_to(index_dir, walk_up=True))
            for r in sorted(rps, reverse=True)
            if r.name.startswith("rootpacket_ring0")
        ][0]
    if ring in (1, 2):
        return [
            str(r.relative_to(index_dir, walk_up=True))
            for r in sorted(rps, reverse=True)
            if r.name.startswith("rootpacket_ring12")
        ][0]
    raise Exception("Failed to find a serialized rootpacket.")


@cli.command(name="post-build")
@click.argument(
    "apps",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-o",
    "--out-dir",
    type=click.Path(dir_okay=True, file_okay=False, path_type=Path),
    required=True,
)
def post_build(apps: tuple[Path, ...], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    app_infos: list[AppInfo] = []

    # Serialize bin apps to JSONs with the structure in the outdir
    for app in apps:
        app_bytes = app.read_bytes()
        app_image = parse_bytes_to_appimage(app_bytes)
        app_json_str = parse_appimage_to_json(app_image)
        header = app_image.header

        app_dir = out_dir / header.id / format_version_tuple_to_str(header.version)
        app_dir.mkdir(parents=True, exist_ok=True)
        out_file = app_dir / get_app_name(app_image)

        out_file.write_text(app_json_str)

    # Take all serialized apps (even previously created ones)
    for file in out_dir.glob(f"*/*/*{APP_EXT}"):
        if file.is_file():
            app_json = json.loads(file.read_text())
            app_header = AppHeader.parse(base64_decode(app_json["header"]))

            digest = app_header.fingerprint()
            app_ring = app_header.app_ring
            app_infos.append(AppInfo(file, digest, app_ring))

    timestamp = int(datetime.now(timezone.utc).timestamp())

    rp_dir = out_dir / ROOT_PACKET_DIR
    rp_dir.mkdir(parents=True, exist_ok=True)

    # Create trees/rootpackets/proofs
    for ring_mask, rings in ROOT_PACKET_GROUPS:
        trees = {ring: _get_tree(_filter_apps(app_infos, ring), ring) for ring in rings}
        if not any(trees.values()):
            continue

        for ring, tree in trees.items():
            if tree is not None:
                _create_proofs(_filter_apps(app_infos, ring), tree, store=True)

        rp = _make_root_packet(
            ring_mask=ring_mask,
            root_rings=[
                tree.get_root_hash() if tree is not None else b"\x00" * 32
                for tree in trees.values()
            ],
            timestamp=timestamp,
            chain_timestamp=0 if 0 in rings else timestamp,
        )
        _apply_dev_signatures(rp)

        rings_str = "".join(str(r) for r in rings)
        rootpacket_json_str = parse_rootpacket_to_json(rp)

        out_file = rp_dir / f"rootpacket_ring{rings_str}.tmr"
        out_file.write_text(rootpacket_json_str)
        print(f"Dev-signed RootPacket (timestamp {timestamp}) written to {out_file}")

    # Create JSON indices (index.v1.json)
    create_main_index(out_dir)
    create_app_indices(out_dir)


def _get_tree(apps: list[AppInfo], app_ring: int) -> MerkleTree | None:
    if not apps or len(apps) == 0:
        return None
    for app in apps:
        if app.app_ring != app_ring:
            raise ValueError("Param `apps` contains an app with unexpected app_ring.")
    app_tree = MerkleTree([app.digest for app in apps])
    return app_tree


def _filter_apps(apps: list[AppInfo], app_ring: int) -> list[AppInfo]:
    return [app for app in apps if app.app_ring == app_ring]


def _create_proofs(apps: list[AppInfo], tree: MerkleTree, store: bool = False) -> None:
    for app in apps:
        try:
            proof = tree.get_proof(app.digest)
            if store:
                proof_hex = [p.hex() for p in proof]
                proof_json_str = dict_as_json_str({"proof": proof_hex})
                out_file = app.path.with_suffix(".proof")
                out_file.write_text(proof_json_str)

        except KeyError:
            print(
                f"App {app.path} (app_ring {app.app_ring}) not found in the merkle tree. App hash: {app.digest}."
            )


def _make_root_packet(
    ring_mask: int,
    root_rings: list[bytes],
    timestamp: int = 0,
    chain_timestamp: int = 0,
) -> RootPacket:
    """Build an unsigned, unstamped RootPacket covering the given ring roots."""
    return RootPacket(
        auth=RootPacketAuth(
            ring_mask=ring_mask,
            reserved=b"\x00" * 2,
            timestamp=timestamp,
            chain_timestamp=chain_timestamp,
            root_rings=root_rings,
        ),
        sigmask=3,
        reserved=b"\x00" * 3,
        signature_0=b"\x00" * 2420,
        signature_1=b"\x00" * 2420,
    )


def _apply_dev_signatures(rp: RootPacket) -> bytes:
    """Sign `rp` in place with both dev keys; returns the signed digest."""
    keys = [mldsa.MLDSA44PrivateKey.from_seed_bytes(seed) for seed in DEV_SIGNING_SEEDS]

    rp.sigmask = 0b11
    digest = rp.digest()

    rp.signature_0 = keys[0].sign(digest)
    rp.signature_1 = keys[1].sign(digest)
    return digest


def get_app_name(app_image: AppImage) -> str:
    header = app_image.header
    app_id = header.id
    app_version = format_version_tuple_to_str(header.version)
    sdk_version = format_version_tuple_to_str(header.sdk_version[:2])
    target_arch = get_target_arch(header.target_arch)
    abi_version = header.abi_version
    model = header.model
    language = get_language(header.language)

    return f"{app_id}_{app_version}_sdk{sdk_version}_{target_arch}_abi{abi_version}_{model}_{language}.{APP_EXT}"


def format_version_tuple_to_str(version: tuple[int, ...]) -> str:
    return ".".join(str(v) for v in version)


def format_version_str_to_tuple(
    version: str,
) -> tuple[int, ...]:
    return tuple(int(v) for v in version.split("."))


def get_target_arch(target_arch_id: int) -> str:
    if target_arch_id == 0:
        return "armv8m"
    if target_arch_id == 1:
        return "linux-x86_64"
    if target_arch_id == 2:
        return "macos-aarch64"
    raise Exception("Unknown target architecture")


def get_language(language: int) -> str:
    if language >= len(APP_LANGUAGES):
        raise Exception("Unknown language")
    return APP_LANGUAGES[language]


if __name__ == "__main__":
    cli()
