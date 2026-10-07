"""Screenshots of a running T3W1 over SWD.

Neither debuglink returns pixels on hardware, and a T3W1 is not on USB at all
while its boot lockscreen is up, so the frame buffer is read over SWD instead.
This works at every stage (boardloader excepted: it does not drive the LTDC)
and needs no device-side support.

The CPU is not stopped: pausing it for a second mid-install would risk host
timeouts, i.e. test the debugger rather than the firmware. A picture therefore
shows the screen as it is when the read happens, which on a screen waiting for
input is the step itself and on a transient one may already be the next.

The display controller (LTDC) scans layer 1 from the address in its CFBAR
register. On T3W1 that is one of the two GFXMMU virtual buffers, which present
the frame linearly: 520 lines of 768 ARGB8888 pixels, the UI in the first 380
of each line (the layer window maps buffer column 0 to panel column 50). The
UI draws into the other buffer and swaps, so the displayed one is stable unless
a swap lands mid-read; CFBAR is read before and after, and a capture that saw
it change is taken again.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image

LOG = logging.getLogger(__name__)

# LTDC on STM32U5G9: APB2 + 0x6800, layer 1 at +0x84, CFBAR at layer +0x28.
# Tried through the secure alias, then the non-secure one.
LTDC_L1_CFBAR = (0x500168AC, 0x400168AC)
# GFXMMU virtual buffers 0 and 1, secure and non-secure aliases.
FRAME_BUFFERS = (0x34000000, 0x34400000, 0x24000000, 0x24400000)

WIDTH = 380  # DISPLAY_RESX
HEIGHT = 520  # DISPLAY_RESY
STRIDE = 768 * 4  # FRAME_BUFFER_PIXELS_PER_LINE, ARGB8888
FRAME_SIZE = (HEIGHT - 1) * STRIDE + WIDTH * 4

# SWD clock in kHz. An ST-Link V3 goes up to 24000; 8000 holds on ordinary
# cables. The target config's own default is much slower.
SWD_KHZ = int(os.environ.get("PQHW_SWD_KHZ", "8000"))
TEAR_RETRIES = 3

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
        [*OPENOCD, "-c", f"adapter speed {SWD_KHZ}; {commands}"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = res.stdout + res.stderr
    if res.returncode != 0:
        tail = " | ".join(out.strip().splitlines()[-3:])
        raise ScreenError(f"openocd failed: {tail}")
    return out


def _check_fb(fb: int) -> int:
    if fb not in FRAME_BUFFERS:
        raise ScreenError(f"display not running (LTDC scans {fb:#010x})")
    return fb


# --- fast path: one session -------------------------------------------------


def _one_session(reg: int, tmp: Path) -> tuple[int, int, bytes]:
    """CFBAR before, the frame, CFBAR after, in a single openocd run.

    Needs `read_memory` and Jim's file I/O; the register values go out through
    a file, and through `echo` as a second channel, since console output of
    commands given with -c is not reliable across openocd builds.
    """
    frame = tmp / "fb.bin"
    regs = tmp / "regs.txt"
    out = _openocd(
        "init; "
        f"set a [lindex [read_memory {reg:#x} 32 1] 0]; "
        f"dump_image {frame} $a {FRAME_SIZE}; "
        f"set b [lindex [read_memory {reg:#x} 32 1] 0]; "
        'echo "PQHW_CFBAR $a $b"; '
        f'set f [open {regs} w]; puts $f "$a $b"; close $f; '
        "exit"
    )
    text = regs.read_text() if regs.exists() else ""
    m = re.search(r"(\S+)\s+(\S+)", text) or re.search(
        r"PQHW_CFBAR\s+(\S+)\s+(\S+)", out
    )
    if m is None or not frame.exists():
        raise ScreenError("single-session capture produced no result")
    return int(m.group(1), 0), int(m.group(2), 0), frame.read_bytes()


# --- fallback: one session per read -----------------------------------------


def read_memory(address: int, size: int) -> bytes:
    """`size` bytes from the running target, through a file (dump_image writes
    one whatever the build's console behaviour)."""
    with tempfile.TemporaryDirectory() as tmp:
        raw = Path(tmp) / "mem.bin"
        out = _openocd(f"init; dump_image {raw} {address:#x} {size}; exit")
        data = raw.read_bytes() if raw.exists() else b""
    if len(data) != size:
        tail = " | ".join(out.strip().splitlines()[-3:])
        raise ScreenError(f"read of {size} B at {address:#010x} failed: {tail}")
    return data


def _read_cfbar() -> tuple[int, int]:
    """(register address that answered, its value)."""
    errors = []
    for reg in LTDC_L1_CFBAR:
        try:
            return reg, int.from_bytes(read_memory(reg, 4), "little")
        except ScreenError as e:
            errors.append(str(e))
    raise ScreenError("could not read the LTDC register; " + "; ".join(errors))


def displayed_buffer() -> int:
    """Address the LTDC is scanning out right now."""
    return _check_fb(_read_cfbar()[1])


def _several_sessions() -> tuple[int, int, bytes]:
    reg, a = _read_cfbar()
    data = read_memory(_check_fb(a), FRAME_SIZE)
    b = int.from_bytes(read_memory(reg, 4), "little")
    return a, b, data


# --- capture ----------------------------------------------------------------

_fast_path_works: bool | None = None


def _grab() -> tuple[int, int, bytes]:
    global _fast_path_works
    if _fast_path_works is not False:
        for reg in LTDC_L1_CFBAR:
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    result = _one_session(reg, Path(tmp))
                _fast_path_works = True
                return result
            except ScreenError as e:
                LOG.debug("single-session capture via %#010x failed: %s", reg, e)
        if _fast_path_works is None:
            LOG.info("single-session capture unavailable, using separate reads")
            _fast_path_works = False
    return _several_sessions()


def capture(dest: Path) -> Path:
    """Write the screen as a PNG to `dest`."""
    start = time.monotonic()
    for attempt in range(1, TEAR_RETRIES + 1):
        before, after, data = _grab()
        _check_fb(before)
        if before == after:
            break
        LOG.info("buffer swapped during capture %d, taking it again", attempt)
    else:
        raise ScreenError(f"screen kept changing over {TEAR_RETRIES} captures")
    if len(data) != FRAME_SIZE:
        raise ScreenError(f"short frame read: {len(data)} of {FRAME_SIZE} bytes")
    data += bytes(STRIDE - WIDTH * 4)  # pad the last line to a full stride
    image = Image.frombuffer(
        "RGBA", (STRIDE // 4, HEIGHT), data, "raw", "BGRA", 0, 1
    ).crop((0, 0, WIDTH, HEIGHT))
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest)
    LOG.debug("screenshot in %.1f s", time.monotonic() - start)
    return dest


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)
    # python -m pqhw.screen [out.png] -- one capture, for checking the setup
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "screen.png")
    t0 = time.monotonic()
    capture(target)
    print(f"wrote {target} in {time.monotonic() - t0:.1f} s (SWD {SWD_KHZ} kHz)")
