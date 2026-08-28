#!/usr/bin/env python3
"""Host side of the consent-digest cross-validation.

Reads the vector consent_test dumped straight out of the REAL device code and
checks that trezor_core_tools' preamble builder -- the thing that will actually
put bytes on the wire -- derives the same auth/proof boundary and the same digest.
A disagreement here means a host would ask the user to confirm one release and the
device would compute a different digest for it, so every interaction-less upgrade
would be refused.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))

from trezor_core_tools.firmware_pq_update import (  # noqa: E402
    boot_header_prefix,
    consent_preamble,
)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <vector-dir>", file=sys.stderr)
        return 2
    d = Path(sys.argv[1])
    header = (d / "header.bin").read_bytes()
    manifest = (d / "manifest.bin").read_bytes()
    want = (d / "digest.bin").read_bytes()

    fails = 0

    def ck(what: str, ok: bool) -> None:
        nonlocal fails
        print(f"  {what:<56} {'ok' if ok else 'FAIL'}")
        if not ok:
            fails += 1

    prefix = boot_header_prefix(header)
    # The device stops the digest at auth_size + proof; anything the host includes
    # beyond that (signatures, the rewritten firmware_type) would diverge.
    auth_size = int.from_bytes(header[32:36], "little")
    node_count = int.from_bytes(header[auth_size : auth_size + 4], "little")
    ck(
        "host boundary == auth_size + 4 + 32*node_count",
        len(prefix) == auth_size + 4 + node_count * 32,
    )
    ck("host prefix is a prefix of the device's header", header.startswith(prefix))
    ck("host prefix excludes the signatures", len(prefix) < len(header))

    got = hashlib.sha256(consent_preamble(header, manifest)).digest()
    ck("HOST DIGEST == DEVICE DIGEST", got == want)
    if got != want:
        print(f"    device: {want.hex()}\n    host:   {got.hex()}")

    # The preamble the host puts on the wire must be exactly the preimage.
    ck(
        "preamble == prefix || manifest",
        consent_preamble(header, manifest) == prefix + manifest,
    )

    print(
        f"\n  {'FAILED' if fails else 'HOST MATCHES DEVICE'} "
        f"({fails} failure{'' if fails == 1 else 's'})"
    )
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
