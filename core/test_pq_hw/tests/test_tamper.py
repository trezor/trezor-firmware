"""The wire tamper matrix: genuine releases with one fault, each refused with
its own message, and the unit recoverable afterwards (the honest install
completes and the seed survives). Cases and messages live in pqhw/tamper.py.

Plan: IN-03 (bl-sig, wrong-model, fw-sig), IN-05 (nothing erased before the
signature check), IN-06 (per-chunk), IN-07 (variant-swap), IN-08 (bare phase
2), IN-13 (no-nrf), IN-14 (custom layout), IL-02 (preamble, vendor), NR-03.
"""

from __future__ import annotations

import pytest
from pqhw import flows, tamper
from pqhw.device import Unit
from pqhw.fixtures import Fixtures

from trezorlib import exceptions, messages

pytestmark = pytest.mark.hw

RELEASE = "release-A"
INSTALLED = (2, 14, 0)


def seeded_unit(unit: Unit, fx: Fixtures):
    ctx = flows.baseline_pq_installed(unit, fx, RELEASE, "universal")
    return ctx, flows.seed_fingerprint(unit, ctx)


def assert_untouched(unit: Unit, ctx, seed: str | None) -> None:
    """IN-05: a refusal before the confirm changed nothing; the unit boots its
    firmware with its seed."""
    flows.close(ctx)
    unit.reset()
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == INSTALLED
    assert flows.seed_fingerprint(unit, ctx) == seed


def assert_recovers(unit: Unit, fx: Fixtures, seed: str | None) -> None:
    """After a phase-2 refusal: the honest install completes and, the variant
    being unchanged, the seed is still there."""
    ctx = flows.reach_bootloader(unit)
    flows.pq_install(unit, ctx, fx.bundle(RELEASE, "universal"))
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == INSTALLED
    assert flows.seed_fingerprint(unit, ctx) == seed


@pytest.mark.parametrize("case", tamper.PHASE1, ids=lambda c: c.name)
def test_phase1_refused(unit: Unit, fx: Fixtures, case: tamper.Tamper) -> None:
    """Sends a genuine release with one field corrupted before installation
    starts (signature, model, manifest, nRF data or custom layout): the
    bootloader must refuse it before any confirm screen and leave the unit
    untouched. [IN-03, IN-05, IN-13, IN-14, NR-03]"""
    ctx, seed = seeded_unit(unit, fx)
    bundle = fx.bundle(RELEASE, case.variant)
    upload = case.alter(flows.Upload.of(bundle), bundle)
    ctx = flows.enter_bootloader(unit, ctx)
    unit.step(f"tamper {case.name}: {case.what}", screenshot=False)
    with pytest.raises(exceptions.TrezorFailure, match=case.expect):
        # confirm=False makes an unexpected confirm screen fail the test
        flows.pq_install(
            unit, ctx, bundle, confirm=not case.before_confirm, upload=upload
        )
    if case.before_confirm:
        assert_untouched(unit, ctx, seed)
    else:
        # refused after the staging reused part of the firmware area: the
        # firmware is gone, the honest install brings it back with the seed
        flows.close(ctx)
        assert_recovers(unit, fx, seed)


@pytest.mark.parametrize("case", tamper.PHASE2, ids=lambda c: c.name)
def test_phase2_refused(unit: Unit, fx: Fixtures, case: tamper.Tamper) -> None:
    """Corrupts the firmware stream after installation has started (a flipped
    byte, wrong or missing chunk hashes): the bootloader must refuse it, and
    the honest install must then complete with the seed. [IN-06]"""
    ctx, seed = seeded_unit(unit, fx)
    bundle = fx.bundle(RELEASE, "universal")
    upload = case.alter(flows.Upload.of(bundle), bundle)
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_phase1(unit, ctx, bundle)
    flows.close(ctx)
    unit.wait_gone()
    unit.step(f"tamper {case.name}: {case.what}", screenshot=False)
    with pytest.raises(exceptions.TrezorFailure, match=case.expect):
        flows.pq_phase2(unit, bundle, upload)
    assert_recovers(unit, fx, seed)


def test_variant_swap_refused(unit: Unit, fx: Fixtures) -> None:
    """Approves universal in the first phase, then streams btc-only firmware:
    the bootloader must refuse it, and the honest install must then
    complete. [IN-07]"""
    ctx, seed = seeded_unit(unit, fx)
    bundle = fx.bundle(RELEASE, "universal")
    upload = tamper.variant_swap(
        flows.Upload.of(bundle), fx.bundle(RELEASE, "btc-only")
    )
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_phase1(unit, ctx, bundle)
    flows.close(ctx)
    unit.wait_gone()
    unit.step("tamper variant-swap: phase 2 streams btc-only", screenshot=False)
    with pytest.raises(exceptions.TrezorFailure, match=tamper.VARIANT_SWAP):
        flows.pq_phase2(unit, bundle, upload)
    assert_recovers(unit, fx, seed)


def test_bare_phase2_refused(unit: Unit, fx: Fixtures) -> None:
    """Streams firmware without the first phase: the bootloader must refuse it
    and erase nothing. This is also the only way to offer a legacy image to
    the PQ bootloader. [IN-08, MG-19]"""
    ctx, seed = seeded_unit(unit, fx)
    ctx = flows.enter_bootloader(unit, ctx)
    data = fx.bundle(RELEASE, "universal").firmware.data
    session = ctx.get_seedless_session()
    unit.step(
        "tamper bare-phase-2: FirmwareErase with no FirmwareBegin", screenshot=False
    )
    with pytest.raises(exceptions.TrezorFailure, match=tamper.BARE_PHASE2):
        session.call(messages.FirmwareErase(length=len(data)))
    unit.step("phase 2 refused")
    assert_untouched(unit, ctx, seed)


@pytest.mark.parametrize("kind", ["bad-preamble", "vendor-change"])
def test_consent_preamble_refused_in_firmware(
    unit: Unit, fx: Fixtures, kind: str
) -> None:
    """Asks the firmware to pre-approve an upgrade it cannot parse, or one for
    another vendor's variant: the firmware must refuse and keep running.
    [IL-02]"""
    ctx, seed = seeded_unit(unit, fx)
    bundle = fx.bundle("release-B", "universal")
    if kind == "bad-preamble":
        preamble, expect = tamper.truncated_preamble(bundle), tamper.BAD_PREAMBLE
    else:
        other = fx.bundle("release-B", "btc-only")
        preamble = tamper.other_vendor_preamble(bundle, other)
        expect = tamper.VENDOR_CHANGE
    with pytest.raises(exceptions.TrezorFailure, match=expect):
        flows.enter_bootloader(unit, ctx, bundle=bundle, preamble=preamble)
    ctx.refresh_features()
    assert not ctx.features.bootloader_mode
    assert flows.version(ctx.features) == INSTALLED
    assert flows.seed_fingerprint(unit, ctx) == seed
