import base64
import json
from pathlib import Path

from trezorlib.extapp import AppImage


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


def parse_image_to_json(app_image: AppImage) -> bytes:
    chunks = app_image.chunks()
    chunks_base64 = [base64_encode(chunk) for chunk, _ in chunks]
    chunk_hashes_hex = [hash.hex() for _, hash in chunks]

    header = app_image.header
    header_base64 = base64_encode(app_image.header_bytes())

    output_dict = {
        "name": header.name,
        "sdk_version": header.sdk_version,
        "abi_version": header.abi_version,
        "target_arch": header.target_arch,
        "app_ring": header.app_ring,
        "header": header_base64,
        "chunk_hashes": chunk_hashes_hex,
        "chunks": chunks_base64,
    }
    return json.dumps(output_dict, indent=2).encode()


def main() -> None:
    pass
    # Serialize bin apps to JSONs with the structure in the outfile
    # Take all apps from the outfile and create the trees/rootpackets/proofs
    #  - Optionally sign and timestamp the rootpackets
    # Create JSON indices (index.v1.json)
