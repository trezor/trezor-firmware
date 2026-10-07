"""SWD cut points: stop the unit at a named function and reset it there,
which is a power cut at a chosen point of the install, repeatable to the
instruction.

openocd sets a hardware breakpoint on the function (its address from the ELF
of the code that will run it), waits for the unit to halt there, clears the
breakpoint and resets. Modes:

  before  reset on entry: the function never ran
  after   run it to its return, then reset: it ran, nothing after it did
  during  let it run `delay` seconds past entry, then reset

The breakpoint is armed while the code it names is the code that will run:
an address from release B's bootloader means nothing to release A's. Arm a
cut in a bootloader that boots later (after the boardloader swap) only once
the old one has stopped.

While armed, openocd holds the ST-Link: screenshots and xtask flash/reset
cannot run, and steps recorded meanwhile carry no picture.
"""

from __future__ import annotations

import logging
import subprocess
import tempfile
import threading
import time
import typing as t
from dataclasses import dataclass, field
from pathlib import Path

from elftools.elf.elffile import ELFFile

from . import screen

LOG = logging.getLogger(__name__)

MODES = ("before", "after", "during")

#: T3W1: the boardloader, where a reset halts the core (memory.h)
BOARDLOADER = range(0x0C004000, 0x0C01E000)
#: T3W1 boot UCB (BOOTUCB_START): magic, header and code address, header hash
UCB = 0x0C01C000
UCB_SIZE = 48
#: T3W1 BOOTLOADER_START
BOOTLOADER = 0x0C01E000
#: when watched memory is read: halted at the cut, halted right after the
#: reset, and SETTLE seconds after the unit was let run again
MOMENTS = ("cut", "reset", "boot")
SETTLE = 8.0

#: name -> (address, length) of memory to snapshot at each moment
Watch = dict[str, tuple[int, int]]
#: (label, ELF, function): calls to record during the boot after the reset
Trace = list[tuple[str, Path, str]]
#: how long the boot after the reset is traced
TRACE_SECONDS = 20.0
#: bytes dumped at each traced call's first argument
TRACE_ARG_BYTES = 48


def symbol_address(elf: Path, name: str) -> int:
    with elf.open("rb") as f:
        for sym in ELFFile(f).get_section_by_name(".symtab").iter_symbols():
            if sym.name == name and sym["st_info"]["type"] == "STT_FUNC":
                return sym["st_value"] & ~1
    raise KeyError(f"{name} is not a function in {elf.name}")


def symbolize(addr: int, elfs: list[Path]) -> str:
    """`function+offset` of a code address, from the first ELF covering it."""
    addr &= ~1
    for elf in elfs:
        with elf.open("rb") as f:
            for sym in ELFFile(f).get_section_by_name(".symtab").iter_symbols():
                start, size = sym["st_value"] & ~1, sym["st_size"]
                if (
                    sym["st_info"]["type"] == "STT_FUNC"
                    and size
                    and start <= addr < start + size
                ):
                    return (
                        f"{sym.name}+{addr - start:#x} ({elf.parent.name}/{elf.name})"
                    )
    return f"{addr:#010x}"


@dataclass(frozen=True)
class CutPoint:
    elf: Path
    symbol: str
    mode: str = "before"
    #: seconds the function runs before the reset, for mode "during"
    delay: float = 0.0

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")

    @property
    def address(self) -> int:
        """`symbol`, or `symbol+0xoff` for an instruction inside a function."""
        name, _, off = self.symbol.partition("+")
        return symbol_address(self.elf, name) + (int(off, 0) if off else 0)

    def __str__(self) -> str:
        extra = f" +{self.delay:g} s" if self.mode == "during" else ""
        return f"{self.mode} {self.symbol}{extra} ({self.elf.name})"


class CutError(Exception):
    pass


