#!/usr/bin/env python3
"""Report which founder key pool a bootloader binary trusts, and its code digest.

The pool a bootloader verifies incoming boot headers against is a COMPILE-TIME
choice (`BOOTLOADER_DEVEL` in sec/image/boot_header.c) and leaves no trace in
the boot header. A release therefore cannot tell from the header whether the
code it is about to fold trusts production keys or the development ones whose
private halves are in this repository -- but the linked public keys are in the
binary, so the artifact can be asked directly.

Reads the keys from trezorlib rather than re-listing them: root_keys_check.py
already proves that copy agrees with the STM header and the nRF's, so there is
no fourth copy to drift.

Also prints SHA-256 over the bootloader CODE -- the extent the signed leaf
commits to, taken from the header's own `code_size`. That digest is what a
ceremony can pin: it is stable across re-signing, whereas the file's digest
changes the moment the header is rewritten.

Output is two `key=value` lines on stdout:

    pool=production|devel|mixed|unknown
    code_sha256=<hex>
"""

from __future__ import annotations

import hashlib
import struct
import sys
from pathlib import Path

from trezorlib.firmware.models import (
    ROOT_ED25519_KEYS,
    ROOT_ED25519_KEYS_DEV,
    ROOT_SLH_DSA_KEYS,
    ROOT_SLH_DSA_KEYS_DEV_PUBLIC,
)

# Offsets into boot_header_auth_t (sec/image/inc/sec/boot_header.h). Only the
# two sizes are needed, and both sit before any field that has ever moved.
_HEADER_SIZE_OFF = 28
_CODE_SIZE_OFF = 36
_MAGIC = b"TRZQ"


def code_digest(image: bytes) -> str:
    """SHA-256 over exactly the bytes the signed leaf commits to."""
    if image[:4] != _MAGIC:
        raise SystemExit(f"not a boot header: magic {image[:4]!r}, want {_MAGIC!r}")
    (header_size,) = struct.unpack_from("<I", image, _HEADER_SIZE_OFF)
    (code_size,) = struct.unpack_from("<I", image, _CODE_SIZE_OFF)
    end = header_size + code_size
    if end > len(image):
        raise SystemExit(
            f"header claims {header_size}+{code_size} bytes but the file holds "
            f"{len(image)}"
        )
    return hashlib.sha256(image[header_size:end]).hexdigest()


def detect_pool(image: bytes) -> str:
    """Which founder pool is linked into this binary.

    Presence is decisive in one direction only: an unreferenced key array is not
    emitted, so the pool the build selected is the one that appears. "unknown"
    means neither was found -- a bootloader old enough to predate founder
    verification, or one that does not link boot_header.c at all.
    """
    prod = [bytes(k) for k in (*ROOT_SLH_DSA_KEYS, *ROOT_ED25519_KEYS)]
    devel = [
        bytes(k) for k in (*ROOT_SLH_DSA_KEYS_DEV_PUBLIC, *ROOT_ED25519_KEYS_DEV)
    ]
    has_prod = any(k in image for k in prod)
    has_devel = any(k in image for k in devel)
    if has_prod and has_devel:
        return "mixed"  # should be impossible; report rather than pick a side
    if has_prod:
        return "production"
    if has_devel:
        return "devel"
    return "unknown"


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} <bootloader.bin>")
    image = Path(sys.argv[1]).read_bytes()
    print(f"pool={detect_pool(image)}")
    print(f"code_sha256={code_digest(image)}")


if __name__ == "__main__":
    main()
