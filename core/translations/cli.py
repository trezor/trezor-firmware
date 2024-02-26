from __future__ import annotations

import datetime
import json
import logging
import typing as t
import subprocess
from pathlib import Path

import click

from trezorlib import cosi, models, merkle_tree
from trezorlib._internal import translations

HERE = Path(__file__).parent.resolve()
LOG = logging.getLogger(__name__)

ALL_MODELS = {models.T2B1, models.T2T1}

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]

PUBLIC_KEYS_PROD = [
    bytes.fromhex(key)
    for key in (
        # TODO add production public keys
        "aabbccdd" * 8,
        "11223344" * 8,
        "55667788" * 8,
    )
]

VERSION_H = HERE.parent / "embed" / "firmware" / "version.h"
SIGNATURES_JSON = HERE / "signatures.json"


class SignatureInfo(t.TypedDict):
    merkle_root: str
    signature: str | None
    datetime: str
    commit: str


class SignatureFile(t.TypedDict):
    current: SignatureInfo
    history: list[SignatureInfo]


def _version_from_version_h() -> translations.VersionTuple:
    defines: t.Dict[str, int] = {}
    with open(VERSION_H) as f:
        for line in f:
            try:
                define, symbol, number = line.rstrip().split()
                assert define == "#define"
                defines[symbol] = int(number)
            except Exception:
                # not a #define, not a number, wrong number of parts
                continue

    return (
        defines["VERSION_MAJOR"],
        defines["VERSION_MINOR"],
        defines["VERSION_PATCH"],
        defines["VERSION_BUILD"],
    )


def make_signature_info(merkle_root: bytes, signature: bytes | None) -> SignatureInfo:
    now = datetime.datetime.utcnow()
    commit = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE)
        .decode("ascii")
        .strip()
    )
    return SignatureInfo(
        merkle_root=merkle_root.hex(),
        signature=signature.hex() if signature is not None else None,
        datetime=now.isoformat(),
        commit=commit,
    )


def update_merkle_root(signature_file: SignatureFile, merkle_root: bytes) -> bool:
    """Update signatures.json with the new Merkle root.

    Returns True if the signature file was updated, False if it was already up-to-date.
    """
    current = signature_file["current"]

    if current["merkle_root"] == merkle_root.hex():
        # Merkle root is already up to date
        return False

    if current["signature"] is None:
        # current content is not signed. just overwrite with a new one
        signature_file["current"] = make_signature_info(merkle_root, None)
        SIGNATURES_JSON.write_text(json.dumps(signature_file, indent=2))
        return True

    # move current to history
    signature_file["history"].insert(0, current)
    # create new current
    signature_file["current"] = make_signature_info(merkle_root, None)
    return True


def generate_all_blobs(rewrite_version: bool) -> list[translations.TranslationsBlob]:
    order = translations.order_from_json(json.loads((HERE / "order.json").read_text()))
    fonts_dir = HERE / "fonts"

    current_version = _version_from_version_h()
    current_version_str = ".".join(str(v) for v in current_version)

    common_version = None

    all_languages = [lang_file.stem for lang_file in HERE.glob("??.json")]
    # TEMP: not generating czech blob - it is not final
    all_languages.remove("cs")
    all_blobs: list[translations.TranslationsBlob] = []
    for lang in all_languages:
        if lang == "en":
            continue

        for model in ALL_MODELS:
            try:
                blob_json = json.loads((HERE / f"{lang}.json").read_text())
                blob_version = translations.version_from_json(
                    blob_json["header"]["version"]
                )
                if rewrite_version:
                    version = current_version
                    if blob_version != current_version:
                        blob_json["header"]["version"] = current_version_str
                        (HERE / f"{lang}.json").write_text(
                            json.dumps(blob_json, indent=2) + "\n"
                        )

                else:
                    version = blob_version
                    if common_version is None:
                        common_version = version
                    elif blob_version != common_version:
                        raise ValueError(
                            f"Language {lang} has version {version} but expected {common_version}"
                        )

                blob = translations.blob_from_defs(
                    blob_json, order, model, version, fonts_dir
                )
                all_blobs.append(blob)
            except Exception as e:
                import traceback

                traceback.print_exc()
                LOG.warning(f"Failed to build {lang} for {model.internal_name}: {e}")
                continue

            LOG.info(f"Built {lang} for {model.internal_name}")

    return all_blobs


