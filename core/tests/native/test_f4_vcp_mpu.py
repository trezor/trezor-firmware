# /// script
# requires-python = ">=3.11"
# dependencies = ["unicorn>=2.1,<3"]
# ///
"""Execute the linked F4 MPU setup and check VCP/CCM access policy."""

import re
import subprocess
import sys
from pathlib import Path

from unicorn import UC_ARCH_ARM, UC_HOOK_MEM_WRITE, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_SP


def symbols(path):
    output = subprocess.check_output(
        ["arm-none-eabi-nm", "--defined-only", str(path)], text=True
    )
    return {
        parts[-1]: int(parts[0], 16)
        for line in output.splitlines()
        if len(parts := line.split()) >= 3
    }


def main():
    kernel, app = map(Path, sys.argv[1:3])
    names, app_names = symbols(kernel), symbols(app)
    uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
    pages = set()

    def map_range(address, size):
        for page in range(address & ~4095, (address + size + 4095) & ~4095, 4096):
            if page not in pages:
                uc.mem_map(page, 4096)
                pages.add(page)

    output = subprocess.check_output(
        ["arm-none-eabi-objdump", "-h", str(kernel)], text=True
    )
    lines, image = output.splitlines(), kernel.read_bytes()
    for index, line in enumerate(lines):
        parts = line.split()
        if len(parts) < 7 or not parts[0].isdigit():
            continue
        size, address, offset = (int(parts[i], 16) for i in (2, 3, 5))
        if size and "ALLOC" in lines[index + 1]:
            map_range(address, size)
            if "CONTENTS" in lines[index + 1]:
                uc.mem_write(address, image[offset : offset + size])
    map_range(0xE000E000, 8192)
    stop = 0x01000000
    map_range(stop, 4096)
    regions, selected = {}, [0]

    def write(_uc, _access, address, _size, value, _data):
        if address == 0xE000ED98:
            selected[0] = value
        elif address in (0xE000ED9C, 0xE000EDA0):
            region = regions.setdefault(selected[0], [0, 0])
            region[address == 0xE000EDA0] = value

    uc.hook_add(UC_HOOK_MEM_WRITE, write)

    def call(name, value=0):
        uc.reg_write(UC_ARM_REG_SP, names["_stack_section_end"])
        uc.reg_write(UC_ARM_REG_LR, stop | 1)
        uc.reg_write(UC_ARM_REG_R0, value)
        uc.emu_start(names[name] | 1, stop, count=100000)

    call("mpu_init")
    header = Path(__file__).resolve().parents[2] / "embed/sys/mpu/inc/sys/mpu.h"
    modes = re.findall(r"^\s+(MPU_MODE_\w+),", header.read_text(), re.M)
    call("mpu_reconfig", modes.index("MPU_MODE_APP"))

    def access(address):
        result = None
        for _, (base, attributes) in sorted(regions.items()):
            if not attributes & 1:
                continue
            size = 1 << (((attributes >> 1) & 31) + 1)
            offset = address - (base & ~(size - 1))
            if 0 <= offset < size:
                if size >= 256 and attributes & (1 << (8 + offset * 8 // size)):
                    continue
                result = ((attributes >> 24) & 7, bool(attributes & (1 << 28)))
        return result

    for address in (0x20000000, 0x20001FFF):
        assert access(address) == (1, True), f"I/O is not privileged NX: {address:#x}"
    for name in (
        "secret_scratch",
        "secret_owners",
        "vault_large_message",
        "g_usb_driver",
    ):
        assert access(names[name]) == (1, True), f"private CCM exposed: {name}"
    if "--optiga" in sys.argv[3:]:
        address = names["tx_buffer"]
        assert 0x20000000 <= address < 0x20002000, "Optiga payload outside I/O"
        assert access(address) == (1, True), "Optiga payload exposed"
    stack = app_names["_stack_section_start"]
    assert stack >= 0x20002000, "application overlaps I/O reservation"
    assert access(stack) == (3, True), "application SRAM is inaccessible"
    assert access(0x40000000) == (1, True), "peripheral privilege policy changed"
    print(
        "F4 linked MPU setup: 8 KiB I/O and vault CCM privileged; app SRAM accessible"
    )


if __name__ == "__main__":
    main()
