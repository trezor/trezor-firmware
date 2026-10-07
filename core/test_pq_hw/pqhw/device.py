"""The unit under test: flashing over SWD, finding it on USB, talking to it."""

from __future__ import annotations

import logging
import subprocess
import threading
import time
import typing as t
from pathlib import Path

from trezorlib import messages, models
from trezorlib.debuglink import (
    DebugLink,
    LayoutType,
    ScreenButtons,
    TrezorTestContext,
)
from trezorlib.transport import Transport, enumerate_devices, get_transport

LOG = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[3]
EMBED = REPO / "core" / "embed"
MODEL = "T3W1"
BUTTONS = ScreenButtons(LayoutType.Eckhart)


class UnitError(Exception):
    pass


class Unit:
    """One T3W1 on the bench, reachable over SWD (openocd) and USB."""

    def __init__(self, path: str | None = None, stall: float = 6.0) -> None:
        self.path = path
        #: Seconds without an answer after which a request counts as waiting on
        #: a confirmation screen. The bootloader sends no ButtonRequest and its
        #: debuglink reports no layout content, so a stall is the only signal.
        self.stall = stall

    # --- SWD ------------------------------------------------------------------

    def xtask(self, *args: str) -> None:
        cmd = ["cargo", "xtask", *args]
        LOG.info("$ %s", " ".join(cmd))
        res = subprocess.run(cmd, cwd=EMBED, capture_output=True, text=True)
        if res.returncode != 0:
            raise UnitError(f"{' '.join(cmd)} failed:\n{res.stdout}\n{res.stderr}")

    def erase(self) -> None:
        """Whole flash, which also resets the monotonic counters."""
        self.xtask("flash-erase", "-m", MODEL)

    def flash(self, project: str, image: Path) -> None:
        self.xtask("flash", "-m", MODEL, "-f", str(image), project)

    def reset(self) -> None:
        self.xtask("reset", "-m", MODEL)

    # --- USB ------------------------------------------------------------------

    def _find(self) -> Transport | None:
        if self.path:
            try:
                return get_transport(self.path)
            except Exception:
                return None
        devices = enumerate_devices()
        if len(devices) > 1:
            raise UnitError(f"{len(devices)} devices connected; pass --unit-path")
        return devices[0] if devices else None

    def present(self) -> bool:
        return self._find() is not None

    def wait_gone(self, timeout: float = 15) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not self.present():
                return
            time.sleep(0.2)
        raise UnitError(f"device did not leave the bus within {timeout:.0f} s")

    def wait_present(self, timeout: float = 120) -> Transport:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            transport = self._find()
            if transport is not None:
                return transport
            time.sleep(0.5)
        raise UnitError(f"device did not appear within {timeout:.0f} s")

    def context(
        self, *, bootloader: bool | None = None, timeout: float = 120
    ) -> TrezorTestContext:
        """A debuglink-enabled client, once the device answers in the wanted mode.

        Never wipes: force_wipe is what the device tests use, and here the
        storage is the thing under test.
        """
        deadline = time.monotonic() + timeout
        last: Exception | None = None
        while time.monotonic() < deadline:
            try:
                transport = self.wait_present(max(1.0, deadline - time.monotonic()))
                ctx = TrezorTestContext(transport, auto_interact=True, force_wipe=False)
            except Exception as e:  # mid-reboot, interface not ready yet
                last = e
                time.sleep(1)
                continue
            mode = bool(ctx.features.bootloader_mode)
            if bootloader is None or mode == bootloader:
                return ctx
            close(ctx)
            last = UnitError(
                f"device is in {'bootloader' if mode else 'firmware'} mode"
            )
            time.sleep(1)
        raise UnitError(f"no usable connection within {timeout:.0f} s: {last}")


def close(ctx: TrezorTestContext) -> None:
    """Release the USB handles; a reconnect after a reboot needs them free."""
    for closer in (ctx.debug.close, ctx.transport.close):
        try:
            closer()
        except Exception:
            pass


def bootloader_tap_confirm(debug: DebugLink) -> None:
    """Tap the right action-bar button, which confirms every bootloader prompt.

    Written raw: the bootloader answers a decision with nothing, so the generic
    helpers' layout read-back is not needed.
    """
    x, y = BUTTONS.ok()
    debug._write(messages.DebugLinkDecision(x=x, y=y))


T = t.TypeVar("T")


def call_watching_prompt(
    ctx: TrezorTestContext,
    func: t.Callable[[], T],
    *,
    stall: float,
    confirm: bool = True,
    timeout: float = 600,
) -> tuple[T, bool]:
    """Run a blocking bootloader request; report whether it waited on a prompt.

    If `func` has not returned after `stall` seconds, the device is taken to be
    showing a confirmation: it is confirmed (or, with confirm=False, left alone
    and reported) and the call is awaited.
    """
    result: dict[str, t.Any] = {}

    def worker() -> None:
        try:
            result["value"] = func()
        except BaseException as e:  # re-raised in the caller's thread
            result["error"] = e

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    th.join(stall)
    prompted = th.is_alive()
    if prompted:
        if not confirm:
            raise UnitError(
                "device is waiting on a confirmation that should not appear"
            )
        bootloader_tap_confirm(ctx.debug)
        th.join(timeout)
        if th.is_alive():
            raise UnitError(f"no answer {timeout:.0f} s after confirming")
    if "error" in result:
        raise result["error"]
    return result["value"], prompted


def firmware_debuglink(
    transport: Transport, version: tuple[int, int, int]
) -> DebugLink:
    """A standalone firmware debuglink, for driving screens without a session."""
    debug = DebugLink(transport.find_debug())
    debug.model = models.T3W1
    debug.version = version
    debug.open()
    return debug
