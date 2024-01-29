from __future__ import annotations

import typing as t
from pathlib import Path

import click

from trezorlib import cosi, models, merkle_tree
from trezorlib._internal import translations

HERE = Path(__file__).parent.resolve()

ALL_MODELS = {models.T2B1, models.T2T1}

PRIVATE_KEYS_DEV = [byte * 32 for byte in (b"\xdd", b"\xde", b"\xdf")]


def _sign_with_privkeys(digest: bytes, privkeys: t.Sequence[bytes]) -> bytes:
    """Locally produce a CoSi signature."""
    pubkeys = [cosi.pubkey_from_privkey(sk) for sk in privkeys]
    nonces = [cosi.get_nonce(sk, digest, i) for i, sk in enumerate(privkeys)]

    global_pk = cosi.combine_keys(pubkeys)
    global_R = cosi.combine_keys(R for _, R in nonces)

    sigs = [
        cosi.sign_with_privkey(digest, sk, global_pk, r, global_R)
        for sk, (r, _) in zip(privkeys, nonces)
    ]

    return cosi.combine_sig(global_R, sigs)


@click.command()
def main() -> None:
    all_languages = [lang_file.stem for lang_file in HERE.glob("??.json")]
    all_blobs = []
    for lang in all_languages:
        if lang == "en":
            continue

        for model in ALL_MODELS:
            try:
                blob = translations.blob_from_dir(HERE, lang, model)
                all_blobs.append(blob)
            except Exception as e:
                import traceback

                traceback.print_exc()
                click.echo(f"Failed to build {lang} for {model.internal_name}: {e}")
                continue
            click.echo(f"Built {lang} for {model.internal_name}")

    tree = merkle_tree.MerkleTree(b.header_bytes for b in all_blobs)
    root = tree.get_root_hash()
    signature = _sign_with_privkeys(root, PRIVATE_KEYS_DEV)
    sigmask = 0b111

    for blob in all_blobs:
        proof = translations.Proof(
            merkle_proof=tree.get_proof(blob.header_bytes),
            signature=signature,
            sigmask=sigmask,
        )
        blob.proof = proof
        header = blob.header
        model_str = header.model.value.decode("ascii")
        version_str = ".".join(str(v) for v in header.firmware_version[:3])
        filename = f"translation-{model_str}-{header.language}-{version_str}.bin"
        click.echo(f"Writing {header.language} for {model_str} v{version_str}: {filename}")
        (HERE / filename).write_bytes(blob.build())

if __name__ == "__main__":
    main()
