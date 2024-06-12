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
from trezorlib._internal.translations import VersionTuple

HERE = Path(__file__).parent.resolve()
LOG = logging.getLogger(__name__)

ALL_MODELS = {models.T2B1, models.T2T1, models.T3T1}

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]

PUBLIC_KEYS_PROD = [
    bytes.fromhex(key)
    for key in (
        "62cea8257b0bca15b33a76405a79c4881eb20ee82346813181a50291d6caec67",
        "594ef09e51139372e528c6c5b8742ee1806f9114caeaeedb04be6a98e1ce3020",
    )
]

VERSION_H = HERE.parent / "embed" / "firmware" / "version.h"
SIGNATURES_JSON = HERE / "signatures.json"


class SignedInfo(t.TypedDict):
    merkle_root: str
    signature: str
    datetime: str
    commit: str
    version: str


class UnsignedInfo(t.TypedDict):
    merkle_root: str
    datetime: str
    commit: str


class SignatureFile(t.TypedDict):
    current: UnsignedInfo
    history: list[SignedInfo]


def _version_from_version_h() -> VersionTuple:
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


def _version_str(version: tuple[int, ...]) -> str:
    return ".".join(str(v) for v in version)


def make_tree_info(merkle_root: bytes) -> UnsignedInfo:
    now = datetime.datetime.utcnow()
    commit = (
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE)
        .decode("ascii")
        .strip()
    )
    return UnsignedInfo(
        merkle_root=merkle_root.hex(), datetime=now.isoformat(), commit=commit
    )


def sign_info(
    info: UnsignedInfo, signature: bytes, version: VersionTuple
) -> SignedInfo:
    return SignedInfo(signature=signature.hex(), version=_version_str(version), **info)


def update_merkle_root(signature_file: SignatureFile, merkle_root: bytes) -> bool:
    """Update signatures.json with the new Merkle root.

    Returns True if the signature file was updated, False if it was already up-to-date.
    """
    current = signature_file["current"]

    if current["merkle_root"] == merkle_root.hex():
        # Merkle root is already up to date
        return False

    # overwrite with a new one
    signature_file["current"] = make_tree_info(merkle_root)
    SIGNATURES_JSON.write_text(json.dumps(signature_file, indent=2))
    return True


