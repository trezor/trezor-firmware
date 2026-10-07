"""Power loss at chosen points of an install, made by an SWD reset at a named
function (pqhw/cutpoint.py). The pass criterion is the plan's common one: no
SWD needed to recover, the same release re-run over USB completes, and the
seed survives (the variant is unchanged throughout).

PL-05 (during the boardloader's copy: needs a real power cut) and PL-09
(cable pulled) are not automated.
"""

from __future__ import annotations

import threading
import time

import pytest
from pqhw import cutpoint, flows
from pqhw.cutpoint import CutPoint
from pqhw.device import Unit
from pqhw.fixtures import Fixtures

pytestmark = [pytest.mark.hw, pytest.mark.cut]

OLD, NEW = "release-A", "release-B"
OLD_BL, NEW_BL = (2, 1, 19), (2, 1, 20)
NEW_FW = (2, 14, 1)
#: seconds into the nRF push (271 KB over UART, ~30 s) for the "during" cuts
PUSH_DELAY = 5.0


def start(unit: Unit, fx: Fixtures):
    """A seeded unit on A, in its bootloader, about to take B: B replaces the
    bootloader code and the nRF, so every phase-1 step runs."""
    ctx = flows.baseline_pq_installed(unit, fx, OLD, "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    return flows.enter_bootloader(unit, ctx), seed, fx.bundle(NEW, "universal")


def finish(unit: Unit, fx: Fixtures, seed, bootloader: tuple[int, int, int]):
    """Recover over USB alone and check where the cut left the unit: which
    bootloader runs, then the honest install of B completes with the seed."""
    ctx = flows.reach_bootloader(unit)
    assert flows.version(ctx.features) == bootloader, "bootloader after the cut"
    report = flows.pq_install(unit, ctx, fx.bundle(NEW, "universal"))
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == NEW_FW
    assert flows.seed_fingerprint(unit, ctx) == seed
    return report


@pytest.mark.parametrize(
    "symbol, mode",
    [
        ("ucb_stage_verify", "before"),  # PL-01
        ("nrf_staging_write_desc", "before"),  # PL-02
        ("ucb_stage_arm", "before"),  # PL-03
    ],
)
def test_cut_in_phase1_before_arming(
    unit: Unit, fx: Fixtures, symbol: str, mode: str
) -> None:
    """PL-01..03: cut before the UCB is armed: the old bootloader stays, any
    partial staging is discarded, the install starts over."""
    ctx, seed, bundle = start(unit, fx)
    cut = CutPoint(fx.release_elf(OLD), symbol, mode)
    unit.step(f"cut armed: {cut}", screenshot=False)
    res = cutpoint.cut_during(cut, lambda: flows.pq_phase1(unit, ctx, bundle))
    assert res.hit, f"phase 1 never reached {symbol}"
    unit.step(f"cut fired: {cut}; {res.ucb_summary()}")
    finish(unit, fx, seed, OLD_BL)


def test_cut_after_arming(unit: Unit, fx: Fixtures) -> None:
    """PL-04: cut once the UCB is armed, before the reboot: the boardloader
    installs B's bootloader anyway, so the re-run is header-only."""
    ctx, seed, bundle = start(unit, fx)
    cut = CutPoint(fx.release_elf(OLD), "ucb_stage_arm", "after")
    unit.step(f"cut armed: {cut}", screenshot=False)
    res = cutpoint.cut_during(cut, lambda: flows.pq_phase1(unit, ctx, bundle))
    assert res.hit
    unit.step(f"cut fired: {cut}; {res.ucb_summary()}")
    report = finish(unit, fx, seed, NEW_BL)
    assert report.served["code"] == 0, "B's bootloader was already in place"


def phase1_then_arm(unit: Unit, ctx, bundle, cut: CutPoint) -> cutpoint.Armed:
    """Phase 1 of A -> B to completion, then arm `cut` in B's bootloader once
    A's has stopped (the same address means other code in A)."""
    flows.pq_phase1(unit, ctx, bundle)
    flows.close(ctx)
    unit.wait_gone()
    armed = cutpoint.arm(cut)
    unit.step(f"cut armed: {cut}", screenshot=False)
    return armed


@pytest.mark.parametrize(
    "symbol, mode, delay",
    [
        ("nrf_update_with_progress", "during", PUSH_DELAY),  # PL-06
        ("nrf_staging_clear", "before", 0.0),  # PL-07
    ],
)
def test_cut_around_nrf_push(
    unit: Unit, fx: Fixtures, symbol: str, mode: str, delay: float
) -> None:
    """PL-06: cut mid-push: the resume driver pushes again and converges.
    PL-07: cut after the push, before the staging is cleared: the live hash
    matches, so the next boot skips and clears. Either way the re-run finds the
    nRF current."""
    ctx, seed, bundle = start(unit, fx)
    cut = CutPoint(fx.release_elf(NEW), symbol, mode, delay)
    with phase1_then_arm(unit, ctx, bundle, cut) as armed:
        assert armed.wait(), f"B's bootloader never reached {symbol}"
    unit.step(f"cut fired: {cut}; {cutpoint.ucb_summary(armed)}")
    report = finish(unit, fx, seed, NEW_BL)
    assert report.served["nrf"] == 0, "the nRF was not brought current on its own"


def test_cut_mid_phase2(unit: Unit, fx: Fixtures) -> None:
    """PL-08: reset while the firmware streams: back in the bootloader with
    B's header, and the re-run completes."""
    ctx, seed, bundle = start(unit, fx)
    flows.pq_phase1(unit, ctx, bundle)
    flows.close(ctx)
    unit.wait_gone()
    phase1_usb = unit._connected
    streaming = threading.Thread(
        target=lambda: _ignore(lambda: flows.pq_phase2(unit, bundle)), daemon=True
    )
    streaming.start()
    # wait for the stream to be under way: PHASE2_RESUME covers the nRF push
    _wait_streaming(unit, phase1_usb, timeout=flows.PHASE2_RESUME)
    unit.reset()
    unit.step("cut: SWD reset mid phase 2")
    streaming.join(60)
    report = finish(unit, fx, seed, NEW_BL)
    assert report.served["code"] == 0


def _ignore(fn) -> None:
    try:
        fn()
    except BaseException:
        pass


def _wait_streaming(unit: Unit, phase1_usb, timeout: float) -> None:
    """Until phase 2 has connected (a new USB identity), plus a few seconds of
    the stream."""
    deadline = time.monotonic() + timeout
    while unit._connected == phase1_usb:
        if time.monotonic() > deadline:
            raise AssertionError("phase 2 never connected")
        time.sleep(0.5)
    time.sleep(8)


# --- migration (intermediary) -------------------------------------------------


def legacy_to_intermediary(unit: Unit, fx: Fixtures, variant: str):
    """Seeded legacy unit, intermediary streamed through the legacy bootloader;
    returns the baseline seed once the unit reboots into the intermediary."""
    ctx = flows.baseline_legacy(unit, fx, variant)
    flows.load_seed(unit, ctx)
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    flows.legacy_install(unit, ctx, fx.intermediary(variant).read_bytes())
    return seed


def migration_finishes(unit: Unit, fx: Fixtures, variant: str, seed) -> None:
    """MG-04: wherever the cut landed, the unit ends in the PQ bootloader and
    release A brings the seed back."""
    ctx = flows.wait_pq_bootloader(unit)
    assert flows.version(ctx.features) == OLD_BL
    flows.pq_install(unit, ctx, fx.bundle(OLD, variant))
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(unit, ctx) == seed


@pytest.mark.parametrize(
    "part, symbol, mode, delay",
    [
        ("kernel", "nrf_update", "during", PUSH_DELAY),  # MG-12
        ("secmon", "boot_image_replace", "before", 0.0),  # MG-13
        ("secmon", "boot_ucb_write", "after", 0.0),  # MG-14
    ],
    ids=["MG-12-nrf-push", "MG-13-before-replace", "MG-14-ucb-armed"],
)
def test_cut_in_intermediary_swap(
    unit: Unit, fx: Fixtures, part: str, symbol: str, mode: str, delay: float
) -> None:
    """MG-12..14: the intermediary's swap cut at each step; the next boot picks
    it up (re-push, re-replace, or the boardloader finishing) and the
    migration completes with the seed."""
    variant = "universal"
    seed = legacy_to_intermediary(unit, fx, variant)
    # armed after the legacy bootloader has stopped running the old image
    cut = CutPoint(fx.intermediary_elf(variant, part), symbol, mode, delay)
    with cutpoint.arm(cut) as armed:
        unit.step(f"cut armed: {cut}", screenshot=False)
        hit = armed.wait()
    if not hit and symbol == "nrf_update":
        pytest.skip("the intermediary found the nRF current: no push to cut")
    assert hit, f"the intermediary never reached {symbol}"
    unit.step(f"cut fired: {cut}; {cutpoint.ucb_summary(armed)}")
    migration_finishes(unit, fx, variant, seed)


def test_cut_in_pq_bootloader_before_firmware(unit: Unit, fx: Fixtures) -> None:
    """MG-15: power lost with the PQ bootloader in place and no firmware yet:
    it comes back to the PQ bootloader, and the release keeps the seed."""
    variant = "universal"
    seed = legacy_to_intermediary(unit, fx, variant)
    ctx = flows.wait_pq_bootloader(unit)
    flows.close(ctx)
    unit.reset()
    unit.step("cut: SWD reset in the PQ bootloader")
    migration_finishes(unit, fx, variant, seed)
