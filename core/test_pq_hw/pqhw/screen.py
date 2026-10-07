"""Screenshots of a running T3W1 over SWD.

Neither debuglink returns pixels on hardware, and a T3W1 is not on USB at all
while its boot lockscreen is up, so the frame buffer is read over SWD instead.
This works at every stage (boardloader excepted: it does not drive the LTDC),
needs no device-side support, and does not stop the CPU.

The display controller (LTDC) scans layer 1 from the address in its CFBAR
register. On T3W1 that is one of the two GFXMMU virtual buffers, which present
the frame linearly: 520 lines of 768 ARGB8888 pixels, the UI in the first 380
of each line (the layer window maps buffer column 0 to panel column 50).
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image

# LTDC on STM32U5G9: APB2 + 0x6800, layer 1 at +0x84, CFBAR at layer +0x28.
# Tried through the secure alias, then the non-secure one.
LTDC_L1_CFBAR = (0x500168AC, 0x400168AC)
# GFXMMU virtual buffers 0 and 1, secure and non-secure aliases.
FRAME_BUFFERS = (0x34000000, 0x34400000, 0x24000000, 0x24400000)

WIDTH = 380  # DISPLAY_RESX
HEIGHT = 520  # DISPLAY_RESY
STRIDE = 768 * 4  # FRAME_BUFFER_PIXELS_PER_LINE, ARGB8888

OPENOCD = [
    "openocd",
    "-f",
    "interface/stlink.cfg",
    "-c",
    "transport select hla_swd",
    "-f",
    "target/stm32u5x.cfg",
]


class ScreenError(Exception):
    pass


def _openocd(commands: str) -> str:
    res = subprocess.run(
        [*OPENOCD, "-c", commands], capture_output=True, text=True, timeout=120
    )
    out = res.stdout + res.stderr
    if res.returncode != 0:
        raise ScreenError(f"openocd failed: {out.strip().splitlines()[-1:]}")
    return out


def read_memory(address: int, size: int) -> bytes:
    """`size` bytes from the running target, through a file.

    `mdw` output is not echoed to the console by every openocd build, so the
    bytes go through dump_image, which writes a file either way.
    """
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "mem.bin"
        out = _openocd(f"init; dump_image {raw} {address:#x} {size}; exit")
        data = raw.read_bytes() if raw.exists() else b""
    if len(data) != size:
        tail = " | ".join(out.strip().splitlines()[-3:])
        raise ScreenError(f"read of {size} B at {address:#010x} failed: {tail}")
    return data


def displayed_buffer() -> int:
    """Address the LTDC is scanning out right now."""
    errors = []
    for reg in LTDC_L1_CFBAR:
        try:
            fb = int.from_bytes(read_memory(reg, 4), "little")
        except ScreenError as e:
            errors.append(str(e))
            continue
        if fb not in FRAME_BUFFERS:
            raise ScreenError(f"display not running (LTDC scans {fb:#010x})")
        return fb
    raise ScreenError("could not read the LTDC register; " + "; ".join(errors))


def capture(dest: Path) -> Path:
    """Write the screen as a PNG to `dest`."""
    fb = displayed_buffer()
    size = (HEIGHT - 1) * STRIDE + WIDTH * 4
    data = read_memory(fb, size)
    data += bytes(STRIDE - WIDTH * 4)  # pad the last line to a full stride
    image = Image.frombuffer(
        "RGBA", (STRIDE // 4, HEIGHT), data, "raw", "BGRA", 0, 1
    ).crop((0, 0, WIDTH, HEIGHT))
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest)
    return dest


if __name__ == "__main__":
    import sys

    # python -m pqhw.screen [out.png] -- one capture, for checking the setup
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "screen.png")
    print(f"LTDC scans {displayed_buffer():#010x}")
    print(f"wrote {capture(target)}")
