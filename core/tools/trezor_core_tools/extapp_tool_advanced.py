import base64
import json
from pathlib import Path
import click

from trezorlib.extapp import AppImage


@click.group()
def cli() -> None:
    """Trezor app tooling."""


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

    for app in apps:
        app_bytes = app.read_bytes()
        app_image = parse_bytes_to_image(app_bytes)
        app_json_str = parse_image_to_json(app_image)

        app_dir = out_dir / app_image.header.id
        app_dir.mkdir(parents=True, exist_ok=True)

        out_file = app_dir / get_app_name(app_image)

        out_file.write_text(app_json_str)
    # Serialize bin apps to JSONs with the structure in the outfile
    # Take all apps from the outfile and create the trees/rootpackets/proofs
    #  - Optionally sign and timestamp the rootpackets
    # Create JSON indices (index.v1.json)


def get_app_name(app_image: AppImage) -> str:
    header = app_image.header
    app_id = header.id
    app_version = ".".join(str(v) for v in header.version)
    sdk_version = ".".join(str(v) for v in header.sdk_version[:2])
    target_arch = get_target_arch(header.target_arch)
    abi_version = header.abi_version
    model = header.model
    language = get_language(header.language)
    ext = "json"

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
