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
from trezorlib.transport import Transport, get_transport
from trezorlib.transport.webusb import WebUsbTransport

LOG = logging.getLogger(__name__)

REPO = Path(__file__).resolve().parents[3]
EMBED = REPO / "core" / "embed"
# The legacy and PQ layouts put FIRMWARE_START in different places (the PQ
# bootloader region is 64 KB larger), and `xtask flash -f` takes the address
# from the tree it runs in. Legacy images are flashed from the legacy source
# tree the fixture builder keeps.
LEGACY_EMBED = REPO / "core" / "test_pq_hw" / "work" / "legacy" / "core" / "embed"
MODEL = "T3W1"
BUTTONS = ScreenButtons(LayoutType.Eckhart)


class UnitError(Exception):
    pass


class AmbiguousUnit(UnitError):
    """More than one candidate on USB: retrying cannot fix it."""


class Unit:
    """One T3W1 on the bench, reachable over SWD (openocd) and USB."""

    def __init__(
        self,
        path: str | None = None,
        stall: float = 6.0,
        ask: t.Callable[[str], None] | None = None,
    ) -> None:
        self.path = path
        #: Asks the person at the bench to act, when the run has one (--operator).
        self.ask = ask
        #: Seconds without an answer after which a request counts as waiting on
        #: a confirmation screen. The bootloader sends no ButtonRequest and its
        #: debuglink reports no layout content, so a stall is the only signal.
        self.stall = stall

    # --- SWD ------------------------------------------------------------------

    def xtask(self, *args: str, embed: Path = EMBED) -> None:
        cmd = ["cargo", "xtask", *args]
        LOG.info("$ %s   (in %s)", " ".join(cmd), embed.relative_to(REPO))
        res = subprocess.run(cmd, cwd=embed, capture_output=True, text=True)
        if res.returncode != 0:
            raise UnitError(f"{' '.join(cmd)} failed:\n{res.stdout}\n{res.stderr}")

    def erase(self) -> None:
        """Whole flash, which also resets the monotonic counters."""
        self.xtask("flash-erase", "-m", MODEL)

    def flash(self, project: str, image: Path, layout: str = "pq") -> None:
        """Write `image` where `project` lives in the given layout."""
        if layout == "legacy":
            if not LEGACY_EMBED.exists():
                raise UnitError(
                    f"{LEGACY_EMBED} is missing: run build_fixtures.py, whose "
                    "legacy worktree provides the legacy flash layout"
                )
            embed = LEGACY_EMBED
        elif layout == "pq":
            embed = EMBED
        else:
            raise ValueError(f"unknown layout {layout!r}")
        self.xtask("flash", "-m", MODEL, "-f", str(image), project, embed=embed)

    def reset(self) -> None:
        self.xtask("reset", "-m", MODEL)

    # --- USB ------------------------------------------------------------------

    def _find(self) -> Transport | None:
        if self.path:
            try:
                return get_transport(self.path)
            except Exception:
                return None
        # USB only: the unit is flashed and driven over its cable, and a BLE or
        # emulator transport answering as well must not be picked instead.
        try:
            devices = WebUsbTransport.enumerate()
        except Exception as e:
            # A device dropping off the bus mid-enumeration (every reboot)
            # fails its descriptor read; it is leaving, so it is not there.
            LOG.debug("enumeration failed, device in transition: %s", e)
            return None
        if len(devices) > 1:
            paths = ", ".join(d.get_path() for d in devices)
            raise AmbiguousUnit(
                f"{len(devices)} USB devices ({paths}); pass --unit-path"
            )
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
        want = {None: "any", True: "bootloader", False: "firmware"}[bootloader]
        LOG.info("waiting up to %.0f s for the unit on USB (%s mode)", timeout, want)
        seen: str | None = None
        while time.monotonic() < deadline:
            try:
                transport = self.wait_present(max(1.0, deadline - time.monotonic()))
                if transport.get_path() != seen:
                    seen = transport.get_path()
                    LOG.info("unit on USB at %s, connecting", seen)
                ctx = TrezorTestContext(transport, auto_interact=True, force_wipe=False)
            except AmbiguousUnit:
                raise
            except Exception as e:  # mid-reboot, interface not ready yet
                if str(e) != str(last):
                    LOG.info("waiting for the device: %s: %s", type(e).__name__, e)
                last = e
                time.sleep(1)
                continue
            f = ctx.features
            mode = bool(f.bootloader_mode)
            LOG.info(
                "connected: %s %s.%s.%s",
                "bootloader" if mode else "firmware",
                f.major_version,
                f.minor_version,
                f.patch_version,
            )
            if bootloader is None or mode == bootloader:
                return ctx
            close(ctx)
            last = UnitError(
                f"device is in {'bootloader' if mode else 'firmware'} mode"
            )
            time.sleep(1)
        raise UnitError(f"no usable connection within {timeout:.0f} s: {last}")


def tap_bootloader_intro(unit: Unit, timeout: float = 120) -> None:
    """Get past the bootloader intro ("Initiate connection") over debuglink.

    A plain RebootToBootloader lands there, and the wire interface comes up
    only after the tap. A debuglink bootloader starts USB with its debug
    interface at boot, so the tap can be sent from the host. Only for that
    entry: on the connect screen of an install, the same spot is Cancel.
    """
    deadline = time.monotonic() + timeout
    last: Exception | None = None
    while time.monotonic() < deadline:
        try:
            transport = unit.wait_present(max(1.0, deadline - time.monotonic()))
            debug = DebugLink(transport.find_debug())
            debug.model = models.T3W1
            debug.open()
        except AmbiguousUnit:
            raise
        except Exception as e:  # debug interface not up yet
            last = e
            time.sleep(0.5)
            continue
        try:
            # answered once the intro layout is on screen
            debug._call(
                messages.DebugLinkGetState(
                    wait_layout=messages.DebugWaitType.CURRENT_LAYOUT
                ),
                timeout=30,
            )
            x, y = BUTTONS.info()  # the single, full-width action-bar button
            debug._write(messages.DebugLinkDecision(x=x, y=y))
            return
        finally:
            try:
                debug.close()
            except Exception:
                pass
    raise UnitError(f"bootloader intro not reachable over debuglink: {last}")


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
