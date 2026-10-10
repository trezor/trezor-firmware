"""The unit under test: flashing over SWD, finding it on USB, talking to it."""

from __future__ import annotations

import logging
import re
import struct
import subprocess
import tempfile
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
MAX_TAPS = 5
#: Seconds the trezorlib connection (protocol probe, THP handshake and the
#: pairing skip) may take. trezorlib reads USB without a timeout, so a device
#: that stops answering mid-handshake would otherwise hang the whole run.
CONNECT_TIMEOUT = 60

# The nRF52832's MCUboot runs single-app: one application slot, no swap, so an
# application written there is what boots (after MCUboot checks its
# signature). MCUboot below it, custom_data and the settings/bond storage
# above it are left alone (nordic/trezor/boards/arm/t3w1_revA_nrf52832).
NRF_SLOT = 0xE000
NRF_SLOT_SIZE = 0x6C000
MCUBOOT_IMAGE_MAGIC = 0x96F3B83D
# nRF52832 POWER.RESETREAS: sticky reset causes, cleared by writing 1s.
NRF_RESETREAS = 0x40000400
NRF_RESETREAS_BITS = {
    0x1: "pin",
    0x2: "watchdog",
    0x4: "soft",
    0x8: "lockup",
    0x10000: "system-off wake (GPIO)",
    0x20000: "system-off wake (LPCOMP)",
    0x40000: "system-off wake (debug)",
    0x80000: "system-off wake (NFC)",
}


def describe_resetreas(value: int) -> str:
    causes = [name for bit, name in NRF_RESETREAS_BITS.items() if value & bit]
    rest = value & ~sum(NRF_RESETREAS_BITS)
    if rest:
        causes.append(f"0x{rest:x}")
    return f"0x{value:08x} ({', '.join(causes) or 'none'})"


def nrf_image_version(image: bytes) -> str:
    """MCUboot image header version: major.minor.revision."""
    magic = struct.unpack_from("<I", image, 0)[0]
    if magic != MCUBOOT_IMAGE_MAGIC:
        raise UnitError(f"not an MCUboot application image (magic 0x{magic:08x})")
    major, minor, rev = struct.unpack_from("<BBH", image, 20)
    return f"{major}.{minor}.{rev}"


