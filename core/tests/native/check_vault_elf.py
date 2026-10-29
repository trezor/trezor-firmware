#!/usr/bin/env python3
"""Check kernel/coreapp placement in the actual embedded ELF pair.

This checks linked symbols, not hardware MPU enforcement or residual stack data.
"""

import argparse
import subprocess


def symbols(nm, path):
    output = subprocess.check_output([nm, "--defined-only", path], text=True)
    return {line.split()[-1] for line in output.splitlines() if line.split()}


def check_f4_memory(nm, kernel_path, coreapp_path, require_vcp=False):
    def locations(path):
        result = {}
        output = subprocess.check_output(
            [nm, "--defined-only", "--print-size", path], text=True
        )
        for line in output.splitlines():
            parts = line.split()
            if len(parts) == 4:
                result[parts[3]] = (int(parts[0], 16), int(parts[1], 16))
        return result

    kernel = locations(kernel_path)
    if not 0x10000000 <= kernel["secret_scratch"][0] < 0x10010000:
        return
    for name in (
        "secret_owners",
        "secret_scratch",
        "vault_large_message",
        "g_usb_driver",
    ):
        address, size = kernel[name]
        assert 0x1000C000 <= address < address + size <= 0x1000FF00, name
    rings = [
        (name, address, size)
        for name, (address, size) in kernel.items()
        if name.startswith(("vcp_tx_buffer.", "vcp_rx_buffer."))
    ]
    if rings or require_vcp:
        assert len(rings) == 2, rings
        for name, address, size in rings:
            assert size == 2048, f"VCP capacity changed: {name}"
            assert 0x20000000 <= address < address + size <= 0x20002000, name
        ordered = sorted((address, size) for _, address, size in rings)
        assert ordered[0][0] + ordered[0][1] <= ordered[1][0], rings
        # The app stack begins its SRAM allocation, before data and heap.
        output = subprocess.check_output(
            [nm, "--defined-only", coreapp_path], text=True
        )
        stack = next(
            int(line.split()[0], 16)
            for line in output.splitlines()
            if line.split()[-1] == "_stack_section_start"
        )
        assert stack >= 0x20002000, "coreapp overlaps VCP rings"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel")
    parser.add_argument("coreapp")
    parser.add_argument("--nm", default="arm-none-eabi-nm")
    parser.add_argument("--vcp", action="store_true", help="require F4 VCP ring checks")
    args = parser.parse_args()
    check_f4_memory(args.nm, args.kernel, args.coreapp, args.vcp)
    kernel = symbols(args.nm, args.kernel)
    coreapp = symbols(args.nm, args.coreapp)
    for name in (
        "secret_owners",
        "secret_scratch",
        "record_ctx",
        "wrapped_dek",
        "vault_dispatch",
        "vault_dispatch_message",
        "vault_message_snapshot",
        "vault_call_message__verified",
        "vault_wipe",
    ):
        assert name in kernel, f"missing kernel vault symbol: {name}"
        assert name not in coreapp, f"vault symbol leaked into coreapp: {name}"
    # Sealed blobs replaced the kernel slot table.
    assert "secret_entries" not in kernel, "kernel still has a secret slot table"
    assert "vault_call" in coreapp, "missing coreapp syscall stub"
    assert "vault_call_message" in coreapp, "missing message syscall stub"
    print("vault ELF placement checks passed")


if __name__ == "__main__":
    main()
