# /// script
# requires-python = ">=3.11"
# dependencies = ["unicorn>=2.1,<3"]
# ///
"""Execute the linked ARM stack scrubber: uv run --script THIS kernel.elf."""

import re
import subprocess
import sys
from pathlib import Path

from unicorn import UC_ARCH_ARM, UC_MODE_MCLASS, UC_MODE_THUMB, Uc
from unicorn.arm_const import (
    UC_ARM_REG_CONTROL,
    UC_ARM_REG_LR,
    UC_ARM_REG_PRIMASK,
    UC_ARM_REG_R4,
    UC_ARM_REG_R5,
    UC_ARM_REG_R6,
    UC_ARM_REG_R7,
    UC_ARM_REG_R8,
    UC_ARM_REG_R9,
    UC_ARM_REG_R10,
    UC_ARM_REG_R11,
    UC_ARM_REG_SP,
)


def main():
    elf = Path(sys.argv[1])
    names = subprocess.check_output(["arm-none-eabi-nm", "-n", str(elf)], text=True)
    symbols = {
        parts[2]: int(parts[0], 16)
        for line in names.splitlines()
        if len(parts := line.split()) == 3 and re.fullmatch("[0-9a-fA-F]+", parts[0])
    }
    start, end = symbols["_stack_section_start"], symbols["_stack_section_end"]
    function = symbols["clear_unused_stack"] & ~1
    sections = subprocess.check_output(
        ["arm-none-eabi-objdump", "-h", str(elf)], text=True
    )
    for line in sections.splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[0].isdigit():
            size, address = int(parts[2], 16), int(parts[3], 16)
            if address <= function < address + size:
                break
    else:
        raise AssertionError("Scrubber code section not found")
    # Combined images can contain two sections named .flash. Read by file
    # offset so objcopy cannot silently select the other section.
    offset = int(parts[5], 16)
    code = elf.read_bytes()[offset : offset + size]
    registers = (
        UC_ARM_REG_R4,
        UC_ARM_REG_R5,
        UC_ARM_REG_R6,
        UC_ARM_REG_R7,
        UC_ARM_REG_R8,
        UC_ARM_REG_R9,
        UC_ARM_REG_R10,
        UC_ARM_REG_R11,
    )
    sentinel = 0x01000000
    ram_start, ram_end = (start - 4096) & ~4095, (end + 8191) & ~4095
    for control in (0, 2):  # Privileged thread, MSP and PSP.
        for mask in (0, 1):
            for sp in (
                start - 16,
                start,
                start + 16,
                (start + end) // 2,
                end,
                end + 16,
            ):
                uc = Uc(UC_ARCH_ARM, UC_MODE_THUMB | UC_MODE_MCLASS)
                code_base = address & ~4095
                uc.mem_map(code_base, (address - code_base + len(code) + 4095) & ~4095)
                uc.mem_write(address, code)
                uc.mem_map(sentinel, 4096)
                uc.mem_map(ram_start, ram_end - ram_start)
                before = bytes([0x5A]) * (ram_end - ram_start)
                uc.mem_write(ram_start, before)
                uc.reg_write(UC_ARM_REG_CONTROL, control)
                uc.reg_write(UC_ARM_REG_SP, sp)
                uc.reg_write(UC_ARM_REG_LR, sentinel | 1)
                uc.reg_write(UC_ARM_REG_PRIMASK, mask)
                for index, register in enumerate(registers):
                    uc.reg_write(register, 0x12340000 + index)
                uc.emu_start(function | 1, sentinel, count=1000000)
                expected = bytearray(before)
                if start <= sp <= end:
                    expected[start - ram_start : sp - ram_start] = bytes(sp - start)
                assert uc.mem_read(ram_start, ram_end - ram_start) == expected, (
                    control,
                    mask,
                    sp,
                )
                assert uc.reg_read(UC_ARM_REG_SP) == sp
                assert uc.reg_read(UC_ARM_REG_PRIMASK) == mask
                for index, register in enumerate(registers):
                    assert uc.reg_read(register) == 0x12340000 + index
    print("ARM stack scrub: bounds, live frames, MSP/PSP and PRIMASK checks passed")


if __name__ == "__main__":
    main()
