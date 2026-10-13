"""Two-phase installs on a PQ unit: empty-device, upgrade, downgrade, variant
change, interaction-less upgrade. Plan cases in the docstrings."""

from __future__ import annotations

import threading

import pytest
from pqhw import flows
from pqhw.device import Unit, UnitError
from pqhw.fixtures import VARIANTS, Fixtures

from trezorlib import exceptions
from trezorlib.messages import Capability, FirmwareScheme

pytestmark = pytest.mark.hw


@pytest.mark.parametrize("variant", VARIANTS)
def test_empty_unit_takes_official_without_prompt(
    unit: Unit, fx: Fixtures, variant: str
) -> None:
    """On a factory-fresh unit, an official firmware (universal or btc-only)
    installs with no confirm screen, so the factory flow needs no person.
    The firmware then reports its own version and capabilities, and the
    bootloader names its vendor. [BT-01, BT-05, VR-06, IN-11]"""
    ctx = flows.baseline_pq_empty(unit, fx, "release-A")
    f = ctx.features
    assert f.firmware_scheme == FirmwareScheme.PqSecure
    assert flows.version(f) == (2, 1, 19)
    assert not f.firmware_present
    assert not f.firmware_corrupted

    bundle = fx.bundle("release-A", variant)
    report = flows.pq_install(unit, ctx, bundle)
    assert not report.prompted
    assert not report.phase2_prompted
    assert report.served["code"] == 0, "the flashed bootloader is A's, header-only"

    ctx = flows.wait_firmware(unit)
    f = ctx.features
    assert flows.version(f) == bundle.firmware.manifest.firmware_version[:3]
    assert not f.initialized
    assert f.firmware_scheme == FirmwareScheme.PqSecure
    assert Capability.Bitcoin in f.capabilities
    assert (Capability.Ethereum in f.capabilities) == (variant == "universal")

    ctx = flows.enter_bootloader(unit, ctx)
    f = ctx.features
    assert f.fw_vendor == flows.VENDOR[variant]
    assert f.firmware_present and not f.firmware_corrupted


def test_custom_on_empty_unit(unit: Unit, fx: Fixtures) -> None:
    """Custom (unofficial) firmware on a fresh unit: a locked bootloader
    refuses it; an unlocked one installs it only after a confirm and flags
    it as unsafe at boot. [IN-11, IN-12]"""
    ctx = flows.baseline_pq_empty(unit, fx, "release-A")
    bundle = fx.bundle("release-A", "custom")
    if ctx.features.bootloader_locked:
        with pytest.raises(exceptions.TrezorFailure, match="Unlock the bootloader"):
            flows.pq_install(unit, ctx, bundle, confirm=False)
        return
    report = flows.pq_install(unit, ctx, bundle)
    assert report.prompted
    # Unofficial firmware is held at the bootloader's unsafe-firmware warning
    # until a person confirms it, so it does not come up on USB by itself.
    try:
        ctx = unit.context(bootloader=False, timeout=60)
    except UnitError:
        unit.step("custom firmware held at the boot warning (needs a person)")
        return
    assert flows.version(ctx.features) == (2, 14, 0)
    ctx = flows.enter_bootloader(unit, ctx)
    assert ctx.features.fw_vendor == flows.VENDOR["custom"]


def test_reinstall_is_header_only(unit: Unit, fx: Fixtures) -> None:
    """Installs the release the unit already runs: neither the bootloader code
    nor the nRF image is sent again, and the seed is kept."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.served == {"code": 0, "nrf": 0}
    ctx = flows.wait_firmware(unit)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_upgrade_streams_bootloader_and_nrf(unit: Unit, fx: Fixtures) -> None:
    """Upgrades A to B: the new bootloader code and the new nRF image are both
    installed, the firmware reports B's version, and the seed is kept.
    [IN-02, NR-01, FW-01]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    assert seed is not None

    bundle = fx.bundle("release-B", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, bundle)
    assert report.prompted, "a non-empty unit confirms a bootloader-mode install"
    assert report.served["code"] == len(bundle.bootloader_code)
    assert bundle.nrf is not None
    assert report.served["nrf"] == len(bundle.nrf.image)

    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 1)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_failed_nrf_push_resumes_install(unit: Unit, fx: Fixtures) -> None:
    """Makes the nRF push of an A-to-B upgrade fail, by halting the nRF over
    J-Link while it runs MCUboot: the bootloader shows the failure, reboots,
    pushes again and must then resume phase 2 on its own (no tap, no host
    restart), ending on B with the seed kept. [KB-12]"""
    if not unit.nrf_jlink:
        pytest.skip("needs --nrf-jlink to stall the nRF")
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    assert seed is not None

    bundle = fx.bundle("release-B", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    up = flows.Upload.of(bundle)
    flows.pq_phase1(unit, ctx, bundle, upload=up)
    flows.close(ctx)

    stalled = {}
    staller = threading.Thread(
        target=lambda: stalled.setdefault("caught", unit.stall_nrf_push()),
        daemon=True,
    )
    staller.start()
    unit.wait_gone()
    needed_person = flows.pq_phase2(unit, bundle, up)
    staller.join(120)
    assert stalled.get("caught"), "the nRF was never caught in MCUboot"
    # The RSOD texts are readable over SWD only on bootloaders that keep them
    # in the boot arguments; others show the RSOD from a local copy.
    rsod = unit.last_rsod
    assert rsod is None or "nRF" in rsod["title"] + rsod["message"], (
        f"the stalled push failed with an unexpected error: {rsod}"
    )
    assert not needed_person, "phase 2 did not resume on its own"

    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 1)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_downgrade_keeps_seed(unit: Unit, fx: Fixtures) -> None:
    """Downgrades B to A from the bootloader: allowed after a confirm, since no
    version floor forbids it, and the seed is kept. [VR-05]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.prompted
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 0)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_variant_change_wipes(unit: Unit, fx: Fixtures) -> None:
    """Switches a seeded universal unit to btc-only firmware: a different
    storage domain, so the confirm warns and the seed is erased. [IN-10]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "btc-only"))
    assert report.prompted, "the seed-erase warning is on the confirm screen"
    ctx = flows.wait_firmware(unit)
    assert flows.seed_fingerprint(unit, ctx) is None


def test_interaction_less_upgrade(unit: Unit, fx: Fixtures) -> None:
    """Upgrade approved in the firmware: after the firmware's own confirm, the
    bootloader installs B without asking again, and the seed is kept.
    [IL-01]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    bundle = fx.bundle("release-B", "universal")
    ctx = flows.enter_bootloader(unit, ctx, bundle=bundle)
    report = flows.pq_install(unit, ctx, bundle, confirm=False)
    assert not report.prompted
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 1)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_interaction_less_refuses_other_release(unit: Unit, fx: Fixtures) -> None:
    """Approval given in the firmware for B universal must not cover B btc-
    only: the bootloader refuses it. [IL-02]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx, bundle=fx.bundle("release-B", "universal"))
    with pytest.raises(exceptions.TrezorFailure, match="Firmware mismatch"):
        flows.pq_install(unit, ctx, fx.bundle("release-B", "btc-only"), confirm=False)
