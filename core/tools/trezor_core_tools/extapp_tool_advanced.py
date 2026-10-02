import base64
import json
from pathlib import Path
import click
from datetime import datetime, timezone

from trezorlib.extapp import AppImage
from trezorlib.merkle_tree import MerkleTree, evaluate_proof
from trezorlib.root_packet import RootPacket, RootPacketAuth
from cryptography.hazmat.primitives.asymmetric import mldsa


@click.group()
def cli() -> None:
    """Trezor app tooling."""


# Rings sharing a single RootPacket, as (ring_mask, rings, base name).
ROOT_PACKET_GROUPS: tuple[tuple[int, tuple[int, ...], str], ...] = (
    (1, (0,), "rootpacket_0"),
    (6, (1, 2), "rootpacket_12"),
)

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


def base64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def load_app_bin(path: Path) -> bytes:
    raise NotImplementedError


def parse_bytes_to_image(app_bytes: bytes) -> AppImage:
    app_image = AppImage.parse(app_bytes, strict=True)
    return app_image


def parse_image_to_bytes(app_image: AppImage) -> bytes:
    app_bytes = app_image.build()
    return app_bytes


def parse_image_to_json(app_image: AppImage) -> str:
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
        "version": header.version,
        "sdk_version": header.sdk_version,
        "abi_version": header.abi_version,
        "target_arch": header.target_arch,
        "app_ring": header.app_ring,
        "language": header.language,
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
    return json.dumps(output_dict, indent=2)


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

    # Serialize bin apps to JSONs with the structure in the outfile
    for app in apps:
        app_bytes = app.read_bytes()
        app_image = parse_bytes_to_image(app_bytes)
        app_json_str = parse_image_to_json(app_image)

        app_dir = out_dir / app_image.header.id
        app_dir.mkdir(parents=True, exist_ok=True)

        out_file = app_dir / get_app_name(app_image)

        out_file.write_text(app_json_str)

    # Take all serialized apps (even previously created ones)
    for file in out_dir.glob(f"*/*tapp"):
        if file.is_file():
            app_infos.append(
                AppInfo(file, app_image.fingerprint(), app_image.header.app_ring)
            )

    timestamp = int(datetime.now(timezone.utc).timestamp())

    rp_dir = out_dir / "root-packets"
    rp_dir.mkdir(parents=True, exist_ok=True)

    # Create trees/rootpackets/proofs
    for ring_mask, rings, name in ROOT_PACKET_GROUPS:
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
            chain_timestamp=timestamp,
        )
        _apply_dev_signatures(rp)

        rings_str = "".join(str(r) for r in rings)
        out_file = rp_dir / f"ring{rings_str}-{rp.auth.timestamp}-signed.tmr"
        out_file.write_bytes(rp.build())
        print(f"Dev-signed RootPacket (timestamp {timestamp}) written to {out_file}")

    # Create JSON indices (index.v1.json)


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
                out_file = app.path.with_suffix(".proof")
                out_file.write_bytes(b"".join(proof))

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
    app_version = ".".join(str(v) for v in header.version)
    sdk_version = ".".join(str(v) for v in header.sdk_version[:2])
    target_arch = get_target_arch(header.target_arch)
    abi_version = header.abi_version
    model = header.model
    language = get_language(header.language)
    ext = "tapp"

    return f"{app_id}_{app_version}_sdk{sdk_version}_{target_arch}_abi{abi_version}_{model}_{language}.{ext}"


def get_target_arch(target_arch_id: int) -> str:
    if target_arch_id == 0:
        return "armv8m"
    if target_arch_id == 1:
        return "linux-x64_64"
    raise Exception("Unknown target architecture")


def get_language(language: int) -> str:
    if language == 0:
        return "en"
    if language == 1:
        return "cs"
    raise Exception("Unknown language")


if __name__ == "__main__":
    cli()
