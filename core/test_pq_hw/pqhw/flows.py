"""Multi-step operations the tests compose: baselines, installs, seed checks."""

from __future__ import annotations

import logging
import time
import typing as t
from dataclasses import dataclass, replace
from hashlib import blake2s, sha256

from trezorlib import btc, debuglink, device, exceptions, firmware, messages
from trezorlib.debuglink import TrezorTestContext
from trezorlib.firmware.pq_secure import PqSecureBundle
from trezorlib.messages import FirmwareScheme
from trezorlib.tools import parse_path

from .device import (
    Unit,
    UnitError,
    call_watching_prompt,
    close,
    run_watching_stalls,
    tap_bootloader_intro,
)
from .fixtures import Fixtures

LOG = logging.getLogger(__name__)

MNEMONIC = "all all all all all all all all all all all all"
LABEL = "PQHW"
# Works on both variants: btc-only firmware has no other coins.
XPUB_PATH = "m/84h/0h/0h"

# Timeouts. A phase-1 reboot can include the boardloader installing a 320 KB
# bootloader and the bootloader pushing a 271 KB nRF image over UART.
REBOOT = 240
# Phase 1 reboot to phase 2 on USB: boardloader swap plus an nRF push.
PHASE2_RESUME = 150
# On USB with a silent wire this long: the bootloader intro, waiting for a tap.
INTRO_SILENCE = 15
# While waiting for a unit that is off USB (a boardloader swap, an nRF push, a
# restart), a screenshot this often: the report then shows progress, an error
# screen or a restart instead of only the timeout.
WAIT_SCREEN_EVERY = 30


class _WaitScreens:
    """Screenshot steps at most every WAIT_SCREEN_EVERY seconds of a wait."""

    def __init__(self, unit: Unit, what: str) -> None:
        self.unit, self.what = unit, what
        self.start = self.last = time.monotonic()

    def tick(self) -> None:
        now = time.monotonic()
        if now - self.last >= WAIT_SCREEN_EVERY:
            self.last = now
            self.unit.step(f"{self.what}: {now - self.start:.0f} s, not on USB yet")


# --- seed -------------------------------------------------------------------


PIN = "1234"
WIPE_CODE = "9876"


def load_seed(unit: Unit, ctx: TrezorTestContext, pin: str | None = None) -> None:
    """Without a PIN unless asked, so that reboots need no unlock. A PIN at
    boot is entered over debuglink (device.unlock_lockscreen). The storage
    salt binds firmware_type with or without a PIN, so a wrong domain still
    loses the seed."""
    session = ctx.get_seedless_session()
    debuglink.load_device(
        session, MNEMONIC, pin=pin, passphrase_protection=False, label=LABEL
    )
    unit.step(
        f"seed loaded over debuglink (LoadDevice, {'PIN ' + pin if pin else 'no PIN'})"
    )


def seed_fingerprint(unit: Unit, ctx: TrezorTestContext) -> str | None:
    """The account xpub, or None on an uninitialised device. Recorded as a
    text-only step: reading it changes nothing on screen."""
    features = ctx.refresh_features()
    if not features.initialized:
        unit.step("seed check: device not initialised", screenshot=False)
        return None
    session = ctx.get_session(passphrase="")
    node = btc.get_public_node(session, parse_path(XPUB_PATH), coin_name="Bitcoin")
    unit.step(f"seed check: {XPUB_PATH} xpub ...{node.xpub[-12:]}", screenshot=False)
    return node.xpub


# --- baselines ----------------------------------------------------------------


def baseline_legacy(unit: Unit, fx: Fixtures, variant: str) -> TrezorTestContext:
    """Pre-migration state: legacy boardloader, bootloader and firmware."""
    unit.erase()
    unit.flash("boardloader", fx.legacy("boardloader"), layout="legacy")
    unit.flash("bootloader", fx.legacy("bootloader"), layout="legacy")
    unit.flash("firmware", fx.legacy(variant), layout="legacy")
    unit.reset()
    return unit.context(bootloader=False, timeout=REBOOT)


def baseline_pq_empty(unit: Unit, fx: Fixtures, release: str) -> TrezorTestContext:
    """A factory-fresh PQ unit: the release's bootloader, firmware_type NONE."""
    unit.erase()
    unit.flash("boardloader", fx.legacy("boardloader"))
    unit.flash("bootloader", fx.release_bootloader(release))
    unit.reset()
    return unit.context(bootloader=True, timeout=REBOOT)