class TranslationsDir:
    def __init__(self, path: Path = HERE):
        self.path = path
        self.order = translations.order_from_json(
            json.loads((self.path / "order.json").read_text())
        )

    @property
    def fonts_dir(self) -> Path:
        return self.path / "fonts"

    def _lang_path(self, lang: str) -> Path:
        return self.path / f"{lang}.json"

    def load_lang(self, lang: str) -> translations.JsonDef:
        return json.loads(self._lang_path(lang).read_text())

    def save_lang(self, lang: str, data: translations.JsonDef) -> None:
        self._lang_path(lang).write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            )
            + "\n"
        )

    def all_languages(self) -> t.Iterable[str]:
        return (lang_file.stem for lang_file in self.path.glob("??.json"))

    def update_version_from_h(self) -> VersionTuple:
        version = _version_from_version_h()
        for lang in self.all_languages():
            blob_json = self.load_lang(lang)
            blob_version = translations.version_from_json(
                blob_json["header"]["version"]
            )
            if blob_version != version:
                blob_json["header"]["version"] = _version_str(version[:3])
                self.save_lang(lang, blob_json)
        return version

    def generate_single_blob(
        self,
        lang: str,
        model: models.TrezorModel,
        version: VersionTuple | None,
    ) -> translations.TranslationsBlob:
        blob_json = self.load_lang(lang)
        blob_version = translations.version_from_json(blob_json["header"]["version"])
        return translations.blob_from_defs(
            blob_json, self.order, model, version or blob_version, self.fonts_dir
        )

    def generate_all_blobs(
        self, version: VersionTuple | None
    ) -> list[translations.TranslationsBlob]:
        common_version = None

        all_blobs: list[translations.TranslationsBlob] = []
        for lang in self.all_languages():
            if lang == "en":
                continue

            for model in ALL_MODELS:
                try:
                    blob = self.generate_single_blob(lang, model, version)
                    blob_version = blob.header.firmware_version
                    if common_version is None:
                        common_version = blob_version
                    elif blob_version != common_version:
                        raise ValueError(
                            f"Language {lang} has version {blob_version} but expected {common_version}"
                        )
                    all_blobs.append(blob)
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    LOG.warning(
                        f"Failed to build {lang} for {model.internal_name}: {e}"
                    )
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
        version = _version_str(header.firmware_version[:3])
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
@click.option("--signed", is_flag=True, help="Generate signed blobs.")
@click.option(
    "--version", "version_str", help="Set the blob version independent of JSON data."
)
def gen(signed: bool | None, version_str: str | None) -> None:
    """Generate all language blobs for all models.

    The generated blobs will be signed with the development keys.
    """
    tdir = TranslationsDir()

    if version_str is None:
        version = tdir.update_version_from_h()
    else:
        version = translations.version_from_json(version_str)

    all_blobs = tdir.generate_all_blobs(version)
    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()

    signature_file: SignatureFile = json.loads(SIGNATURES_JSON.read_text())

    if signed:
        for entry in signature_file["history"]:
            if entry["merkle_root"] == root.hex():
                signature_hex = entry["signature"]
                signature_bytes = bytes.fromhex(signature_hex)
                sigmask, signature = signature_bytes[0], signature_bytes[1:]
                build_all_blobs(all_blobs, tree, sigmask, signature, production=True)
                return
        else:
            raise click.ClickException(
                "No matching signature found in signatures.json. Run `cli.py sign` first."
            )

    signature = cosi.sign_with_privkeys(root, PRIVATE_KEYS_DEV)
    sigmask = 0b111
    build_all_blobs(all_blobs, tree, sigmask, signature)

    if version_str is not None:
        click.echo("Skipping Merkle root update because of explicit version.")
    elif update_merkle_root(signature_file, root):
        SIGNATURES_JSON.write_text(json.dumps(signature_file, indent=2) + "\n")
        click.echo("Updated signatures.json")
    else:
        click.echo("signatures.json is already up-to-date")


@cli.command()
@click.option(
    "--version", "version_str", help="Set the blob version independent of JSON data."
)
def merkle_root(version_str: str | None) -> None:
    """Print the Merkle root of all language blobs."""
    if version_str is None:
        version = None
    else:
        version = translations.version_from_json(version_str)

    tdir = TranslationsDir()
    all_blobs = tdir.generate_all_blobs(version)
    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()

    if version_str is not None:
        # short-circuit: just print the Merkle root
        click.echo(root.hex())
        return

    # we are using in-tree version. check in-tree merkle root
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
@click.argument("signature_hex")
@click.option("--force", is_flag=True, help="Write even if the signature is invalid.")
@click.option(
    "--version", "version_str", help="Set the blob version independent of JSON data."
)
def sign(signature_hex: str, force: bool | None, version_str: str | None) -> None:
    """Insert a signature into language blobs."""
    if version_str is None:
        version = None
    else:
        version = translations.version_from_json(version_str)

    tdir = TranslationsDir()
    all_blobs = tdir.generate_all_blobs(version)
    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()

    blob_version = all_blobs[0].header.firmware_version
    signature_file: SignatureFile = json.loads(SIGNATURES_JSON.read_text())

    if version_str is None:
        # we are using in-tree version. check in-tree merkle root
        if signature_file["current"]["merkle_root"] != root.hex():
            raise click.ClickException(
                f"Merkle root mismatch!\n"
                f"Expected:                  {root.hex()}\n"
                f"Stored in signatures.json: {signature_file['current']['merkle_root']}"
            )
    # else, proceed with the calculated Merkle root

    # Update signature file data. It will be written only if the signature verifies.
    tree_info = make_tree_info(root)
    signed_info = sign_info(tree_info, bytes.fromhex(signature_hex), blob_version)
    signature_file["history"].insert(0, signed_info)

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