def _intel_hex(data: bytes, base: int) -> str:
    """Intel HEX for `data` at `base`, which nrfjprog programs page-wise."""

    def record(rtype: int, addr: int, payload: bytes) -> str:
        body = bytes([len(payload), addr >> 8, addr & 0xFF, rtype]) + payload
        return f":{body.hex().upper()}{(-sum(body)) & 0xFF:02X}"

    lines = []
    upper = None
    for off in range(0, len(data), 16):
        addr = base + off
        if addr >> 16 != upper:
            upper = addr >> 16
            lines.append(record(0x04, 0, upper.to_bytes(2, "big")))
        lines.append(record(0x00, addr & 0xFFFF, data[off : off + 16]))
    lines.append(record(0x01, 0, b""))
    return "\n".join(lines) + "\n"


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
        nrf_jlink: str | None = None,
    ) -> None:
        self.path = path
        #: J-Link wired to the nRF (a serial number, or "auto" for the only
        #: one attached); None leaves the nRF as the previous run left it.
        self.nrf_jlink = nrf_jlink
        #: The RSOD texts seen during the last watched wait (flows), if any.
        self.last_rsod: dict[str, str] | None = None
        #: Asks the person at the bench to act, when the run has one (--operator).
        self.ask = ask
        #: Flow recorder for the HTML report (set by conftest under --hw).
        self.recorder: t.Any = None
        self._last_enum_error: str | None = None
        #: USB identity of the last connection, for wait_gone.
        self._connected: tuple[int, int] | None = None
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

    # --- nRF over J-Link -------------------------------------------------------

    def _nrfjprog(self, *args: str) -> str:
        cmd = ["nrfjprog", "-f", "NRF52"]
        if self.nrf_jlink and self.nrf_jlink != "auto":
            cmd += ["-s", self.nrf_jlink]
        cmd += list(args)
        LOG.info("$ %s", " ".join(cmd))
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if res.returncode != 0:
            raise UnitError(f"{' '.join(cmd)} failed:\n{res.stdout}\n{res.stderr}")
        return res.stdout

    def nrf_resetreas(self, clear: bool = False) -> int | None:
        """The nRF's sticky reset causes (None without a J-Link); `clear`
        resets them afterwards, so the next read shows only later resets."""
        if not self.nrf_jlink:
            return None
        out = self._nrfjprog("--memrd", f"{NRF_RESETREAS:#x}", "--n", "4")
        m = re.search(r":\s*([0-9A-Fa-f]{8})", out)
        if m is None:
            raise UnitError(f"could not read RESETREAS:\n{out}")
        if clear:
            self._nrfjprog("--memwr", f"{NRF_RESETREAS:#x}", "--val", "0xFFFFFFFF")
        # nrfjprog can leave the core halted, and a halted nRF does not answer
        # the bootloader, which then pushes an image the nRF already runs.
        self._nrfjprog("--run")
        return int(m.group(1), 16)

    def stall_nrf_push(
        self, start: float = 5.0, window: float = 60.0, hold: float = 15.0
    ) -> bool:
        """Make the next nRF push fail, as KB-11 did: from `start` s on, poll
        the nRF and, once it runs MCUboot (a push holds it there for ~25 s;
        the application runs above the slot start), halt it for `hold` s.
        Returns whether a push was caught within `window` s."""
        time.sleep(start)
        deadline = time.monotonic() + window
        while time.monotonic() < deadline:
            try:
                # Halts the core for the read.
                regs = self._nrfjprog("--readregs")
            except UnitError:
                time.sleep(1)  # the STM is resetting the nRF
                continue
            m = re.search(r"PC:\s*0x([0-9A-Fa-f]+)", regs)
            if m is not None and int(m.group(1), 16) < NRF_SLOT:
                LOG.info("nRF in MCUboot: holding it for %.0f s", hold)
                time.sleep(hold)
                self._nrfjprog("--run")
                return True
            self._nrfjprog("--run")
            time.sleep(1)
        return False

    def flash_nrf(self, image: bytes, label: str) -> bool:
        """Put the nRF on a known application image; False without a J-Link.

        Only the pages the image covers are erased: MCUboot, custom_data and
        the bond storage stay. The image is verified after writing; whether
        it starts is checked after the reset, when the nRF is not held in
        MCUboot (see below).
        """
        if not self.nrf_jlink:
            return False
        version = nrf_image_version(image)
        if len(image) > NRF_SLOT_SIZE:
            raise UnitError(f"nRF image {label} does not fit the slot")
        with tempfile.NamedTemporaryFile("w", suffix=".hex") as f:
            f.write(_intel_hex(image, NRF_SLOT))
            f.flush()
            self._nrfjprog("--program", f.name, "--sectorerase", "--verify")
        self._nrfjprog("--reset")
        # An erased STM leaves the nRF's STAY_IN_BLD line floating, and
        # MCUboot may then wait in serial recovery instead of starting the
        # application; the STM's next boot resets the nRF properly. So an nRF
        # still in MCUboot is noted, not failed: the image itself is verified.
        in_app = False
        for _ in range(3):
            time.sleep(1)
            # Halts the core for one register read, then lets it run on.
            regs = self._nrfjprog("--readregs")
            self._nrfjprog("--run")
            m = re.search(r"PC:\s*0x([0-9A-Fa-f]+)", regs)
            if m is not None and int(m.group(1), 16) >= NRF_SLOT:
                in_app = True
                break
        if not in_app:
            self.step(
                f"nRF set to {label} ({version}), but it waits in MCUboot "
                "(STAY_IN_BLD floats while the STM is erased)",
                screenshot=False,
            )
            return True
        self.step(f"nRF set to {label} ({version}) over J-Link", screenshot=False)
        return True

    def step(self, caption: str, screenshot: bool = True) -> None:
        """A point in the flow worth seeing: logged, and captured for the report
        (with a screenshot unless the step changes nothing on screen)."""
        if self.recorder is not None:
            self.recorder.step(caption, screenshot=screenshot)
        else:
            LOG.info("step: %s", caption)

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
            # Logged once per message: a unit stuck failing enumeration would
            # otherwise look exactly like one that is absent.
            msg = f"{type(e).__name__}: {e}"
            if msg != self._last_enum_error:
                LOG.info("USB enumeration failed (device in transition?): %s", msg)
                self._last_enum_error = msg
            return None
        self._last_enum_error = None
        if len(devices) > 1:
            paths = ", ".join(d.get_path() for d in devices)
            raise AmbiguousUnit(
                f"{len(devices)} USB devices ({paths}); pass --unit-path"
            )
        return devices[0] if devices else None

    def present(self) -> bool:
        return self._find() is not None

    @staticmethod
    def _identity(transport: Transport | None) -> tuple[int, int] | None:
        """(bus, address): the address is new on every enumeration, so it tells
        a rebooted device from one that never left."""
        device = getattr(transport, "device", None)
        if device is None:
            return None
        try:
            return device.getBusNumber(), device.getDeviceAddress()
        except Exception:
            return None

    @staticmethod
    def wire_answers(transport: Transport, timeout: float = 2.0) -> bool:
        """Whether the wire interface answers. The bootloader's intro has USB
        up and even takes packets, but does not read them until it is tapped;
        trezorlib's own protocol probe then waits for an answer forever. So
        this sends the same probe, a v1 Cancel, with its own timeout. Every
        mode answers it: a bootloader or v1 firmware with a Failure, a THP
        firmware with Failure(InvalidProtocol). The answer is drained so it
        cannot reach the next session."""
        import usb1

        ms = int(timeout * 1000)
        try:
            transport.open()
        except Exception:
            return False
        try:
            h, ep = transport.handle, transport.endpoint
            cancel = messages.MessageType.Cancel
            packet = b"?##" + int(cancel).to_bytes(2, "big") + (0).to_bytes(4, "big")
            try:
                sent = h.interruptWrite(ep, packet.ljust(64, b"\0"), ms)
            except usb1.USBErrorTimeout as e:
                sent = e.transferred
            if not sent:
                return False
            answered = False
            wait = ms
            # the answer, then the rest of it, packet by packet; capped, so a
            # device that keeps sending cannot hold the probe
            for _ in range(64):
                try:
                    h.interruptRead(0x80 | ep, 64, wait)
                except usb1.USBErrorTimeout as e:
                    return answered or bool(e.received)
                answered = True
                wait = 300
            return answered
        except Exception:
            return False
        finally:
            try:
                transport.close()
            except Exception:
                pass

    def wait_gone(self, timeout: float = 15) -> None:
        """Until the device connected last has rebooted: seen absent, or back
        under a new USB address (a fast reboot can complete between polls, or
        while a screenshot is being taken)."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            transport = self._find()
            if transport is None:
                return
            ident = self._identity(transport)
            if self._connected is not None and ident not in (None, self._connected):
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

    def _connect(self, transport: Transport) -> TrezorTestContext:
        """TrezorTestContext, but abandoned after CONNECT_TIMEOUT seconds.

        On a stall the screen is captured (that is the one clue to what the
        device waits for) and the transport is closed, which fails the stuck
        read in the worker; the caller then retries.
        """
        result: dict[str, t.Any] = {}

        def worker() -> None:
            try:
                result["ctx"] = TrezorTestContext(
                    transport, auto_interact=True, force_wipe=False
                )
            except BaseException as e:  # re-raised in the caller's thread
                result["error"] = e

        th = threading.Thread(target=worker, daemon=True)
        th.start()
        th.join(CONNECT_TIMEOUT)
        if th.is_alive():
            self.step(f"connection stalled for {CONNECT_TIMEOUT} s, retrying")
            try:
                transport.close()
            except Exception:
                pass
            th.join(10)
            raise UnitError(f"connection stalled for {CONNECT_TIMEOUT} s")
        if "error" in result:
            raise result["error"]
        return result["ctx"]

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
                if not self.wire_answers(transport):
                    raise UnitError("on USB, but the wire interface is silent")
                ctx = self._connect(transport)
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
                self._connected = self._identity(transport)
                self.step(
                    f"{'bootloader' if mode else 'firmware'} "
                    f"{f.major_version}.{f.minor_version}.{f.patch_version}"
                )
                return ctx
            close(ctx)
            last = UnitError(
                f"device is in {'bootloader' if mode else 'firmware'} mode"
            )
            time.sleep(1)
        raise UnitError(f"no usable connection within {timeout:.0f} s: {last}")


def tap_bootloader_intro(
    unit: Unit, timeout: float = 120, bootloader_only: bool = False
) -> bool:
    """Get past the bootloader intro ("Initiate connection") over debuglink.

    A plain RebootToBootloader lands there, and the wire interface comes up
    only after the tap. A debuglink bootloader starts USB with its debug
    interface at boot, so the tap can be sent from the host. Only for that
    entry: on the connect screen of an install, the same spot is Cancel.

    With `bootloader_only`, nothing is tapped unless the screen is the
    intro: no layout tokens, or tokens with its "Initiate connection".
    Returns whether it tapped.
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
            state = debug._call(
                messages.DebugLinkGetState(
                    wait_layout=messages.DebugWaitType.CURRENT_LAYOUT
                ),
                timeout=30,
            )
            tokens = " ".join(getattr(state, "tokens", None) or [])
            # the intro shows this button; no firmware screen does
            if bootloader_only and tokens and "Initiate connection" not in tokens:
                LOG.info("not the bootloader intro, no tap; screen: %s", tokens[:200])
                return False
            unit.step("bootloader intro: tapping 'Initiate connection'")
            x, y = BUTTONS.info()  # the single, full-width action-bar button
            debug._write(messages.DebugLinkDecision(x=x, y=y))
            return True
        except Exception as e:  # USB still settling after the reboot
            if str(e) != str(last):
                LOG.info("bootloader debuglink not ready: %s", e)
            last = e
            time.sleep(1)
        finally:
            try:
                debug.close()
            except Exception:
                pass
    raise UnitError(f"bootloader intro not reachable over debuglink: {last}")


