#!/usr/bin/env python3
"""Convert an image to prodtest `display-image` commands.

The output commands can be pasted directly into the prodtest CLI.

Example:
  python core/tools/display_image_converter.py image.png --width 240 --height 320 > upload.txt
"""

from __future__ import annotations

import argparse
import errno
import os
import sys
import time
from pathlib import Path


try:
    from PIL import Image
except ImportError:
    print(
        "Missing dependency: Pillow. Install it with `pip install Pillow`.",
        file=sys.stderr,
    )
    sys.exit(2)


def rgb888_to_rgb565_le_bytes(r: int, g: int, b: int) -> bytes:
    r5 = (r * 31) // 255
    g6 = (g * 63) // 255
    b5 = (b * 31) // 255
    value = (r5 << 11) | (g6 << 5) | b5
    # Display command expects raw bytes; MCU is little-endian.
    return bytes((value & 0xFF, (value >> 8) & 0xFF))


def image_to_rgb565_le(path: Path, width: int, height: int) -> bytes:
    img = Image.open(path).convert("RGB")
    if img.size != (width, height):
        img = img.resize((width, height), Image.Resampling.LANCZOS)

    out = bytearray(width * height * 2)
    pos = 0
    rgb_bytes = img.tobytes()
    for i in range(0, len(rgb_bytes), 3):
        r = rgb_bytes[i]
        g = rgb_bytes[i + 1]
        b = rgb_bytes[i + 2]
        px = rgb888_to_rgb565_le_bytes(r, g, b)
        out[pos] = px[0]
        out[pos + 1] = px[1]
        pos += 2
    return bytes(out)


def emit_commands(raw: bytes, chunk_bytes: int) -> str:
    lines = ["display-image begin"]
    for i in range(0, len(raw), chunk_bytes):
        chunk = raw[i : i + chunk_bytes]
        lines.append(f"display-image chunk {chunk.hex()}")
    lines.append("display-image end")
    return "\n".join(lines) + "\n"


def emit_c_header(raw: bytes, width: int, height: int, symbol: str) -> str:
    if not symbol.replace("_", "a").isalnum() or symbol[0].isdigit():
        raise ValueError("Invalid C symbol name")

    guard = f"{symbol.upper()}_H"
    lines = [
        f"#ifndef {guard}",
        f"#define {guard}",
        "",
        "#include <stdint.h>",
        "",
        f"#define {symbol}_WIDTH {width}",
        f"#define {symbol}_HEIGHT {height}",
        f"#define {symbol}_SIZE {len(raw)}",
        "",
        f"static const uint8_t {symbol}[{len(raw)}] = {{",
    ]

    hex_bytes = [f"0x{b:02X}" for b in raw]
    for i in range(0, len(hex_bytes), 16):
        lines.append("    " + ", ".join(hex_bytes[i : i + 16]) + ",")

    lines.extend([
        "};",
        "",
        f"#endif  // {guard}",
        "",
    ])
    return "\n".join(lines)


def send_commands_to_tty(commands: str, tty_path: Path, line_delay_ms: int) -> None:
    lines = commands.splitlines()
    delay_s = line_delay_ms / 1000.0

    try:
        fd = os.open(str(tty_path), os.O_RDWR | os.O_NOCTTY)
    except OSError as exc:
        raise RuntimeError(
            f"Cannot open {tty_path}: {exc}. "
            "If tio is connected, close it first or use --output and paste manually."
        ) from exc

    try:
        for line in lines:
            payload = line.encode("ascii") + b"\n"
            try:
                os.write(fd, payload)
            except OSError as exc:
                if exc.errno in (errno.EIO, errno.EBUSY, errno.EACCES):
                    raise RuntimeError(
                        f"Write to {tty_path} failed: {exc}. "
                        "The tty is likely owned by another process (e.g. tio). "
                        "Use --output and paste commands in the active tio session."
                    ) from exc
                raise
            if delay_s > 0:
                time.sleep(delay_s)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path, help="Input image path")
    parser.add_argument("--width", type=int, required=True, help="Target width in pixels")
    parser.add_argument("--height", type=int, required=True, help="Target height in pixels")
    parser.add_argument(
        "--chunk-bytes",
        type=int,
        default=512,
        help="Raw byte count per display-image chunk (default: 512)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output file for generated commands",
    )
    parser.add_argument(
        "--output-c",
        type=Path,
        default=None,
        help="Optional output C header path with embedded RGB565 byte array",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="prodtest_embedded_image_data",
        help="C symbol base name used with --output-c",
    )
    parser.add_argument(
        "--tty",
        type=Path,
        default=None,
        help="Optional tty device path (for direct send), e.g. /dev/ttyACM1",
    )
    parser.add_argument(
        "--line-delay-ms",
        type=int,
        default=5,
        help="Delay between sent lines when using --tty (default: 5)",
    )
    args = parser.parse_args()

    if args.width <= 0 or args.height <= 0:
        print("Width and height must be positive.", file=sys.stderr)
        return 2
    if args.chunk_bytes <= 0:
        print("--chunk-bytes must be positive.", file=sys.stderr)
        return 2
    if args.line_delay_ms < 0:
        print("--line-delay-ms must be >= 0.", file=sys.stderr)
        return 2
    outputs = [
        args.output is not None,
        args.output_c is not None,
        args.tty is not None,
    ]
    if sum(outputs) > 1:
        print("Use only one output mode: --output, --output-c, or --tty.", file=sys.stderr)
        return 2

    raw = image_to_rgb565_le(args.image, args.width, args.height)
    commands = emit_commands(raw, args.chunk_bytes)

    if args.tty is not None:
        try:
            send_commands_to_tty(commands, args.tty, args.line_delay_ms)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(
            f"Sent image as display-image commands to {args.tty} "
            f"({len(raw)} bytes raw RGB565).",
            file=sys.stderr,
        )
    elif args.output_c is not None:
        try:
            c_header = emit_c_header(raw, args.width, args.height, args.symbol)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        args.output_c.write_text(c_header, encoding="ascii")
        print(
            f"Wrote {args.output_c} ({len(raw)} bytes raw RGB565, symbol={args.symbol}).",
            file=sys.stderr,
        )
    elif args.output is None:
        sys.stdout.write(commands)
    else:
        args.output.write_text(commands, encoding="ascii")
        print(f"Wrote {args.output} ({len(raw)} bytes raw RGB565).", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
