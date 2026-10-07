"""Power loss at chosen points of an install, made by an SWD reset at a named
function (pqhw/cutpoint.py). The pass criterion is the plan's common one: no
SWD needed to recover, the same release re-run over USB completes, and the
seed survives (the variant is unchanged throughout).

PL-05 (during the boardloader's copy: needs a real power cut) and PL-09
(cable pulled) are not automated.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest
from pqhw import cutpoint, flows
from pqhw.cutpoint import CutPoint
from pqhw.device import Unit
from pqhw.fixtures import Fixtures

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_fixtures import check_elf_matches  # noqa: E402

pytestmark = [pytest.mark.hw, pytest.mark.cut]

OLD, NEW = "release-A", "release-B"
OLD_BL, NEW_BL = (2, 1, 19), (2, 1, 20)
NEW_FW = (2, 14, 1)
#: seconds into the nRF push (271 KB over UART, ~30 s) for the "during" cuts
PUSH_DELAY = 5.0


def code_watch(fx: Fixtures):
    """Where A's and B's bootloader code differ (their compiled-in version),
    read in place: which release's code is installed at each moment of a cut.
    Returns (watch, labels) for cutpoint."""
    a, b = fx.bundle(OLD, "universal"), fx.bundle(NEW, "universal")
    ca, cb = a.bootloader_code, b.bootloader_code
    d = next(i for i in range(len(ca)) if ca[i] != cb[i]) & ~3
    addr = cutpoint.BOOTLOADER + len(a.boot_header) + d
    return (
        {"bootloader": (addr, 8)},
        {"bootloader": {ca[d : d + 8]: "A", cb[d : d + 8]: "B"}},
    )


# The boardloader the suite flashes (built in the legacy worktree; not yet a
# staged fixture). Only used for tracing, after a check that it is that build.
BOARDLOADER_ELF = (
    (Path(__file__).resolve().parents[1])
    / "work/legacy/core/build-xtask/artifacts/T3W1/boardloader.elf"
)


def ucb_trace(fx: Fixtures) -> cutpoint.Trace:
    """Who reads and who writes the boot UCB during the boot after a cut: the
    boardloader's boot_ucb_read (its return says whether it will install) and
    any boot_ucb_write in A's bootloader (with the caller that armed it)."""
    trace: cutpoint.Trace = [
        ("A boot_ucb_write", fx.release_elf(OLD), "boot_ucb_write")
    ]
    if BOARDLOADER_ELF.exists():
        flashed = fx.legacy("boardloader").read_bytes()
        try:
            check_elf_matches(BOARDLOADER_ELF, flashed, "boot_ucb_read")
            trace.insert(
                0, ("boardloader boot_ucb_read", BOARDLOADER_ELF, "boot_ucb_read")
            )
        except Exception:
            pass
    return trace


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
        # Cut on the call instruction in the caller, not on the callee's
        # entry: see CutPoint.address.
        ("workflow_firmware_update_pq>ucb_stage_verify", "before"),  # PL-01
        ("nrf_on_finish>nrf_staging_write_desc", "before"),  # PL-02
        ("workflow_firmware_update_pq>ucb_stage_arm", "before"),  # PL-03
    ],
)
def test_cut_in_phase1_before_arming(
    unit: Unit, fx: Fixtures, symbol: str, mode: str
) -> None:
    """Simulates power loss at a point of the A to B install before the
    bootloader swap is committed: the old bootloader must stay, and re-
    running the install over USB must complete with the seed. [PL-01, PL-02,
    PL-03]"""
    ctx, seed, bundle = start(unit, fx)
    cut = CutPoint(fx.release_elf(OLD), symbol, mode)
    unit.step(f"cut armed: {cut}", screenshot=False)
    watch, labels = code_watch(fx)
    res = cutpoint.cut_during(
        cut,
        lambda: flows.pq_phase1(unit, ctx, bundle),
        watch=watch,
        trace=ucb_trace(fx),
    )
    assert res.hit, f"phase 1 never reached {symbol}"
    unit.step(f"cut fired: {cut}; {res.summary(labels)}")
    unit.step(cutpoint.calls_summary(res.armed), screenshot=False)
    caller = res.armed.hit_caller if res.armed else None
    unit.step(f"cut called from {caller}; {res.action_summary()}", screenshot=False)
    finish(unit, fx, seed, OLD_BL)


