"""Two-phase installs on a PQ unit: empty-device, upgrade, downgrade, variant
change, interaction-less upgrade. Plan cases in the docstrings."""

from __future__ import annotations

import pytest
from pqhw import flows
from pqhw.device import Unit
from pqhw.fixtures import VARIANTS, Fixtures

from trezorlib import exceptions
from trezorlib.messages import FirmwareScheme

pytestmark = pytest.mark.hw


@pytest.mark.parametrize("variant", VARIANTS)
def test_empty_unit_takes_official_without_prompt(
    unit: Unit, fx: Fixtures, variant: str
) -> None:
    """BT-05, IN-11 (official half): an empty unit reads empty and installs an
    official variant with no prompt, so the factory flow stays unattended."""
    ctx = flows.baseline_pq_empty(unit, fx, "release-A")
    f = ctx.features
    assert f.firmware_scheme == FirmwareScheme.PqSecure
    assert flows.version(f) == (2, 1, 19)
    assert not f.firmware_present
    assert not f.firmware_corrupted

    report = flows.pq_install(unit, ctx, fx.bundle("release-A", variant))
    assert not report.prompted
    assert not report.phase2_prompted
    assert report.served["code"] == 0, "the flashed bootloader is A's, header-only"

    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 0)
    assert not ctx.features.initialized


def test_empty_unit_asks_before_custom(unit: Unit, fx: Fixtures) -> None:
    """IN-11 (custom half): empty does not mean unattended for unofficial code."""
    ctx = flows.baseline_pq_empty(unit, fx, "release-A")
    try:
        report = flows.pq_install(unit, ctx, fx.bundle("release-A", "custom"))
    except exceptions.TrezorFailure as e:
        if "restrict" in str(e).lower():
            pytest.skip(f"bootloader is locked on this unit: {e}")
        raise
    assert report.prompted


def test_reinstall_is_header_only(unit: Unit, fx: Fixtures) -> None:
    """The same release again: no bootloader code and no nRF image streamed."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.served == {"code": 0, "nrf": 0}
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(ctx) == seed


def test_upgrade_streams_bootloader_and_nrf(unit: Unit, fx: Fixtures) -> None:
    """IN-02, NR-01, FW-01: A -> B replaces the bootloader code (rebuilt, so it
    does not conform) and pushes nRF 1.0.1 -> 1.1.3; the seed survives."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(ctx)
    assert seed is not None

    bundle = fx.bundle("release-B", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, bundle)
    assert report.prompted, "a non-empty unit confirms a bootloader-mode install"
    assert report.served["code"] == len(bundle.bootloader_code)
    assert bundle.nrf is not None
    assert report.served["nrf"] == len(bundle.nrf.image)

    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 1)
    assert flows.seed_fingerprint(ctx) == seed


def test_downgrade_keeps_seed(unit: Unit, fx: Fixtures) -> None:
    """VR-05: B -> A is allowed after a confirm, below no floor, seed kept."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B", "universal")
    seed = flows.seed_fingerprint(ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.prompted
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 0)
    assert flows.seed_fingerprint(ctx) == seed


def test_variant_change_wipes(unit: Unit, fx: Fixtures) -> None:
    """IN-10: universal -> btc-only is a different storage domain."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "btc-only"))
    assert report.prompted, "the seed-erase warning is on the confirm screen"
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(ctx) is None


def test_interaction_less_upgrade(unit: Unit, fx: Fixtures) -> None:
    """IL-01: confirmed in firmware, installed by the bootloader without asking."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(ctx)
    bundle = fx.bundle("release-B", "universal")
    ctx = flows.enter_bootloader(unit, ctx, bundle=bundle)
    report = flows.pq_install(unit, ctx, bundle, confirm=False)
    assert not report.prompted
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 1)
    assert flows.seed_fingerprint(ctx) == seed


def test_interaction_less_refuses_other_release(unit: Unit, fx: Fixtures) -> None:
    """IL-02 consent-mismatch: consent for B universal does not cover B btc-only."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx, bundle=fx.bundle("release-B", "universal"))
    with pytest.raises(exceptions.TrezorFailure, match="Firmware mismatch"):
        flows.pq_install(unit, ctx, fx.bundle("release-B", "btc-only"), confirm=False)
