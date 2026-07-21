#!/usr/bin/env python3
"""
otfdec_demo.py — Exercise the OTFDEC ext-flash encrypt/execute cycle via prodtest.

The script walks through the full end-to-end cycle:

  1. Erase the target 4 KB sector.
  2. Write known plaintext via ext-flash-otfdec-load (encrypts with OTFDEC1
     encipher mode in secmon, then programs the ciphertext to flash).
  3. Read back via ext-flash-read  (XIP / OTFDEC-decrypted)  → must match plaintext.
  4. Read back via ext-flash-read-raw (indirect SPI, no OTFDEC) → must be ciphertext.
  5. Assert steps 3 and 4 differ, proving the chip stores ciphertext while the
     CPU sees plaintext.
  6. Load a minimal Thumb-2 function (BX LR — immediate return) at a second
     offset and execute it via ext-flash-otfdec-exec.  A clean return proves
     OTFDEC transparently decrypts fetched instructions.

Usage:
    python3 otfdec_demo.py [--device /dev/ttyACM0] [--addr 0x0000]

Prerequisites:
  - Device running prodtest with USE_EXT_FLASH and USE_EXT_FLASH_OTFDEC enabled.
  - OTFDEC1 must have been initialised by secmon on boot (ext_flash_otfdec_init).
  - pyserial installed: pip install pyserial
"""

from __future__ import annotations

import argparse
import re
import shlex
import sys
from typing import Any

import serial

_ANSI_RE = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


# ---------------------------------------------------------------------------
# Prodtest CLI connection
# ---------------------------------------------------------------------------

class ProdtestError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"ERROR {code}: {message}")
        self.code = code
        self.message = message


class Connection:
    """Minimal prodtest serial CLI driver.

    Protocol:
      - Commands sent one ASCII character at a time, terminated with CR.
      - Response lines:
          '#  ...'  trace / informational (may carry hex-dump data)
          'OK [hexdata]'  success, optional payload
          'ERROR code "message"'  failure
    """

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 10.0) -> None:
        self.ser = serial.Serial(port, baudrate, timeout=timeout)

    def _writeline(self, line: str) -> None:
        print(f">>> {line}")
        for ch in line:
            self.ser.write(ch.encode())
        self.ser.write(b"\r")

    def _readline(self) -> str:
        raw = _ANSI_RE.sub("", self.ser.readline().strip().decode(errors="replace"))
        if raw:
            print(f"<<< {raw}")
        return raw

    def command(self, cmd: str, *args: Any) -> tuple[bytes | None, list[str]]:
        """Send a command and collect the response.

        Returns:
            (ok_payload, trace_lines) where ok_payload is the hex-decoded OK
            argument (or None), and trace_lines is a list of '#'-prefixed lines
            with the leading '# ' stripped.

        Raises ProdtestError on an ERROR response.
        """
        parts: list[str] = [cmd]
        for a in args:
            if isinstance(a, (bytes, bytearray)):
                parts.append(a.hex())
            elif isinstance(a, int):
                parts.append(f"0x{a:08X}")
            else:
                parts.append(str(a))
        self._writeline(" ".join(parts))

        trace: list[str] = []
        while True:
            line = self._readline()
            if not line:
                continue
            if line.startswith("ERROR"):
                rest = line[len("ERROR"):].strip()
                tokens = shlex.split(rest) if rest else []
                code = tokens[0] if tokens else "?"
                msg = tokens[1] if len(tokens) > 1 else rest
                raise ProdtestError(code, msg)
            elif line.startswith("OK"):
                payload = line[2:].strip()
                if not payload:
                    return None, trace
                try:
                    return bytes.fromhex(payload), trace
                except ValueError:
                    return payload.encode(), trace
            elif line.startswith("#"):
                trace.append(line[1:].strip())
            # blank or unexpected lines: skip


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_hexdump(trace_lines: list[str]) -> bytes:
    """Reconstruct bytes from prodtest hex-dump trace lines.

    Each line has the form:  XXXXXXXX: AABBCCDD...
    """
    result = bytearray()
    for line in trace_lines:
        if ":" not in line:
            continue
        _, _, hex_part = line.partition(":")
        try:
            result.extend(bytes.fromhex(hex_part.strip()))
        except ValueError:
            pass
    return bytes(result)


def ok(msg: str) -> None:
    print(f"    \033[32mPASS\033[0m  {msg}")


def fail(msg: str) -> None:
    print(f"    \033[31mFAIL\033[0m  {msg}")
    sys.exit(1)


def check(condition: bool, msg: str) -> None:
    if condition:
        ok(msg)
    else:
        fail(msg)


