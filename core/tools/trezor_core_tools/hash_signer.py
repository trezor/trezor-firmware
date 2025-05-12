#!/usr/bin/env python3
import click

from trezorlib import cosi, firmware
from trezorlib._internal import firmware_headers

from typing import List, Sequence, Tuple

# =========================== signing =========================


def _make_dev_keys(*key_bytes: bytes) -> Sequence[bytes]:
    return [k * 32 for k in key_bytes]


@click.command()
@click.option(
    "-d",
    "--digest",
    "digest",
    help="Digest to be signed.",
)
def main(
    digest
):

    DEV_KEYS = _make_dev_keys(b"\x44", b"\x45")

    privkeys = DEV_KEYS
    sigmask = (1 << len(privkeys)) - 1

    print("Signing with local private keys...")

    print(bytes.fromhex(digest))

    signature = cosi.sign_with_privkeys(bytes.fromhex(digest), privkeys)

    print(f'SIG: 0x{signature.hex()}')
    print(f"SIGMASK: {sigmask:#06x}")


if __name__ == "__main__":
    main()
