"""Multi-step operations the tests compose: baselines, installs, seed checks."""

from __future__ import annotations

import logging
import time
import typing as t
from dataclasses import dataclass
from hashlib import blake2s, sha256

from trezorlib import btc, debuglink, device, firmware, messages
from trezorlib.debuglink import TrezorTestContext
from trezorlib.firmware.pq_secure import PqSecureBundle
from trezorlib.messages import FirmwareScheme
from trezorlib.tools import parse_path

from .device import Unit, UnitError, call_watching_prompt, close
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


# --- seed -------------------------------------------------------------------


PIN = "1234"
WIPE_CODE = "9876"


def load_seed(ctx: TrezorTestContext, pin: str | None = None) -> None:
    """Without a PIN unless asked: a T3W1 is not on USB until its boot
    lockscreen is unlocked, so a PIN at boot needs a person. The storage salt
    binds firmware_type with or without a PIN, so a wrong domain still loses
    the seed."""
    session = ctx.get_seedless_session()
    debuglink.load_device(
        session, MNEMONIC, pin=pin, passphrase_protection=False, label=LABEL
    )


def seed_fingerprint(ctx: TrezorTestContext) -> str | None:
    """The account xpub, or None on an uninitialised device."""
    features = ctx.refresh_features()
    if not features.initialized:
        return None
    session = ctx.get_session(passphrase="")
    node = btc.get_public_node(session, parse_path(XPUB_PATH), coin_name="Bitcoin")
    return node.xpub


# --- baselines ----------------------------------------------------------------


def baseline_legacy(unit: Unit, fx: Fixtures, variant: str) -> TrezorTestContext:
    """Pre-migration state: legacy boardloader, bootloader and firmware."""
    unit.erase()
    unit.flash("boardloader", fx.legacy("boardloader"))
    unit.flash("bootloader", fx.legacy("bootloader"))
    unit.flash("firmware", fx.legacy(variant))
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
        load_seed(ctx)
    return ctx


# --- installs -------------------------------------------------------------------


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
) -> TrezorTestContext:
    """From firmware mode; with `bundle`, as a pre-authorised (interaction-less)
    upgrade the firmware confirms itself."""
    session = ctx.get_session(passphrase="")
    if bundle is None:
        device.reboot_to_bootloader(session)
    else:
        device.reboot_to_bootloader(
            session,
            boot_command=messages.BootCommand.INSTALL_UPGRADE,
            firmware_preamble=bundle.consent_preamble(),
        )
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
) -> tuple[bool, dict[str, int]]:
    """FirmwareBegin and whatever code or nRF image the device pulls; returns
    (prompted, bytes served per image). The device then reboots."""
    assert ctx.features.bootloader_mode, "phase 1 starts in bootloader mode"
    nrf = bundle.nrf if send_nrf else None
    session = ctx.get_seedless_session()
    code = bundle.bootloader_code

    def begin() -> messages.FirmwareRequest | messages.Success:
        return session.call(
            messages.FirmwareBegin(
                boot_header=bundle.boot_header,
                module_headers=bundle.firmware.manifest_region,
                code_length=len(code),
                code_hash=sha256(code).digest(),
                nrf_length=len(nrf.image) if nrf else None,
                nrf_co_path=nrf.co_path if nrf else None,
                nrf_image_hash=nrf.image_hash if nrf else None,
            )
        )

    resp, prompted = call_watching_prompt(ctx, begin, stall=unit.stall, confirm=confirm)
    served = {"code": 0, "nrf": 0}
    while isinstance(resp, messages.FirmwareRequest):
        is_nrf = (resp.coprocessor_index or 0) != 0
        src = nrf.image if (is_nrf and nrf) else code
        payload = src[resp.offset : resp.offset + resp.length]
        resp = session.call(
            messages.FirmwareUpload(payload=payload, hash=blake2s(payload).digest())
        )
        served["nrf" if is_nrf else "code"] += len(payload)
    messages.Success.ensure_isinstance(resp)
    LOG.info("phase 1 done: prompted=%s served=%s", prompted, served)
    return prompted, served


def pq_phase2(unit: Unit, bundle: PqSecureBundle) -> bool:
    """After phase 1's reboot: stream the firmware. Returns whether it needed a
    person, which it never should: the bootloader is meant to resume on its own
    (BOOT_COMMAND_CONTINUE_UPGRADE) with the wire up."""
    needed_person = False
    try:
        ctx = unit.context(bootloader=True, timeout=PHASE2_RESUME)
    except UnitError:
        # Not on USB: the bootloader is on its intro ("Initiate connection"),
        # which brings the wire up only after a tap -- it did not resume.
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
    data = bundle.firmware.data

    def erase() -> t.Any:
        return session.call(messages.FirmwareErase(length=len(data)))

    resp, prompted = call_watching_prompt(ctx, erase, stall=unit.stall, confirm=False)
    firmware._stream_firmware_upload(
        session, data, resp, lambda _: None, bundle.chunk_prev_hashes()
    )
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
) -> InstallReport:
    """Both phases from bootloader mode, ending with the device rebooting into
    the new firmware. A refused install raises the device's TrezorFailure."""
    prompted, served = pq_phase1(unit, ctx, bundle, confirm=confirm, send_nrf=send_nrf)
    close(ctx)
    unit.wait_gone()
    phase2_prompted = pq_phase2(unit, bundle)
    return InstallReport(prompted, served, phase2_prompted)


def legacy_install(
    unit: Unit, ctx: TrezorTestContext, data: bytes, *, confirm: bool = True
) -> bool:
    """A legacy (vendor-header) image through a legacy bootloader. Returns
    whether the bootloader asked for confirmation."""
    assert ctx.features.bootloader_mode, "legacy_install starts in bootloader mode"
    session = ctx.get_seedless_session()

    def erase() -> t.Any:
        return session.call(messages.FirmwareErase(length=len(data)))

    resp, prompted = call_watching_prompt(ctx, erase, stall=unit.stall, confirm=confirm)
    firmware._stream_firmware_upload(session, data, resp, lambda _: None)
    close(ctx)
    unit.wait_gone()
    return prompted


def wait_pq_bootloader(unit: Unit, timeout: float = 2 * REBOOT) -> TrezorTestContext:
    """The PQ bootloader, as opposed to the legacy one: both report
    bootloader_mode, only one reports the Merkle-tree scheme."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ctx = unit.context(
            bootloader=True, timeout=max(1.0, deadline - time.monotonic())
        )
        if ctx.features.firmware_scheme == FirmwareScheme.PqSecure:
            return ctx
        close(ctx)
        time.sleep(2)
    raise UnitError(f"no PQ bootloader within {timeout:.0f} s")


def version(features: messages.Features) -> tuple[int, int, int]:
    return (features.major_version, features.minor_version, features.patch_version)
