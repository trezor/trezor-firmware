#!/usr/bin/env python3

import typing as t
from hashlib import sha256
from pathlib import Path

import click
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    Prehashed,
    decode_dss_signature,
)

from trezorlib.firmware.legacy import LegacyV2Firmware
from trezorlib.firmware.models import LEGACY_V3_DEV

SECRET_KEYS = [
    ec.derive_private_key(
        int.from_bytes(bytes.fromhex(sk), "big"), ec.SECP256K1()
    )
    for sk in (
        "ca8de06e1e93d101136fa6fbc41432c52b6530299dfe32808030ee8e679702f1",
        "dde47dd393f7d76f9b522bfa9760bc4543d2c3654491393774f54e066461fccb",
        "14ba98c5c5cb8f1b214c661f4046ec2288c34fe2e73e02f149ec3dd8dad07ae2",
    )
]

PUBLIC_KEYS = [sk.public_key() for sk in SECRET_KEYS]

# Should be these public keys
assert [
    pk.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.CompressedPoint,
    )
    for pk in PUBLIC_KEYS
] == LEGACY_V3_DEV.firmware_keys


def signmessage(digest: bytes, key: ec.EllipticCurvePrivateKey) -> bytes:
    """Sign via SignMessage"""
    btc_digest = b"\x18Bitcoin Signed Message:\n\x20" + digest
    final_digest = sha256(sha256(btc_digest).digest()).digest()
    der_sig = key.sign(final_digest, ec.ECDSA(Prehashed(hashes.SHA256())))
    r, s = decode_dss_signature(der_sig)
    return r.to_bytes(32, "big") + s.to_bytes(32, "big")


@click.command()
@click.argument("firmware", type=click.File("rb"))
@click.option("-i", "--index", "indices", type=int, multiple=True)
def cli(firmware: click.utils.LazyFile, indices: t.Sequence[int]) -> None:
    fw = LegacyV2Firmware.parse(firmware.read())
    if not indices:
        indices = [1, 2]

    if len(indices) > 3:
        raise click.ClickException("Too many indices")

    digest = fw.digest()
    for i, idx in enumerate(indices):
        sk = SECRET_KEYS[idx - 1]
        sig = signmessage(digest, sk)

        fw.header.v1_key_indexes[i] = idx
        fw.header.v1_signatures[i] = sig

    new_fw = Path(firmware.name).with_suffix(".signed.bin")
    new_fw.write_bytes(fw.build())
    click.echo(f"Wrote signed firmware to {new_fw}")


if __name__ == "__main__":
    cli()