def baseline_pq_installed(
    unit: Unit, fx: Fixtures, release: str, variant: str, seeded: bool = True
) -> TrezorTestContext:
    """A PQ unit running `release`/`variant`, optionally with the test seed."""
    ctx = baseline_pq_empty(unit, fx, release)
    report = pq_install(unit, ctx, fx.bundle(release, variant))
    assert not report.prompted, "an official install on an empty unit must not ask"
    ctx = unit.context(bootloader=False, timeout=REBOOT)
    if seeded:
        load_seed(unit, ctx)
    return ctx


# --- installs -------------------------------------------------------------------


@dataclass(frozen=True)
class Upload:
    """What an install puts on the wire, taken from a bundle. Tamper cases
    derive an altered copy (dataclasses.replace) instead of patching flows."""

    boot_header: bytes
    #: the image's manifest region, sent as FirmwareBegin.module_headers
    module_headers: bytes
    #: bootloader code, served if the device asks for it
    code: bytes
    nrf_image: bytes | None
    nrf_co_path: bytes | None
    nrf_image_hash: bytes | None
    #: phase 2: the firmware image and its inline chunk hashes
    firmware: bytes
    prev_hashes: dict[int, bytes]

    @classmethod
    def of(cls, bundle: PqSecureBundle, send_nrf: bool = True) -> Upload:
        nrf = bundle.nrf if send_nrf else None
        return cls(
            boot_header=bundle.boot_header,
            module_headers=bundle.firmware.manifest_region,
            code=bundle.bootloader_code,
            nrf_image=nrf.image if nrf else None,
            nrf_co_path=nrf.co_path if nrf else None,
            nrf_image_hash=nrf.image_hash if nrf else None,
            firmware=bundle.firmware.data,
            prev_hashes=bundle.chunk_prev_hashes(),
        )

    def but(self, **changes: t.Any) -> Upload:
        return replace(self, **changes)


@dataclass
class InstallReport:
    #: phase 1 waited on a confirmation screen
    prompted: bool
    #: bytes the device pulled in phase 1, per image ("code", "nrf")
    served: dict[str, int]
    #: phase 2 waited on a confirmation screen (it never should)
    phase2_prompted: bool = False


def enter_bootloader(
    unit: Unit,
    ctx: TrezorTestContext,
    bundle: PqSecureBundle | None = None,
    *,
    preamble: bytes | None = None,
) -> TrezorTestContext:
    """From firmware mode; with `bundle`, as a pre-authorised (interaction-less)
    upgrade the firmware confirms itself. `preamble` replaces the bundle's
    consent preamble (tamper cases); a firmware that refuses it raises its
    TrezorFailure and stays where it is."""
    # a seeded session is refused on an uninitialised device (NotInitialized)
    if ctx.refresh_features().initialized:
        session = ctx.get_session(passphrase="")
    else:
        session = ctx.get_seedless_session()
    unit.step(
        "firmware: reboot to bootloader"
        + (" pre-authorising the release (interaction-less)" if bundle else "")
        + "; its confirm is pressed over debuglink",
        screenshot=False,
    )
    if bundle is None:
        # lands on the bootloader intro, which needs a tap to bring the wire up
        device.reboot_to_bootloader(session)
        close(ctx)
        unit.wait_gone()
        # A tap that lands before the intro is drawn is lost; on this path the
        # screen can only be the intro, so tapping again is safe.
        for _ in range(3):
            tap_bootloader_intro(unit)
            try:
                return unit.context(bootloader=True, timeout=20)
            except UnitError:
                continue
        raise UnitError("bootloader wire did not come up after tapping the intro")
    else:
        try:
            device.reboot_to_bootloader(
                session,
                boot_command=messages.BootCommand.INSTALL_UPGRADE,
                firmware_preamble=(
                    preamble if preamble is not None else bundle.consent_preamble()
                ),
            )
        except exceptions.TrezorFailure as e:
            unit.step(f"firmware refused the upgrade: {e.message}")
            raise
    close(ctx)
    unit.wait_gone()
    return unit.context(bootloader=True, timeout=REBOOT)


