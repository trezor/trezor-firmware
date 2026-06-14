#!/usr/bin/env python3
"""Cross-check the Trezor apps/darkfi firmware against the darkfi-sdk oracle.

Drives a Trezor (emulator over UDP, or a physical device over USB) through the
three DarkFi messages and asserts every returned field matches what
`drk-hww-oracle` computes from the *same* BIP-39 mnemonic and account index:

    DarkfiGetFullViewingKey  ->  ak, nk
    DarkfiGetAddress         ->  pk_d
    DarkfiSignSpendAuth      ->  commit, rk, response

The device and the oracle must be driven with the *same* mnemonic.

  * --emulator wipes the (emulator) device and loads the mnemonic for you.
  * For a physical device, restore the test mnemonic onto it first, then run
    without --emulator. Button/PIN prompts are auto-confirmed via DebugLink.

Usage:

    python darkfi_oracle_check.py --emulator \
        --oracle /path/to/drk-hww-oracle \
        --mnemonic "all all all all all all all all all all all all"

    TREZOR_PATH=... python darkfi_oracle_check.py \
        --oracle /path/to/drk-hww-oracle \
        --mnemonic "all all all all all all all all all all all all"

Exit code 0 = all fields matched.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

from trezorlib import debuglink, messages
from trezorlib.debuglink import TrezorTestContext
from trezorlib.transport import enumerate_devices, get_transport


# Fixed account index and signing inputs for the check. alpha must be a
# canonical little-endian Pallas base-field element (high byte 0 keeps it < p).
ACCOUNT = 0
ALPHA_HEX = "03080d12171c21262b30353a3f44494e53585d62676c71767b80858a8f949900"
SIGHASH_HEX = "1122334455667788990011223344556677889900112233445566778899001122"


def _parse(text: str) -> dict[str, str]:
    d = {}
    for line in text.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def oracle_keys(oracle: str, mnemonic: str, account: int) -> dict[str, str]:
    out = subprocess.run(
        [oracle, "keys", "--mnemonic", mnemonic, "--account", str(account)],
        check=True, capture_output=True, text=True,
    ).stdout
    return _parse(out)


def oracle_sign(oracle: str, mnemonic: str, account: int, alpha: str, sighash: str) -> dict[str, str]:
    out = subprocess.run(
        [oracle, "sign", "--mnemonic", mnemonic, "--account", str(account),
         "--alpha", alpha, "--sighash", sighash],
        check=True, capture_output=True, text=True,
    ).stdout
    return _parse(out)


def make_context(args) -> TrezorTestContext:
    if args.emulator:
        transport = get_transport("udp:127.0.0.1:21324")
        return TrezorTestContext(transport, auto_interact=True, force_wipe=True)

    path = args.path or os.environ.get("TREZOR_PATH")
    if path:
        transport = get_transport(path)
    else:
        devices = enumerate_devices()
        if not devices:
            raise RuntimeError("No Trezor device found")
        transport = devices[0]
    return TrezorTestContext(transport, auto_interact=True, force_wipe=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--oracle", required=True, help="path to drk-hww-oracle binary")
    ap.add_argument("--mnemonic", required=True, help="BIP-39 mnemonic (same on device + oracle)")
    ap.add_argument("--emulator", action="store_true", help="target emulator over UDP, auto-load mnemonic")
    ap.add_argument("--path", default=None, help="explicit transport path for a physical device")
    args = ap.parse_args()

    exp_keys = oracle_keys(args.oracle, args.mnemonic, ACCOUNT)
    exp_sign = oracle_sign(args.oracle, args.mnemonic, ACCOUNT, ALPHA_HEX, SIGHASH_HEX)

    ctx = make_context(args)

    # On the emulator we control the seed: wipe + load the test mnemonic so the
    # device derives the same keys as the oracle.
    if args.emulator:
        if ctx.features.initialized:
            ctx.wipe_device()
        debuglink.load_device(
            ctx.get_seedless_session(),
            mnemonic=args.mnemonic,
            pin=None,
            passphrase_protection=False,
            label="darkfi-test",
        )

    session = ctx.get_session(passphrase=None)

    results: list[tuple[str, str, str]] = []

    fvk = session.call(
        messages.DarkfiGetFullViewingKey(account=ACCOUNT),
        expect=messages.DarkfiFullViewingKey,
    )
    results.append(("ak", exp_keys["ak"], fvk.ak.hex()))
    results.append(("nk", exp_keys["nk"], fvk.nk.hex()))

    addr = session.call(
        messages.DarkfiGetAddress(account=ACCOUNT, show_display=True),
        expect=messages.DarkfiAddress,
    )
    results.append(("pk_d", exp_keys["pk_d"], addr.pk_d.hex()))

    sig = session.call(
        messages.DarkfiSignSpendAuth(
            account=ACCOUNT,
            alpha=bytes.fromhex(ALPHA_HEX),
            sighash=bytes.fromhex(SIGHASH_HEX),
            details=messages.DarkfiSpendDetails(
                value=42,
                token_id=bytes.fromhex(
                    "0807060504030201000f0e0d0c0b0a090807060504030201000f0e0d0c0b0a09"
                ),
                recipient=addr.pk_d,
            ),
        ),
        expect=messages.DarkfiSpendAuthSignature,
    )
    results.append(("commit", exp_sign["commit"], sig.commit.hex()))
    results.append(("rk", exp_sign["rk"], sig.rk.hex()))
    results.append(("response", exp_sign["response"], sig.response.hex()))

    width = max(len(f) for f, *_ in results)
    all_ok = True
    print(f"\n{'field':<{width}}  {'oracle (sdk)':<64}  match")
    print("-" * (width + 64 + 8))
    for field, exp, got in results:
        ok = exp == got
        all_ok &= ok
        print(f"{field:<{width}}  {exp:<64}  {'OK' if ok else 'FAIL'}")
        if not ok:
            print(f"{'device':<{width}}  {got:<64}  <-")

    print()
    if all_ok:
        print("ALL FIELDS MATCH — firmware reproduces the SDK bit-for-bit.")
        return 0
    print("MISMATCH — see FAIL rows above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