def _trace(marks: Path, trace: list[tuple[str, int]]) -> list[str]:
    """Record each call to the traced functions during the boot: entry (pc,
    caller, first argument), then its return value and the memory the first
    argument pointed to, read once the function has run."""
    if not trace:
        return []
    ms = int(TRACE_SECONDS * 1000)
    hex_re = "{0x[0-9a-fA-F]+}"
    lines = [f"set tf [open {{{marks / 'trace.txt'}}} w]", "set n 0"]
    lines += [f"bp {addr:#x} 2 hw" for _label, addr in trace]
    lines += [
        f"set end [expr {{[clock milliseconds] + {ms}}}]",
        "while {[clock milliseconds] < $end} {",
        "  catch {resume}",
        "  set left [expr {$end - [clock milliseconds]}]",
        "  if {$left <= 0 || [catch {wait_halt $left}]} { break }",
        f"  set pc [lindex [regexp -inline {hex_re} [reg pc]] 0]",
        f"  set lr [lindex [regexp -inline {hex_re} [reg lr]] 0]",
        f"  set a0 [lindex [regexp -inline {hex_re} [reg r0]] 0]",
        # run the call out: a breakpoint on its return address
        f"  rbp all",
        "  bp [expr {$lr & ~1}] 2 hw",
        "  catch {resume}",
        "  if {[catch {wait_halt 5000}]} { set ret timeout } else {",
        f"    set ret [lindex [regexp -inline {hex_re} [reg r0]] 0] }}",
        "  rbp all",
        # quoted, not braced: $n must substitute when catch runs the body
        f'  catch {{dump_image "{marks}/arg$n.bin" $a0 {TRACE_ARG_BYTES}}}',
        '  puts $tf "$n $pc $lr $a0 $ret"; flush $tf',
        "  incr n",
    ]
    lines += [f"  bp {addr:#x} 2 hw" for _label, addr in trace]
    lines += ["}", "rbp all", "close $tf", "catch {resume}"]
    return lines


def _script(
    cut: CutPoint,
    timeout: float,
    marks: Path,
    watch: Watch,
    trace: list[tuple[str, int]] | None = None,
) -> str:
    """Jim Tcl for openocd. Progress goes to marker files: console output of
    scripted commands is not reliable across openocd builds."""

    def snap(moment: str) -> list[str]:
        return [
            f"catch {{dump_image {{{marks / f'{name}@{moment}.bin'}}} {a:#x} {n}}}"
            for name, (a, n) in watch.items()
        ]

    addr = cut.address
    ms = int(timeout * 1000)

    def mark(name: str, value: str = "") -> str:
        return f'set f [open {{{marks / name}}} w]; puts $f "{value}"; close $f'

    lines = [
        f"adapter speed {screen.SWD_KHZ}",
        "init",
        f"bp {addr:#x} 2 hw",
        mark("armed"),
        f"if {{[catch {{wait_halt {ms}}}]}} {{ rbp all; {mark('timeout')}; exit }}",
        "rbp all",
    ]
    if cut.mode == "after":
        # LR at entry is the return address; break there once it runs out
        lines += [
            "set lr [lindex [regexp -inline {0x[0-9a-fA-F]+} [reg lr]] 0]",
            "bp [expr {$lr & ~1}] 2 hw",
            "resume",
            f"if {{[catch {{wait_halt {ms}}}]}} {{ rbp all; {mark('timeout')}; exit }}",
            "rbp all",
        ]
    elif cut.mode == "during":
        lines += ["resume", f"sleep {int(cut.delay * 1000)}"]
    # `reset halt`, not `reset run`: a reset that failed would leave openocd
    # to exit and the core to carry on past the cut, silently. Halted at the
    # reset vector, the PC proves the reset happened; then it runs.
    lines += [
        "set pc [lindex [regexp -inline {0x[0-9a-fA-F]+} [reg pc]] 0]",
        "set hlr [lindex [regexp -inline {0x[0-9a-fA-F]+} [reg lr]] 0]",
        mark("hit_lr", "$hlr"),
        mark("hit", "$pc"),
        *snap("cut"),
        f"if {{[catch {{reset halt}} err]}} {{ {mark('reset_error', '$err')}; exit }}",
        "set rpc [lindex [regexp -inline {0x[0-9a-fA-F]+} [reg pc]] 0]",
        mark("reset", "$rpc"),
        *snap("reset"),
        *_trace(marks, trace or []),
        "catch {resume}",
        f"sleep {int(SETTLE * 1000)}",
        *snap("boot"),
        "exit",
    ]
    return "\n".join(lines) + "\n"