def pq_phase1(
    unit: Unit,
    ctx: TrezorTestContext,
    bundle: PqSecureBundle,
    *,
    confirm: bool = True,
    send_nrf: bool = True,
    upload: Upload | None = None,
) -> tuple[bool, dict[str, int]]:
    """FirmwareBegin and whatever code or nRF image the device pulls; returns
    (prompted, bytes served per image). The device then reboots. `upload`
    replaces what the bundle would send."""
    assert ctx.features.bootloader_mode, "phase 1 starts in bootloader mode"
    up = upload or Upload.of(bundle, send_nrf)
    session = ctx.get_seedless_session()
    code = up.code
    nrf_image = up.nrf_image

    def begin() -> messages.FirmwareRequest | messages.Success:
        return session.call(
            messages.FirmwareBegin(
                boot_header=up.boot_header,
                module_headers=up.module_headers,
                code_length=len(code),
                code_hash=sha256(code).digest(),
                nrf_length=len(nrf_image) if nrf_image else None,
                nrf_co_path=up.nrf_co_path,
                nrf_image_hash=up.nrf_image_hash,
            )
        )

    try:
        resp, prompted = call_watching_prompt(
            ctx,
            begin,
            stall=unit.stall,
            confirm=confirm,
            on_prompt=lambda: unit.step("phase 1: confirmation, tapping confirm"),
        )
    except exceptions.TrezorFailure as e:
        # the bootloader also draws its failure screen
        unit.step(f"phase 1 refused: {e.message}")
        raise
    served = {"code": 0, "nrf": 0}
    while isinstance(resp, messages.FirmwareRequest):
        is_nrf = (resp.coprocessor_index or 0) != 0
        src = nrf_image if (is_nrf and nrf_image) else code
        payload = src[resp.offset : resp.offset + resp.length]
        resp = session.call(
            messages.FirmwareUpload(payload=payload, hash=blake2s(payload).digest())
        )
        served["nrf" if is_nrf else "code"] += len(payload)
    messages.Success.ensure_isinstance(resp)
    LOG.info("phase 1 done: prompted=%s served=%s", prompted, served)
    # text only: the device reboots straight away, mid-capture
    unit.step(
        f"phase 1 done (bootloader code {served['code']} B, nRF {served['nrf']} B)",
        screenshot=False,
    )
    return prompted, served


def pq_phase2(unit: Unit, bundle: PqSecureBundle, upload: Upload | None = None) -> bool:
    """After phase 1's reboot: stream the firmware. Returns whether it needed a
    person, which it never should: the bootloader is meant to resume on its own
    (BOOT_COMMAND_CONTINUE_UPGRADE) with the wire up. A rejected stream raises
    the device's TrezorFailure."""
    up = upload or Upload.of(bundle)
    needed_person = False
    try:
        deadline = time.monotonic() + PHASE2_RESUME
        screens = _WaitScreens(unit, "waiting for phase 2")
        while True:
            try:
                ctx = unit.context(
                    bootloader=True,
                    timeout=min(WAIT_SCREEN_EVERY, deadline - time.monotonic()),
                )
                break
            except UnitError:
                if time.monotonic() >= deadline:
                    raise
                screens.tick()
    except UnitError:
        # Not on USB: the bootloader is on its intro ("Initiate connection"),
        # which brings the wire up only after a tap -- it did not resume.
        unit.step("phase 2 did not come up on USB within the resume time")
        if unit.ask is None:
            raise UnitError(
                "phase 2 never came up on USB: the bootloader did not resume the "
                "install on its own (likely on the intro screen, 'Initiate "
                "connection'). Run with --operator to continue past it."
            ) from None
        unit.ask("The device did not resume phase 2. Tap 'Initiate connection'.")
        needed_person = True
        ctx = unit.context(bootloader=True, timeout=REBOOT)
    session = ctx.get_seedless_session()
    data = up.firmware

    def erase() -> t.Any:
        return session.call(messages.FirmwareErase(length=len(data)))

    resp, prompted = call_watching_prompt(ctx, erase, stall=unit.stall, confirm=False)
    try:
        firmware._stream_firmware_upload(
            session, data, resp, lambda _: None, up.prev_hashes
        )
    except exceptions.TrezorFailure as e:
        unit.step(f"phase 2 refused: {e.message}")
        raise
    unit.step("phase 2: firmware streamed", screenshot=False)
    close(ctx)
    unit.wait_gone()
    return prompted or needed_person


def pq_install(
    unit: Unit,
    ctx: TrezorTestContext,
    bundle: PqSecureBundle,
    *,
    confirm: bool = True,
    send_nrf: bool = True,
    upload: Upload | None = None,
) -> InstallReport:
    """Both phases from bootloader mode, ending with the device rebooting into
    the new firmware. A refused install raises the device's TrezorFailure."""
    up = upload or Upload.of(bundle, send_nrf)
    prompted, served = pq_phase1(unit, ctx, bundle, confirm=confirm, upload=up)
    close(ctx)
    unit.wait_gone()
    phase2_prompted = pq_phase2(unit, bundle, up)
    return InstallReport(prompted, served, phase2_prompted)


