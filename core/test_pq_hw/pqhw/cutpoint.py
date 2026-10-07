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
        with self.elf.open("rb") as f:
            symtab = ELFFile(f).get_section_by_name(".symtab")
            for sym in symtab.iter_symbols():
                if sym.name == self.symbol and sym["st_info"]["type"] == "STT_FUNC":
                    return sym["st_value"] & ~1  # Thumb bit
        raise KeyError(f"{self.symbol} is not a function in {self.elf.name}")

    def __str__(self) -> str:
        extra = f" +{self.delay:g} s" if self.mode == "during" else ""
        return f"{self.mode} {self.symbol}{extra} ({self.elf.name})"


class CutError(Exception):
    pass


def _script(cut: CutPoint, timeout: float, marks: Path) -> str:
    """Jim Tcl for openocd. Progress goes to marker files: console output of
    scripted commands is not reliable across openocd builds."""
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
    lines += [
        "set pc [lindex [regexp -inline {0x[0-9a-fA-F]+} [reg pc]] 0]",
        mark("hit", "$pc"),
        "reset run",
        "exit",
    ]
    return "\n".join(lines) + "\n"


@dataclass
class Armed:
    """An openocd process waiting at a cut point."""

    cut: CutPoint
    timeout: float
    _proc: subprocess.Popen | None = None
    _tmp: tempfile.TemporaryDirectory | None = None
    hit_pc: int | None = None
    output: str = field(default="", repr=False)

    def start(self, arm_timeout: float = 30) -> Armed:
        self._tmp = tempfile.TemporaryDirectory()
        marks = Path(self._tmp.name)
        script = marks / "cut.tcl"
        script.write_text(_script(self.cut, self.timeout, marks))
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
            self._proc.wait(self.timeout * 2 + 60)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self.output = self._finish()
        hit = Path(self._tmp.name) / "hit"
        if hit.exists():
            self.hit_pc = int(hit.read_text().strip() or "0", 0)
            LOG.info("cut %s fired (pc %#010x), unit reset", self.cut, self.hit_pc)
            return True
        if (Path(self._tmp.name) / "timeout").exists():
            LOG.info("cut %s not reached in %.0f s", self.cut, self.timeout)
            return False
        raise CutError(f"openocd ended without a result: {self._tail()}")

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


def arm(cut: CutPoint, timeout: float = 300) -> Armed:
    """Arm `cut` for work the unit does on its own (a boot, a push)."""
    return Armed(cut, timeout).start()


@dataclass
class CutResult:
    #: the unit reached the cut point and was reset there
    hit: bool
    #: the host-side action finished (returned or raised) before the cut
    action_done: bool = False
    action_error: BaseException | None = None
    action_value: t.Any = None


def cut_during(
    cut: CutPoint, action: t.Callable[[], t.Any], timeout: float = 300
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

    with arm(cut, timeout) as armed:
        th = threading.Thread(target=run, daemon=True)
        th.start()
        hit = armed.wait()
    # the device reset under the action; give it time to notice
    done.wait(30)
    return CutResult(
        hit=hit,
        action_done=done.is_set(),
        action_error=box.get("error"),
        action_value=box.get("value"),
    )