@dataclass
class Armed:
    """An openocd process waiting at a cut point."""

    cut: CutPoint
    timeout: float
    #: memory to snapshot at each of MOMENTS (the UCB is always included)
    watch: Watch = field(default_factory=dict)
    #: calls to record during the boot after the reset
    trace: Trace = field(default_factory=list)
    #: one dict per traced call, in order
    calls: list[dict] = field(default_factory=list)
    _proc: subprocess.Popen | None = None
    _tmp: tempfile.TemporaryDirectory | None = None
    hit_pc: int | None = None
    #: return address at the cut: who called the cut function
    hit_caller: str | None = None
    reset_pc: int | None = None
    #: (name, moment) -> bytes read, absent if the read failed
    snapshots: dict[tuple[str, str], bytes] = field(default_factory=dict)
    output: str = field(default="", repr=False)

    def start(self, arm_timeout: float = 30) -> Armed:
        self._tmp = tempfile.TemporaryDirectory()
        marks = Path(self._tmp.name)
        script = marks / "cut.tcl"
        self.watch = {"ucb": (UCB, UCB_SIZE), **self.watch}
        points = [(label, symbol_address(elf, fn)) for label, elf, fn in self.trace]
        script.write_text(_script(self.cut, self.timeout, marks, self.watch, points))
        screen.probe_holder = f"cut point {self.cut}"
        self._proc = subprocess.Popen(
            [*screen.OPENOCD, "-f", str(script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        deadline = time.monotonic() + arm_timeout
        while not (marks / "armed").exists():
            if self._proc.poll() is not None or time.monotonic() > deadline:
                self.output = self._finish()
                raise CutError(f"could not arm {self.cut}: {self._tail()}")
            time.sleep(0.05)
        LOG.info("armed: %s at %#010x", self.cut, self.cut.address)
        return self

    def wait(self) -> bool:
        """Until the cut fired (True: the unit was reset there) or the timeout
        passed with the unit never reaching it (False)."""
        assert self._proc is not None and self._tmp is not None
        try:
            self._proc.wait(self.timeout * 2 + SETTLE + TRACE_SECONDS + 60)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self.output = self._finish()
        LOG.info("openocd: %s", self._tail())
        marks = Path(self._tmp.name)
        hit = marks / "hit"
        if hit.exists():
            self.hit_pc = int(hit.read_text().strip() or "0", 0)
            lr = marks / "hit_lr"
            if lr.exists() and lr.read_text().strip():
                self.hit_caller = symbolize(
                    int(lr.read_text().strip(), 0), [self.cut.elf]
                )
                LOG.info("cut function called from %s", self.hit_caller)
            for line in self.output.splitlines():
                if "halted due to" in line:
                    LOG.info("openocd: %s", line.strip())
            reset = marks / "reset"
            if not reset.exists():
                err = (
                    (marks / "reset_error").read_text().strip()
                    if (marks / "reset_error").exists()
                    else self._tail()
                )
                raise CutError(
                    f"cut {self.cut} reached (pc {self.hit_pc:#010x}) but the "
                    f"reset failed, so the unit ran on past it: {err}"
                )
            self.reset_pc = int(reset.read_text().strip() or "0", 0)
            for name, (_a, n) in self.watch.items():
                for moment in MOMENTS:
                    f = marks / f"{name}@{moment}.bin"
                    if f.exists() and f.stat().st_size == n:
                        self.snapshots[name, moment] = f.read_bytes()
                    LOG.info(
                        "%s @%s: %s",
                        name,
                        moment,
                        self.snapshots.get((name, moment), b"").hex() or "unread",
                    )
            self._read_trace(marks)
            if self.reset_pc not in BOARDLOADER:
                raise CutError(
                    f"cut {self.cut}: after the reset the core is at "
                    f"{self.reset_pc:#010x}, not in the boardloader; no reset"
                )
            LOG.info(
                "cut %s fired (pc %#010x); reset, core restarted at %#010x",
                self.cut,
                self.hit_pc,
                self.reset_pc,
            )
            return True
        if (Path(self._tmp.name) / "timeout").exists():
            LOG.info("cut %s not reached in %.0f s", self.cut, self.timeout)
            return False
        raise CutError(f"openocd ended without a result: {self._tail()}")

    def _read_trace(self, marks: Path) -> None:
        f = marks / "trace.txt"
        if not self.trace or not f.exists():
            return
        by_addr = {symbol_address(elf, fn): label for label, elf, fn in self.trace}
        elfs = list(dict.fromkeys(elf for _l, elf, _f in self.trace))
        for line in f.read_text().splitlines():
            n, pc, lr, a0, ret = line.split()
            arg = marks / f"arg{n}.bin"
            call = {
                "call": by_addr.get(int(pc, 0), pc),
                "caller": symbolize(int(lr, 0), elfs),
                "arg0": a0,
                "ret": ret,
                "arg_mem": arg.read_bytes().hex() if arg.exists() else None,
            }
            self.calls.append(call)
            LOG.info("traced call: %s", call)
        if not self.calls:
            LOG.info("traced calls: none in %.0f s", TRACE_SECONDS)

    def cancel(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
        self._finish()

    def _finish(self) -> str:
        out = ""
        if self._proc is not None:
            try:
                out, _ = self._proc.communicate(timeout=10)
            except Exception:
                self._proc.kill()
        screen.probe_holder = None
        return out or ""

    def _tail(self) -> str:
        return " | ".join(self.output.strip().splitlines()[-4:])

    def __enter__(self) -> Armed:
        return self

    def __exit__(self, *exc: t.Any) -> None:
        self.cancel()
        if self._tmp is not None:
            self._tmp.cleanup()


def arm(
    cut: CutPoint,
    timeout: float = 300,
    watch: Watch | None = None,
    trace: Trace | None = None,
) -> Armed:
    """Arm `cut` for work the unit does on its own (a boot, a push)."""
    return Armed(cut, timeout, dict(watch or {}), list(trace or [])).start()


@dataclass
class CutResult:
    #: the unit reached the cut point and was reset there
    hit: bool
    #: the host-side action finished (returned or raised) before the cut
    action_done: bool = False
    action_error: BaseException | None = None
    action_value: t.Any = None
    armed: Armed | None = None

    def summary(self, labels: dict[str, dict[bytes, str]] | None = None) -> str:
        return summary(self.armed, labels)

    def action_summary(self) -> str:
        """Where the host side was when the cut fired: still waiting on the
        device (as it should be), or already done."""
        if not self.action_done:
            return "host: still in the exchange at the cut"
        if self.action_error is not None:
            e = self.action_error
            return f"host: exchange ended with {type(e).__name__}: {e}"[:300]
        return f"host: exchange COMPLETED before the cut: {self.action_value!r}"[:300]


def summary(
    armed: Armed | None, labels: dict[str, dict[bytes, str]] | None = None
) -> str:
    """The watched memory at each moment, for the report. `labels` names known
    contents per watch (e.g. which release's bootloader code). The UCB reads
    as erased, armed (its magic), or anything else, which is most likely a
    read the flash protection blanked (the UCB sits in the boardloader's
    range), not data."""
    if armed is None:
        return "nothing watched"
    labels = labels or {}

    def one(name: str, moment: str) -> str:
        data = armed.snapshots.get((name, moment))
        if data is None:
            return "unread"
        if data in labels.get(name, {}):
            return labels[name][data]
        if data == b"\xff" * len(data):
            return "erased"
        if name == "ucb":
            if data[:4] == b"\x00" * 4:
                return "blank read"
            return "ARMED " + data[:12].hex()
        return data.hex()

    return "; ".join(
        f"{name}: " + ", ".join(f"{m} {one(name, m)}" for m in MOMENTS)
        for name in armed.watch
    )


def calls_summary(armed: Armed | None) -> str:
    """The traced calls in order, for the report."""
    if armed is None or not armed.trace:
        return ""
    if not armed.calls:
        return "traced calls: none"
    parts = []
    for c in armed.calls:
        caller = c["caller"].split(" (")[0]
        parts.append(f"{c['call']} from {caller} -> {c['ret']}")
    return "traced calls: " + "; ".join(parts)


def cut_during(
    cut: CutPoint,
    action: t.Callable[[], t.Any],
    timeout: float = 300,
    watch: Watch | None = None,
    trace: Trace | None = None,
) -> CutResult:
    """Arm `cut`, run the host side of the exchange that reaches it, and reset
    the unit there. The action loses its device mid-call; whatever it raises
    then is expected and only kept for the record."""
    box: dict[str, t.Any] = {}
    done = threading.Event()

    def run() -> None:
        try:
            box["value"] = action()
        except BaseException as e:  # the device vanishing mid-call
            box["error"] = e
        finally:
            done.set()

    with arm(cut, timeout, watch, trace) as armed:
        th = threading.Thread(target=run, daemon=True)
        th.start()
        hit = armed.wait()
    # the device reset under the action; give it time to notice
    done.wait(30)
    return CutResult(
        armed=armed,
        hit=hit,
        action_done=done.is_set(),
        action_error=box.get("error"),
        action_value=box.get("value"),
    )