def _layout_tokens(debug: DebugLink, timeout: float = 30) -> str:
    """The current layout as one string (its JSON tokens, joined)."""
    state = debug._call(
        messages.DebugLinkGetState(wait_layout=messages.DebugWaitType.CURRENT_LAYOUT),
        timeout=timeout,
    )
    return "".join(getattr(state, "tokens", None) or [])


def read_screen(unit: Unit, timeout: float = 120) -> tuple[str, t.Any]:
    """The current layout's tokens and the USB identity it was read under,
    from whatever is running a debuglink (a locked firmware included)."""
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
            return _layout_tokens(debug), unit._identity(transport)
        except Exception as e:
            last = e
            time.sleep(1)
        finally:
            try:
                debug.close()
            except Exception:
                pass
    raise UnitError(f"no debuglink layout within {timeout:.0f} s: {last}")


def unlock_lockscreen(unit: Unit, code: str, timeout: float = 120) -> str:
    """Enter `code` (a PIN or the wipe code) at a firmware's boot lockscreen.

    Debug builds start USB and a debuglink session before the PIN prompt, so
    the lockscreen is driven like the click tests do it: a tap opens the PIN
    keyboard, then the code goes in as text input. The writes are raw: the
    boot-time debug session ends when the boot screen does, so a decision that
    unlocks the device may never be answered. Returns the lockscreen's layout
    tokens, for checks on what it showed.
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
            lockscreen = _layout_tokens(debug)
            if "PinKeyboard" not in lockscreen:
                unit.step("boot lockscreen: tapping to open the PIN keyboard")
                for _ in range(MAX_TAPS):
                    x, y = BUTTONS.info()
                    debug._write(messages.DebugLinkDecision(x=x, y=y))
                    time.sleep(1)
                    if "PinKeyboard" in _layout_tokens(debug):
                        break
                else:
                    raise UnitError("the PIN keyboard did not open")
            unit.step(f"PIN keyboard: entering {code} over debuglink")
            debug._write(messages.DebugLinkDecision(input=code))
            return lockscreen
        except UnitError:
            raise
        except Exception as e:  # USB still settling after the reboot
            if str(e) != str(last):
                LOG.info("firmware debuglink not ready: %s", e)
            last = e
            time.sleep(1)
        finally:
            try:
                debug.close()
            except Exception:
                pass
    raise UnitError(f"boot lockscreen not reachable over debuglink: {last}")


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
    msg = messages.DebugLinkDecision(x=x, y=y)
    try:
        debug._write(msg)
    except Exception:
        # the test context opens its debug transport only for a probe
        debug.open()
        debug._write(msg)


T = t.TypeVar("T")


def call_watching_prompt(
    ctx: TrezorTestContext,
    func: t.Callable[[], T],
    *,
    stall: float,
    confirm: bool = True,
    timeout: float = 600,
    on_prompt: t.Callable[[], None] | None = None,
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
        if on_prompt is not None:
            on_prompt()
        # Some installs confirm on more than one screen; keep tapping while the
        # request stays blocked. A tap on a progress screen does nothing.
        for tap in range(1, MAX_TAPS + 1):
            LOG.info("request blocked %.0f s: tapping confirm (%d)", stall, tap)
            bootloader_tap_confirm(ctx.debug)
            th.join(stall)
            if not th.is_alive():
                break
        th.join(timeout)
        if th.is_alive():
            raise UnitError(f"no answer {timeout:.0f} s after {MAX_TAPS} taps")
    if "error" in result:
        raise result["error"]
    return result["value"], prompted


def run_watching_stalls(
    ctx: TrezorTestContext,
    work: t.Callable[[t.Callable[[], None]], T],
    *,
    stall: float,
    confirm: bool = True,
    timeout: float = 600,
    on_prompt: t.Callable[[], None] | None = None,
) -> tuple[T, bool]:
    """Run a multi-request exchange; tap confirm whenever it stops progressing.

    For flows whose confirmation comes mid-stream: a legacy bootloader answers
    FirmwareErase at once, reads the headers, and only then asks. `work` gets a
    `tick` to call on every step that made progress.
    """
    last = time.monotonic()

    def tick() -> None:
        nonlocal last
        last = time.monotonic()

    result: dict[str, t.Any] = {}

    def worker() -> None:
        try:
            result["value"] = work(tick)
        except BaseException as e:  # re-raised in the caller's thread
            result["error"] = e

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    deadline = time.monotonic() + timeout
    taps = 0
    while th.is_alive() and time.monotonic() < deadline:
        th.join(0.5)
        if th.is_alive() and time.monotonic() - last > stall:
            if not confirm:
                raise UnitError(
                    "device is waiting on a confirmation that should not appear"
                )
            if taps >= MAX_TAPS:
                raise UnitError(f"still blocked after {MAX_TAPS} taps")
            taps += 1
            if taps == 1 and on_prompt is not None:
                on_prompt()
            LOG.info("exchange stalled %.0f s: tapping confirm (%d)", stall, taps)
            bootloader_tap_confirm(ctx.debug)
            tick()
    if th.is_alive():
        raise UnitError(f"no answer within {timeout:.0f} s")
    if "error" in result:
        raise result["error"]
    return result["value"], taps > 0


def firmware_debuglink(
    transport: Transport, version: tuple[int, int, int]
) -> DebugLink:
    """A standalone firmware debuglink, for driving screens without a session."""
    debug = DebugLink(transport.find_debug())
    debug.model = models.T3W1
    debug.version = version
    debug.open()
    return debug
