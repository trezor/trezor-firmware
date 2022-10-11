"""
Translate bytecode instructions in frozen_mpy.c to human readable form.
"""

from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).parent
CORE_DIR = HERE.parent

FROZEN_MPY_FILE = CORE_DIR / "build/firmware/frozen_mpy.c"
NEW_FILE = str(FROZEN_MPY_FILE) + "_translated"

# Taken from core/vendor/micropython/py/bc0.h
OPCODES: dict[str, str] = {
    "0x10": "LOAD QSTR const",
    "0x11": "LOAD QSTR name",
    "0x12": "LOAD QSTR global",
    "0x13": "LOAD QSTR attribute",
    "0x14": "LOAD QSTR method",
    "0x15": "LOAD QSTR super method",
    "0x16": "STORE QSTR name",
    "0x17": "STORE QSTR global",
    "0x18": "STORE QSTR attribute",
    "0x19": "DELETE QSTR name",
    "0x1a": "DELETE QSTR global",
    "0x1b": "IMPORT QSTR name",
    "0x1c": "IMPORT QSTR from",
    "0x20": "MAKE closure",
    "0x21": "MAKE closure defargs",
    "0x22": "LOAD small int",
    "0x23": "LOAD obj ptr",
    "0x24": "LOAD fast N uint",
    "0x25": "LOAD deref uint",
    "0x26": "STORE fast N uint",
    "0x27": "STORE deref uint",
    "0x28": "DELETE fast N uint",
    "0x29": "DELETE deref uint",
    "0x2a": "BUILD tuple",
    "0x2b": "BUILD list",
    "0x2c": "BUILD map",
    "0x2d": "BUILD set",
    "0x2e": "BUILD slice",
    "0x2f": "STORE comp",
    "0x30": "UNPACK sequence",
    "0x31": "UNPACK ex",
    "0x32": "MAKE function",
    "0x33": "MAKE function defargs",
    "0x34": "CALL function",
    "0x35": "CALL function var kw",
    "0x36": "CALL method",
    "0x37": "CALL method var kw",
    "0x40": "JUMP unwind",
    "0x42": "JUMP",
    "0x43": "JUMP pop if true",
    "0x44": "JUMP pop if false",
    "0x45": "JUMP if true or pop",
    "0x46": "JUMP if false or pop",
    "0x47": "SETUP with",
    "0x48": "SETUP except",
    "0x49": "SETUP finally",
    "0x4a": "POP block",
    "0x50": "LOAD False",
    "0x51": "LOAD None",
    "0x52": "LOAD True",
    "0x53": "LOAD null",
    "0x54": "LOAD build class",
    "0x55": "LOAD subscript",
    "0x56": "STORE subscript",
    "0x57": "DUP top",
    "0x58": "DUP top two",
    "0x59": "POP top",
    "0x5a": "ROT two",
    "0x5b": "ROT three",
    "0x5c": "WITH cleanup",
    "0x5d": "END finally",
    "0x5e": "GET iter",
    "0x5f": "GET iter stack",
    "0x62": "STORE map",
    "0x63": "RETURN value",
    "0x64": "RAISE last",
    "0x65": "RAISE obj",
    "0x66": "RAISE from",
    "0x67": "YIELD value",
    "0x68": "YIELD from (AWAIT)",
    "0x69": "IMPORT star",
    "0xd7": "<",
    "0xd8": ">",
    "0xd9": "==",
    "0xda": "<=",
    "0xdb": ">=",
    "0xdc": "!=",
    "0xde": "is",
    "0xef": "&",
    "0xf0": "<<",
}


def main() -> None:
    with open(FROZEN_MPY_FILE, "r") as f:
        lines = f.readlines()

    new_lines: list[str] = []
    for line in lines:
        first_byte = line.strip().split(",")[0]

        # Check if it is a byte, otherwise skip
        try:
            num = int(first_byte, 16)
        except ValueError:
            new_lines.append(line)
            continue

        # Some OP codes have a value in themselves
        if 0x70 <= num <= 0xAF:
            # Small int
            var = num - 0x10 - 0x70
            val = f"INT {var}"
            line = line.replace(first_byte, val, 1)
        elif 0xB0 <= num <= 0xBF:
            # Local variable loading
            var = num - 0xB0
            val = f"LOAD local {var}"
            line = line.replace(first_byte, val, 1)
        elif 0xC0 <= num <= 0xCF:
            # Local variable storing
            var = num - 0xC0
            val = f"STORE local {var}"
            line = line.replace(first_byte, val, 1)
        else:
            # Hardcoded OPcodes
            if first_byte in OPCODES:
                line = line.replace(first_byte, OPCODES[first_byte], 1)
            else:
                pass
                # print(f"Unknown opcode: {first_byte}")

        new_lines.append(line)

    with open(NEW_FILE, "w") as f:
        f.write("".join(new_lines))

    print(f"Translated file saved as {NEW_FILE}")


if __name__ == "__main__":
    main()