def legacy_install(
    unit: Unit, ctx: TrezorTestContext, data: bytes, *, confirm: bool = True
) -> bool:
    """A legacy (vendor-header) image through a legacy bootloader. Returns
    whether the bootloader asked for confirmation."""
    assert ctx.features.bootloader_mode, "legacy_install starts in bootloader mode"
    session = ctx.get_seedless_session()

    def upload(tick: t.Callable[[], None]) -> None:
        # The legacy bootloader confirms after it has read the headers, i.e.
        # in the middle of the stream, so the whole exchange is watched.
        resp = session.call(messages.FirmwareErase(length=len(data)))
        tick()
        firmware._stream_firmware_upload(session, data, resp, lambda _: tick())

    _, prompted = run_watching_stalls(
        ctx,
        upload,
        stall=unit.stall,
        confirm=confirm,
        on_prompt=lambda: unit.step("legacy install: confirmation, tapping confirm"),
    )
    unit.step("legacy install: firmware streamed", screenshot=False)
    close(ctx)
    unit.wait_gone()
    return prompted


#: vendor string the bootloader reports per variant (fw_check_pq.c)
VENDOR = {
    "universal": "Trezor",
    "btc-only": "Trezor Bitcoin-only",
    "custom": "UNSAFE, DO NOT USE!",
}


def wipe_in_bootloader(unit: Unit, ctx: TrezorTestContext) -> TrezorTestContext:
    """Host WipeDevice in the bootloader, confirmed on the device; returns the
    bootloader it comes back to."""
    session = ctx.get_seedless_session()
    resp, _ = call_watching_prompt(
        ctx,
        lambda: session.call(messages.WipeDevice()),
        stall=unit.stall,
        on_prompt=lambda: unit.step("bootloader wipe: confirmation, tapping confirm"),
    )
    messages.Success.ensure_isinstance(resp)
    unit.step("bootloader wipe done", screenshot=False)
    close(ctx)
    unit.wait_gone()
    return unit.context(bootloader=True, timeout=REBOOT)


def _connect_any(unit: Unit, deadline: float) -> TrezorTestContext:
    """A connection in whatever mode the unit is in. A bootloader sitting on
    its intro ("Initiate connection") is enumerated with the wire down until
    tapped; one that stays like that for INTRO_SILENCE seconds is tapped (only
    if debuglink shows that screen)."""
    silent_since: float | None = None
    screens = _WaitScreens(unit, "waiting for the unit")
    while time.monotonic() < deadline:
        try:
            return unit.context(bootloader=None, timeout=10)
        except UnitError:
            pass
        screens.tick()
        now = time.monotonic()
        if not unit.present():
            silent_since = None  # still rebooting, or pushing the nRF
        elif silent_since is None:
            silent_since = now
        elif now - silent_since > INTRO_SILENCE:
            tap_bootloader_intro(unit, timeout=30, bootloader_only=True)
            silent_since = None
    unit.step("unit not reachable over USB in time")
    raise UnitError("unit not reachable over USB in time")


def reach_bootloader(unit: Unit, timeout: float = PHASE2_RESUME) -> TrezorTestContext:
    """Wherever a refusal or a cut left the unit: its bootloader, on USB. A
    unit back in firmware is rebooted into the bootloader."""
    ctx = _connect_any(unit, time.monotonic() + timeout)
    if ctx.features.bootloader_mode:
        unit.step("recovery: in the bootloader")
        return ctx
    unit.step("recovery: back in firmware, rebooting to the bootloader")
    return enter_bootloader(unit, ctx)


def wait_pq_bootloader(unit: Unit, timeout: float = 2 * REBOOT) -> TrezorTestContext:
    """The PQ bootloader, as opposed to the legacy one: both report
    bootloader_mode, only one reports the Merkle-tree scheme. A firmware on
    the way (the intermediary doing its swap) is left alone; a PQ bootloader
    that comes up on its intro (after a cut, with no boot command telling it
    to connect) is tapped."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ctx = _connect_any(unit, deadline)
        f = ctx.features
        if f.bootloader_mode and f.firmware_scheme == FirmwareScheme.PqSecure:
            return ctx
        close(ctx)
        time.sleep(2)
    raise UnitError(f"no PQ bootloader within {timeout:.0f} s")


def version(features: messages.Features) -> tuple[int, int, int]:
    return (features.major_version, features.minor_version, features.patch_version)
