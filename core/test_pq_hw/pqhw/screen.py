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
# A failed nRF push during an install shows the RSOD itself and keeps this
# command, with the texts in its (otherwise unused) arguments.
BOOT_COMMAND_CONTINUE_UPGRADE = 0x6D2F84B1
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
    command = int.from_bytes(raw[:8], "little")
    if command not in (BOOT_COMMAND_SHOW_RSOD, BOOT_COMMAND_CONTINUE_UPGRADE):
        return None
    pm = raw[8:]
    texts = {}
    for off, name in _PM_TEXT:
        texts[name] = pm[off : off + 64].split(b"\0", 1)[0].decode(errors="replace")
    if command == BOOT_COMMAND_CONTINUE_UPGRADE and not texts["title"]:
        return None  # a plain phase-2 boot carries no texts
    return texts


# nrf_update.c `g_last_update`: member offsets (u32 arrays of 3 tries, except
# `tries` and `uart_flags`). tests/test_fixtures.py checks them against the
# ELF's DWARF: a size check alone missed a reordering once.
PUSH_FIELDS = {
    "tries": 0,
    "error": 4,
    "ms": 16,
    "uart_errors": 28,
    "stats": 40,
    "resends": 52,
    "uart_flags": 64,
}
_PUSH_RECORD_SIZE = 68
_PUSH_STEPS = {1: "s", 2: "r", 3: "cs", 4: "cr"}
_PUSH_ERRORS = {1: "to", 2: "wm", 3: "bz"}


def nrf_push_record(elf: Path) -> list[str] | None:
    """The last nRF push of the running bootloader (`g_last_update`), one
    line per try; None if there was none or the record cannot be read.

    A push that succeeds shows nothing on screen, so this is the only view of
    the chunk re-sends it needed (KB-11).
    """
    if probe_holder is not None:
        return None
    from elftools.elf.elffile import ELFFile

    with elf.open("rb") as f:
        symtab = ELFFile(f).get_section_by_name(".symtab")
        syms = symtab.get_symbol_by_name("g_last_update") if symtab else None
    if not syms or syms[0]["st_size"] != _PUSH_RECORD_SIZE:
        return None  # another layout: better nothing than a wrong decode
    try:
        raw = read_memory(syms[0]["st_value"], _PUSH_RECORD_SIZE)
    except ScreenError:
        return None
    tries = raw[0]
    if not 0 < tries <= 3:
        return None
    u32 = lambda off: int.from_bytes(raw[off : off + 4], "little")  # noqa: E731
    lines = []
    for i in range(tries):
        at = {k: v + 4 * i for k, v in PUSH_FIELDS.items()}
        error, ms = u32(at["error"]), u32(at["ms"])
        uart, stats, resends = (
            u32(at["uart_errors"]),
            u32(at["stats"]),
            u32(at["resends"]),
        )
        if error:
            step = _PUSH_STEPS.get(error >> 24, "?")
            err = _PUSH_ERRORS.get((error >> 16) & 0xFF, "?")
            result = f"failed {step}/{err}@{(error & 0xFFFF) * 256}"
        else:
            result = "ok"
        lines.append(
            f"try {i + 1}: {result} after {ms} ms, slowest reply {stats >> 16} ms, "
            f"{resends >> 16} re-sends ({resends & 0xFFFF} answered), "
            f"{uart} UART errors"
        )
    return lines


# STM32U5 USB_OTG_HS, through both aliases: which one answers depends on the
# firmware's TrustZone setup (the other reads as zero).
_OTG_HS = {"ns": 0x42040000, "s": 0x52040000}


def usb_controller_state() -> str:
    """The STM's USB device controller, decoded: whether the firmware
    connected to the bus at all (DCTL.SDIS clear) and whether a host
    enumerated it (DCFG.DAD, the address it was given)."""
    if probe_holder is not None:
        return f"not read: SWD probe held by {probe_holder}"
    parts = []
    for name, base in _OTG_HS.items():
        try:
            core = read_memory(base, 0x40)
            dev = read_memory(base + 0x800, 0x10)
        except ScreenError as e:
            parts.append(f"{name}: unreadable ({e})")
            continue
        u32 = lambda b, off: int.from_bytes(b[off : off + 4], "little")  # noqa: E731
        gotgctl, gccfg = u32(core, 0x00), u32(core, 0x38)
        dcfg, dctl, dsts = u32(dev, 0x0), u32(dev, 0x4), u32(dev, 0x8)
        if not (gotgctl | gccfg | dcfg | dctl | dsts):
            parts.append(f"{name}: all zero")
            continue
        parts.append(
            f"{name}: soft-disconnect {'ON' if dctl & 0x2 else 'off'}, "
            f"address {(dcfg >> 4) & 0x7F}, "
            f"{'suspended' if dsts & 0x1 else 'not suspended'}, "
            f"B-session {'valid' if gotgctl & (1 << 19) else 'invalid'} "
            f"(GOTGCTL {gotgctl:#010x} GCCFG {gccfg:#010x} DCFG {dcfg:#010x} "
            f"DCTL {dctl:#010x} DSTS {dsts:#010x})"
        )
    return "; ".join(parts)


