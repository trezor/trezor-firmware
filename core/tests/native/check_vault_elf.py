#!/usr/bin/env python3
"""Check kernel/coreapp placement in the actual embedded ELF pair.

This checks linked symbols, not hardware MPU enforcement or residual stack data.
"""

import argparse
import subprocess


def symbols(nm, path):
    output = subprocess.check_output([nm, "--defined-only", path], text=True)
    return {line.split()[-1] for line in output.splitlines() if line.split()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel")
    parser.add_argument("coreapp")
    parser.add_argument("--secmon", help="secmon ELF on models where it owns storage")
    parser.add_argument("--nm", default="arm-none-eabi-nm")
    args = parser.parse_args()
    kernel = symbols(args.nm, args.kernel)
    coreapp = symbols(args.nm, args.coreapp)
    for name in (
        "secret_owners",
        "secret_scratch",
        "vault_dispatch",
        "vault_dispatch_message",
        "vault_message_snapshot",
        "vault_call_message__verified",
        "vault_wipe",
    ):
        assert name in kernel, f"missing kernel vault symbol: {name}"
        assert name not in coreapp, f"vault symbol leaked into coreapp: {name}"
    # SAES builds (C3) keep no record key or expanded schedule in the kernel;
    # software builds keep the wrapped key and a transient context there.
    if "vault_saes_record" in kernel:
        for name in ("record_ctx", "wrapped_dek"):
            assert name not in kernel, f"software record key in kernel: {name}"
        if args.secmon:
            secmon = symbols(args.nm, args.secmon)
            assert "record_key_wrapped" in secmon, "SAES record key not in secmon"
            assert "record_key_wrapped" not in kernel, "SAES record key in kernel"
    else:
        for name in ("record_ctx", "wrapped_dek"):
            assert name in kernel, f"missing kernel vault symbol: {name}"
    # Sealed blobs replaced the kernel slot table.
    assert "secret_entries" not in kernel, "kernel still has a secret slot table"
    storage = symbols(args.nm, args.secmon) if args.secmon else kernel
    assert "sealed_storage_keys" in storage, "missing sealed storage key cache"
    assert "cached_keys" not in storage, "plaintext storage key cache remains"
    assert "vault_call" in coreapp, "missing coreapp syscall stub"
    assert "vault_call_message" in coreapp, "missing message syscall stub"
    print("vault ELF placement checks passed")


if __name__ == "__main__":
    main()
