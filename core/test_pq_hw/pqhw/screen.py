"""Screenshots of a running T3W1 over SWD.

Neither debuglink returns pixels on hardware, so the frame buffer is read over
SWD instead.
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
UI draws into the other buffer and swaps, so the displayed one is stable while
no swap happens. A read takes over a second, though, and two swaps inside it
(A -> B -> A) leave CFBAR unchanged while A was redrawn under the read, which
gives a picture made of two frames. So besides comparing CFBAR before and
after, every SAMPLE_STEP-th line is read again at the end and must match: a
redraw anywhere in the read changes the lines read before it. A capture that
fails either check is taken again.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import threading
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

# SWD clock in kHz: an ST-Link V3's maximum (measured on the bench: 3.2 s per
# capture against 4.1 s at 8000). Lower it with PQHW_SWD_KHZ on a long cable
# or an older probe. The target config's own default is much slower.
SWD_KHZ = int(os.environ.get("PQHW_SWD_KHZ", "24000"))
TEAR_RETRIES = 3
# Lines re-read after the frame to prove nothing was redrawn during the read.
SAMPLE_STEP = 8
SAMPLE_LINES = range(0, HEIGHT, SAMPLE_STEP)

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


# One openocd at a time: the RSOD watcher polls from a thread.
_probe_lock = threading.Lock()


def _openocd(commands: str) -> str:
    with _probe_lock:
        return _openocd_unlocked(commands)


def _openocd_unlocked(commands: str) -> str:
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


def _settled(frame: bytes, samples: dict[int, bytes]) -> bool:
    """The re-read lines match the frame: nothing was redrawn during the read."""
    line = WIDTH * 4
    return all(frame[y * STRIDE : y * STRIDE + line] == d for y, d in samples.items())


def _one_session(reg: int, tmp: Path) -> tuple[int, int, bytes, bool]:
    """CFBAR before, the frame, the sample lines again, CFBAR after, in a
    single openocd run.

    Needs `read_memory` and Jim's file I/O; the register values go out through
    a file, and through `echo` as a second channel, since console output of
    commands given with -c is not reliable across openocd builds.
    """
    frame = tmp / "fb.bin"
    regs = tmp / "regs.txt"
    resample = "".join(
        f"dump_image {tmp / f's{y}.bin'} [expr {{$a + {y * STRIDE}}}] {WIDTH * 4}; "
        for y in SAMPLE_LINES
    )
    out = _openocd(
        "init; "
        f"set a [lindex [read_memory {reg:#x} 32 1] 0]; "
        f"dump_image {frame} $a {FRAME_SIZE}; "
        f"{resample}"
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
    data = frame.read_bytes()
    samples = {}
    for y in SAMPLE_LINES:
        path = tmp / f"s{y}.bin"
        if not path.exists():
            raise ScreenError(f"single-session capture lost sample line {y}")
        samples[y] = path.read_bytes()
    return int(m.group(1), 0), int(m.group(2), 0), data, _settled(data, samples)


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


# The bootloader's boot command and arguments (`g_boot_command`, 8 B, then
# `g_boot_args`, section .boot_args): the same addresses in every release
# (tests/test_fixtures.py checks the ELFs).
BOOT_COMMAND = 0x30000000
BOOT_ARGS = 0x30000008
BOOT_ARGS_SIZE = 248
BOOT_COMMAND_SHOW_RSOD = 0x7CD945A0
# systask_postmortem_t: reason (1 B enum), privileged (1), then, 4-aligned, the
# error union's title, message and footer, 64 B each.
_PM_TEXT = ((4, "title"), (68, "message"), (132, "footer"))


def rsod_now() -> dict[str, str] | None:
    """The RSOD on screen right now, read from RAM; None if there is none.

    A fatal error saves its texts with BOOT_COMMAND_SHOW_RSOD, shows them for
    10 s, then reboots with a command that clears them: the texts are
    readable only while the RSOD is up. A screenshot every 30-40 s catches
    that by chance; polling this does not.
    """
    if probe_holder is not None:
        return None
    try:
        raw = read_memory(BOOT_COMMAND, 8 + BOOT_ARGS_SIZE)
    except ScreenError:
        return None
    if int.from_bytes(raw[:8], "little") != BOOT_COMMAND_SHOW_RSOD:
        return None
    pm = raw[8:]
    texts = {}
    for off, name in _PM_TEXT:
        texts[name] = pm[off : off + 64].split(b"\0", 1)[0].decode(errors="replace")
    return texts


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


def _several_sessions() -> tuple[int, int, bytes, bool]:
    """Slow path: the whole frame twice, which must match."""
    reg, a = _read_cfbar()
    data = read_memory(_check_fb(a), FRAME_SIZE)
    again = read_memory(a, FRAME_SIZE)
    b = int.from_bytes(read_memory(reg, 4), "little")
    return a, b, data, data == again


# --- capture ----------------------------------------------------------------

_fast_path_works: bool | None = None

#: set while something else (the cut-point driver) holds the ST-Link
probe_holder: str | None = None


def _grab() -> tuple[int, int, bytes, bool]:
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


def capture(dest: Path) -> bool:
    """Write the screen as a PNG to `dest`. Returns False when the screen kept
    changing over every attempt: the picture is then the last one taken and
    may mix two frames, which still beats no picture of a transient screen."""
    if probe_holder is not None:
        raise ScreenError(f"SWD probe held by {probe_holder}")
    start = time.monotonic()
    for attempt in range(1, TEAR_RETRIES + 1):
        before, after, data, settled = _grab()
        _check_fb(before)
        settled = settled and before == after
        if settled:
            break
        LOG.info("screen redrawn during capture %d", attempt)
    if len(data) != FRAME_SIZE:
        raise ScreenError(f"short frame read: {len(data)} of {FRAME_SIZE} bytes")
    data += bytes(STRIDE - WIDTH * 4)  # pad the last line to a full stride
    image = Image.frombuffer(
        "RGBA", (STRIDE // 4, HEIGHT), data, "raw", "BGRA", 0, 1
    ).crop((0, 0, WIDTH, HEIGHT))
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(dest)
    LOG.debug("screenshot in %.1f s", time.monotonic() - start)
    return settled


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.DEBUG)
    # python -m pqhw.screen [out.png] -- one capture, for checking the setup
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "screen.png")
    t0 = time.monotonic()
    settled = capture(target)
    note = "" if settled else ", screen was changing: may mix two frames"
    print(f"wrote {target} in {time.monotonic() - t0:.1f} s (SWD {SWD_KHZ} kHz{note})")