def test_cut_after_arming(unit: Unit, fx: Fixtures) -> None:
    """Simulates power loss just after the bootloader swap is committed: the
    boardloader must install B's bootloader on the next boot, and the re-run
    only needs the firmware. [PL-04]"""
    ctx, seed, bundle = start(unit, fx)
    cut = CutPoint(
        fx.release_elf(OLD), "workflow_firmware_update_pq>ucb_stage_arm", "after"
    )
    unit.step(f"cut armed: {cut}", screenshot=False)
    watch, labels = code_watch(fx)
    res = cutpoint.cut_during(
        cut,
        lambda: flows.pq_phase1(unit, ctx, bundle),
        watch=watch,
        trace=ucb_trace(fx),
    )
    assert res.hit
    unit.step(f"cut fired: {cut}; {res.summary(labels)}")
    unit.step(cutpoint.calls_summary(res.armed), screenshot=False)
    caller = res.armed.hit_caller if res.armed else None
    unit.step(f"cut called from {caller}; {res.action_summary()}", screenshot=False)
    report = finish(unit, fx, seed, NEW_BL)
    assert report.served["code"] == 0, "B's bootloader was already in place"


def phase1_then_arm(
    unit: Unit, ctx, bundle, cut: CutPoint, watch: cutpoint.Watch
) -> cutpoint.Armed:
    """Phase 1 of A -> B to completion, then arm `cut` in B's bootloader once
    A's has stopped (the same address means other code in A)."""
    flows.pq_phase1(unit, ctx, bundle)
    flows.close(ctx)
    unit.wait_gone()
    armed = cutpoint.arm(cut, watch=watch)
    unit.step(f"cut armed: {cut}", screenshot=False)
    return armed


@pytest.mark.parametrize(
    "symbol, mode, delay",
    [
        ("nrf_ota_resume_boot>nrf_update_with_progress", "during", PUSH_DELAY),  # PL-06
        ("nrf_ota_resume_boot>nrf_staging_clear", "before", 0.0),  # PL-07
    ],
)
def test_cut_around_nrf_push(
    unit: Unit, fx: Fixtures, symbol: str, mode: str, delay: float
) -> None:
    """Simulates power loss during, or right after, the nRF update on the first
    boot of B's bootloader: the next boot must bring the nRF up to date on
    its own. [PL-06, PL-07]"""
    ctx, seed, bundle = start(unit, fx)
    cut = CutPoint(fx.release_elf(NEW), symbol, mode, delay)
    watch, labels = code_watch(fx)
    with phase1_then_arm(unit, ctx, bundle, cut, watch) as armed:
        assert armed.wait(), f"B's bootloader never reached {symbol}"
    unit.step(f"cut fired: {cut}; {cutpoint.summary(armed, labels)}")
    report = finish(unit, fx, seed, NEW_BL)
    assert report.served["nrf"] == 0, "the nRF was not brought current on its own"


def test_cut_mid_phase2(unit: Unit, fx: Fixtures) -> None:
    """Resets the unit while the firmware is being streamed: it must come back
    in the bootloader, and the re-run must complete with the seed. [PL-08]"""
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
        ("kernel", "nrf_update__verified>nrf_update", "during", PUSH_DELAY),  # MG-12
        (
            "secmon",
            "boot_image_replace__verified>boot_image_replace",
            "before",
            0.0,
        ),  # MG-13
        ("secmon", "boot_image_replace>boot_ucb_write", "after", 0.0),  # MG-14
    ],
    ids=["MG-12-nrf-push", "MG-13-before-replace", "MG-14-ucb-armed"],
)
def test_cut_in_intermediary_swap(
    unit: Unit, fx: Fixtures, part: str, symbol: str, mode: str, delay: float
) -> None:
    """Simulates power loss at each step of the intermediary's swap to the PQ
    bootloader: the next boot must carry on, and the migration must end with
    the seed intact. [MG-12, MG-13, MG-14]"""
    variant = "universal"
    seed = legacy_to_intermediary(unit, fx, variant)
    # armed after the legacy bootloader has stopped running the old image
    cut = CutPoint(fx.intermediary_elf(variant, part), symbol, mode, delay)
    with cutpoint.arm(cut) as armed:
        unit.step(f"cut armed: {cut}", screenshot=False)
        hit = armed.wait()
    if not hit and symbol.endswith(">nrf_update"):
        pytest.skip("the intermediary found the nRF current: no push to cut")
    assert hit, f"the intermediary never reached {symbol}"
    unit.step(f"cut fired: {cut}; {cutpoint.summary(armed)}")
    migration_finishes(unit, fx, variant, seed)


def test_cut_in_pq_bootloader_before_firmware(unit: Unit, fx: Fixtures) -> None:
    """Simulates power loss after migration, while the PQ bootloader waits for
    its first firmware: it must come back to the PQ bootloader, and
    installing the release must keep the seed. [MG-15]"""
    variant = "universal"
    seed = legacy_to_intermediary(unit, fx, variant)
    ctx = flows.wait_pq_bootloader(unit)
    flows.close(ctx)
    unit.reset()
    unit.step("cut: SWD reset in the PQ bootloader")
    migration_finishes(unit, fx, variant, seed)
