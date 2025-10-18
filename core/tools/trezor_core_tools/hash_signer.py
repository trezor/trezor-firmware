#!/usr/bin/env python3
from __future__ import annotations

from typing import Sequence

import click

from trezorlib import _ed25519

# =========================== signing =========================


def _make_dev_keys(*key_bytes: bytes) -> Sequence[bytes]:
    return [k * 32 for k in key_bytes]


@click.command()
@click.option(
    "-d",
    "--digest",
    "digest",
    help="Digest to be signed.",
    required=True,
)
@click.option(
    "-s0",
    "--getsig0",
    "getsig0",
    is_flag=True,
    help="Print out signature 0",
)
@click.option(
    "-s1",
    "--getsig1",
    "getsig1",
    is_flag=True,
    help="Print out signature 1",
)
@click.option(
    "-m",
    "--getmask",
    "getmask",
    is_flag=True,
    help="Print out sigmask",
)
def main(digest: str, getsig0: bool, getsig1: bool, getmask: bool) -> None:

    DEV_KEYS = _make_dev_keys(b"\x44", b"\x45")

    privkeys = DEV_KEYS
    sigmask = (1 << len(privkeys)) - 1

    signatures = [
        _ed25519.signature_unsafe(
            bytes.fromhex(digest), key, _ed25519.publickey_unsafe(key)
        )
        for idx, key in enumerate(DEV_KEYS)
    ]

    if getsig0:
        print(f"0x{signatures[0].hex()}")
    if getsig1:
        print(f"0x{signatures[1].hex()}")
    if getmask:
        print(f"{sigmask:#06x}")


if __name__ == "__main__":
    main()