# USB OTG_HS global interrupt on STM32U5 (CMSIS OTG_HS_IRQn).
_OTG_HS_IRQ = 73
# NVIC, read through the secure view: ISER at +0x000, ISPR +0x100, IABR +0x200,
# ITNS +0x280, IPR (one byte per IRQ) +0x300.
_NVIC = 0xE000E100


def _u32(b: bytes, off: int) -> int:
    return int.from_bytes(b[off : off + 4], "little")


def _cpu_state() -> str:
    """PC, active exception and interrupt masks: halts the core briefly, reads
    its registers and lets it run on."""
    # `reg` prints to the console, which -c does not reliably surface: take
    # its output with `capture` into a file. The halt line ("xPSR: .. pc: ..")
    # comes through the log and is the fallback.
    with tempfile.TemporaryDirectory() as tmp:
        dump = Path(tmp) / "regs.txt"
        out = _openocd(
            f"init; halt; set r [capture reg]; resume; "
            f"set f [open {dump} w]; puts $f $r; close $f; exit"
        )
        text = (dump.read_text() if dump.exists() else "") + "\n" + out
    regs = {}
    for name, value in re.findall(
        r"\b([a-z_A-Z]+)\s*\(/\d+\):\s*(0x[0-9a-fA-F]+)", text
    ):
        regs.setdefault(name.lower(), int(value, 16))
    for name, value in re.findall(r"\b(xPSR|pc|msp|psp):\s*(0x[0-9a-fA-F]+)", text):
        regs.setdefault(name.lower(), int(value, 16))
    if "pc" not in regs:
        tail = " | ".join(text.strip().splitlines()[-3:])
        raise ScreenError(f"no registers in the halt output: {tail}")
    ipsr = regs.get("xpsr", 0) & 0x1FF
    where = (
        "thread mode"
        if ipsr == 0
        else (f"IRQ {ipsr - 16} handler" if ipsr >= 16 else f"exception {ipsr} handler")
    )
    masks = ", ".join(
        f"{n} {regs[n]:#x}"
        for n in (
            "primask_s",
            "basepri_s",
            "primask_ns",
            "basepri_ns",
            "primask",
            "basepri",
        )
        if n in regs
    )
    return f"PC {regs['pc']:#010x} in {where} ({masks})"


def usb_stall_state() -> str:
    """Why a firmware that runs never answers USB: is the OTG_HS interrupt
    enabled, pending, being served, and what is the CPU doing instead."""
    if probe_holder is not None:
        return f"not read: SWD probe held by {probe_holder}"
    parts = []
    try:
        nvic = read_memory(_NVIC, 0x400)
        word, bit = 4 * (_OTG_HS_IRQ // 32), 1 << (_OTG_HS_IRQ % 32)
        flag = lambda off: bool(_u32(nvic, off + word) & bit)  # noqa: E731
        parts.append(
            f"IRQ {_OTG_HS_IRQ}: {'enabled' if flag(0x000) else 'DISABLED'}, "
            f"{'PENDING' if flag(0x100) else 'not pending'}, "
            f"{'ACTIVE' if flag(0x200) else 'not active'}, "
            f"targets {'non-secure' if flag(0x280) else 'secure'}, "
            f"priority {nvic[0x300 + _OTG_HS_IRQ]:#04x}"
        )
    except ScreenError as e:
        parts.append(f"NVIC unreadable ({e})")
    for name, base in _OTG_HS.items():
        try:
            core = read_memory(base, 0x20)
            dev = read_memory(base + 0x800, 0x20)
            ep_in = read_memory(base + 0x900, 0x10)
            ep_out = read_memory(base + 0xB00, 0x14)
            pcgcctl = _u32(read_memory(base + 0xE00, 4), 0)
        except ScreenError as e:
            parts.append(f"OTG {name} unreadable ({e})")
            continue
        gahbcfg, gintsts, gintmsk = _u32(core, 0x08), _u32(core, 0x14), _u32(core, 0x18)
        if not (gahbcfg | gintsts | gintmsk):
            continue  # the alias the firmware does not use reads as zero
        daint, daintmsk = _u32(dev, 0x18), _u32(dev, 0x1C)
        parts.append(
            f"OTG {name}: global int {'on' if gahbcfg & 1 else 'OFF'}, "
            f"pending&unmasked {gintsts & gintmsk:#010x} "
            f"(GINTSTS {gintsts:#010x} GINTMSK {gintmsk:#010x}), "
            f"DAINT {daint:#010x}/{daintmsk:#010x}, "
            f"EP0 in ctl {_u32(ep_in, 0):#010x} int {_u32(ep_in, 8):#010x}, "
            f"out ctl {_u32(ep_out, 0):#010x} int {_u32(ep_out, 8):#010x} "
            f"tsiz {_u32(ep_out, 0x10):#010x}, "
            f"PCGCCTL {pcgcctl:#010x} (PHY clock "
            f"{'STOPPED' if pcgcctl & 1 else 'running'}, bus clock "
            f"{'GATED' if pcgcctl & 2 else 'on'}"
            f"{', PHY suspended' if pcgcctl & 0x10 else ''})"
        )
    try:
        parts.append(_cpu_state())
    except ScreenError as e:
        parts.append(f"CPU unreadable ({e})")
    return "; ".join(parts)


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