def section(n: int, title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  Step {n}: {title}")
    print(f"{'─' * 60}")


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------

# 64 bytes of sequential plaintext.  Chosen so that:
#   - it is a non-trivial, recognisable pattern
#   - it contains no 0xFF (erased-cell value), so a raw read of 0xFF would
#     indicate the cell was never programmed
#   - length is a multiple of 16 (OTFDEC AES block constraint)
PLAINTEXT = bytes(range(0x00, 0x40))  # 64 bytes: 0x00 0x01 … 0x3F

# Minimal Thumb-2 function: BX LR + NOPs, padded to 16 bytes (one AES block).
#   0x4770 = BX LR  → little-endian in memory: 70 47
#   0xBF00 = NOP    → little-endian in memory: 00 BF
# The function does nothing except return, proving that OTFDEC correctly
# decrypted the instruction bytes so the CPU could execute them.
THUMB_RET = bytes([
    0x70, 0x47,  # BX LR
    0x00, 0xBF,  # NOP
    0x00, 0xBF,  # NOP
    0x00, 0xBF,  # NOP
    0x00, 0xBF,  # NOP
    0x00, 0xBF,  # NOP
    0x00, 0xBF,  # NOP
    0x00, 0xBF,  # NOP  (pad to 16 bytes)
])


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def run_demo(conn: Connection, base_addr: int) -> None:
    if base_addr & 15:
        print("error: --addr must be 16-byte aligned (OTFDEC AES block boundary)",
              file=sys.stderr)
        sys.exit(1)

    sector_addr = base_addr & ~0xFFF  # round down to 4 KB sector
    data_addr = base_addr
    code_addr = base_addr + 0x100   # code 256 B after the data block

    if (code_addr + len(THUMB_RET)) > (sector_addr + 0x1000):
        print("error: code block overflows the erased sector; reduce --addr or increase sector size",
              file=sys.stderr)
        sys.exit(1)

    # ------------------------------------------------------------------
    section(1, f"Erase 4 KB sector at 0x{sector_addr:08X}")
    # ------------------------------------------------------------------
    conn.command("ext-flash-erase", "sector", f"0x{sector_addr:08X}")
    print(f"    Sector 0x{sector_addr:08X}–0x{sector_addr + 0xFFF:08X} erased.")

    # ------------------------------------------------------------------
    section(2, f"OTFDEC-load {len(PLAINTEXT)} B plaintext at 0x{data_addr:08X}")
    # ------------------------------------------------------------------
    print(f"    Plaintext  : {PLAINTEXT.hex()}")
    conn.command("ext-flash-otfdec-load", f"0x{data_addr:08X}", PLAINTEXT)
    print("    Ciphertext written to flash.")

    # ------------------------------------------------------------------
    section(3, "ext-flash-read (XIP / OTFDEC) → expect plaintext")
    # ------------------------------------------------------------------
    _, trace = conn.command("ext-flash-read", f"0x{data_addr:08X}", len(PLAINTEXT))
    xip_bytes = parse_hexdump(trace)
    print(f"    XIP read   : {xip_bytes.hex()}")
    check(len(xip_bytes) == len(PLAINTEXT), f"received {len(xip_bytes)} bytes (expected {len(PLAINTEXT)})")
    check(xip_bytes == PLAINTEXT, "XIP data matches original plaintext")

    # ------------------------------------------------------------------
    section(4, "ext-flash-read-raw (indirect SPI, no OTFDEC) → expect ciphertext")
    # ------------------------------------------------------------------
    _, trace = conn.command("ext-flash-read-raw", f"0x{data_addr:08X}", len(PLAINTEXT))
    raw_bytes = parse_hexdump(trace)
    print(f"    Raw read   : {raw_bytes.hex()}")
    check(len(raw_bytes) == len(PLAINTEXT), f"received {len(raw_bytes)} bytes (expected {len(PLAINTEXT)})")
    check(raw_bytes != PLAINTEXT, "raw (ciphertext) differs from plaintext")
    check(
        any(b != 0xFF for b in raw_bytes),
        "flash cell was actually programmed (at least one non-0xFF byte)",
    )

    # ------------------------------------------------------------------
    section(5, "Summary: data stored vs. data visible through OTFDEC")
    # ------------------------------------------------------------------
    mismatches = sum(a != b for a, b in zip(PLAINTEXT, raw_bytes))
    print(f"    {mismatches}/{len(PLAINTEXT)} bytes differ between plaintext and ciphertext.")
    check(mismatches > 0, "AES-CTR keystream altered the data (OTFDEC active)")

    # ------------------------------------------------------------------
    section(6, f"Load Thumb-2 BX-LR payload at 0x{code_addr:08X} and execute")
    # ------------------------------------------------------------------
    print(f"    Payload    : {THUMB_RET.hex()}  (BX LR + NOPs)")
    conn.command("ext-flash-otfdec-load", f"0x{code_addr:08X}", THUMB_RET)
    print("    Code written.  Calling ext-flash-otfdec-exec ...")
    conn.command("ext-flash-otfdec-exec", f"0x{code_addr:08X}")
    ok("Returned from ext flash — OTFDEC instruction decryption is working")

    # ------------------------------------------------------------------
    print(f"\n{'═' * 60}")
    print("  All steps passed.  OTFDEC encrypt / XIP-decrypt cycle verified.")
    print(f"{'═' * 60}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--device", "-d",
        default="/dev/ttyACM0",
        help="Serial port of the prodtest device (default: /dev/ttyACM0)",
    )
    ap.add_argument(
        "--addr", "-a",
        default="0x0000",
        help="Base flash offset for the demo (16-byte aligned, default: 0x0000)",
    )
    args = ap.parse_args()

    base_addr = int(args.addr, 0)

    print(f"Connecting to {args.device} ...")
    conn = Connection(args.device)

    conn.command("ping")
    print("Device is alive.")

    run_demo(conn, base_addr)


if __name__ == "__main__":
    main()