def build_all_blobs(
    all_blobs: list[translations.TranslationsBlob],
    merkle_tree: merkle_tree.MerkleTree,
    sigmask: int,
    signature: bytes,
    production: bool = False,
) -> None:
    for blob in all_blobs:
        proof = translations.Proof(
            merkle_proof=merkle_tree.get_proof(blob.header_bytes),
            signature=signature,
            sigmask=sigmask,
        )
        blob.proof = proof
        header = blob.header
        model = header.model.value.decode("ascii")
        version = ".".join(str(v) for v in header.firmware_version[:3])
        if production:
            suffix = ""
        else:
            suffix = "-unsigned"
        filename = f"translation-{model}-{header.language}-{version}{suffix}.bin"
        (HERE / filename).write_bytes(blob.build())
        LOG.info(f"Wrote {header.language} for {model} v{version}: {filename}")


@click.group()
def cli() -> None:
    pass


@cli.command()
def gen() -> None:
    """Generate all language blobs for all models.

    The generated blobs will be signed with the development keys.
    """
    all_blobs = generate_all_blobs(rewrite_version=True)
    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()
    signature = cosi.sign_with_privkeys(root, PRIVATE_KEYS_DEV)
    sigmask = 0b111
    build_all_blobs(all_blobs, tree, sigmask, signature)

    signature_file = json.loads(SIGNATURES_JSON.read_text())
    if update_merkle_root(signature_file, root):
        SIGNATURES_JSON.write_text(json.dumps(signature_file, indent=2) + "\n")
        click.echo("Updated signatures.json")
    else:
        click.echo("signatures.json is already up-to-date")


@cli.command()
def merkle_root() -> None:
    """Print the Merkle root of all language blobs."""
    all_blobs = generate_all_blobs(rewrite_version=False)
    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()

    signature_file: SignatureFile = json.loads(SIGNATURES_JSON.read_text())
    if signature_file["current"]["merkle_root"] != root.hex():
        raise click.ClickException(
            f"Merkle root mismatch!\n"
            f"Expected:                  {root.hex()}\n"
            f"Stored in signatures.json: {signature_file['current']['merkle_root']}\n"
            "Run `cli.py gen` to update the stored Merkle root."
        )

    click.echo(root.hex())


@cli.command()
@click.argument("signature_hex", required=False)
@click.option("--force", is_flag=True)
def sign(signature_hex: str | None, force: bool) -> None:
    """Insert a signature into language blobs.

    If signature_hex is not provided, the signature will be located in signatures.json.
    """
    all_blobs = generate_all_blobs(rewrite_version=False)
    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()

    signature_file: SignatureFile = json.loads(SIGNATURES_JSON.read_text())
    if signature_file["current"]["merkle_root"] != root.hex():
        raise click.ClickException(
            f"Merkle root mismatch!\n"
            f"Expected:                  {root.hex()}\n"
            f"Stored in signatures.json: {signature_file['current']['merkle_root']}"
        )

    if signature_hex is None:
        if signature_file["current"]["signature"] is None:
            raise click.ClickException("Please provide a signature.")
        signature_hex = signature_file["current"]["signature"]
    elif (
        not force
        and signature_file["current"]["signature"] is not None
        and signature_file["current"]["signature"] != signature_hex
    ):
        raise click.ClickException(
            "A different signature is already present in signatures.json\n"
            "Use --force to overwrite it."
        )
    else:
        # Update signature file data. It will be written only if the signature verifies.
        signature_file["current"]["signature"] = signature_hex
        signature_file["current"]["datetime"] = datetime.datetime.utcnow().isoformat()

    signature_bytes = bytes.fromhex(signature_hex)
    sigmask, signature = signature_bytes[0], signature_bytes[1:]

    try:
        cosi.verify(signature, root, 2, PUBLIC_KEYS_PROD, sigmask)
    except Exception as e:
        if force:
            LOG.warning(f"Invalid signature: {e}. --force is provided, writing anyway.")
            pass
        else:
            raise click.ClickException(f"Invalid signature: {e}") from e

    SIGNATURES_JSON.write_text(json.dumps(signature_file, indent=2) + "\n")
    build_all_blobs(all_blobs, tree, sigmask, signature, production=True)


if __name__ == "__main__":
    cli()
