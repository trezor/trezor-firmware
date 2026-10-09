"""Version floors: fix_version, min_prev_version and the bootloader monotonic.
Each is asserted in both directions, so a floor that fires on everything fails."""

from __future__ import annotations

import pytest
from pqhw import flows
from pqhw.device import Unit
from pqhw.fixtures import Fixtures

from trezorlib import exceptions

pytestmark = pytest.mark.hw


def test_fix_version_wipes_below(unit: Unit, fx: Fixtures) -> None:
    """Installs release A (2.14.0) over B-fix, whose fix_version floor (release
    2.14.1) is above A. The install must still go ahead, but only after a
    confirm, and the seed must be erased. [VR-03]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B-fix", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.prompted
    ctx = flows.wait_firmware(unit)
    assert flows.seed_fingerprint(unit, ctx) is None


def test_fix_version_keeps_at(unit: Unit, fx: Fixtures) -> None:
    """Installs release B over B-fix: B (2.14.1) is exactly at the
    fix_version floor, so the seed must be kept. [VR-03]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B-fix", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_install(unit, ctx, fx.bundle("release-B", "universal"))
    ctx = flows.wait_firmware(unit)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_min_prev_refused_below(unit: Unit, fx: Fixtures) -> None:
    """Offers release C, which only installs over release 2.14.1 or newer, to a
    unit on A (2.14.0). It must be refused before any confirm
    screen, leaving A and the seed untouched. [VR-04]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    with pytest.raises(exceptions.TrezorFailure, match="Unsupported upgrade path"):
        flows.pq_install(
            unit, ctx, fx.bundle("release-C-minprev", "universal"), confirm=False
        )
    flows.close(ctx)
    unit.reset()
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 0)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_min_prev_accepted_at(unit: Unit, fx: Fixtures) -> None:
    """Offers release C to a unit on B (2.14.1, exactly at C's floor): it must
    install and keep the seed. [VR-04]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_install(unit, ctx, fx.bundle("release-C-minprev", "universal"))
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 3)
    assert flows.seed_fingerprint(unit, ctx) == seed


@pytest.mark.burns
def test_monotonic_refuses_older_bootloader(unit: Unit, fx: Fixtures) -> None:
    """Installs release E, which raises the bootloader anti-rollback counter to
    4, then offers B (counter 3): B must be refused before any confirm
    screen. Moves a forward-only counter; the next test's flash erase resets
    it. [VR-01]"""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_install(unit, ctx, fx.bundle("release-E-mono", "universal"))
    ctx = flows.wait_firmware(unit)
    assert flows.version(ctx.features) == (2, 14, 4)
    ctx = flows.enter_bootloader(unit, ctx)
    with pytest.raises(exceptions.TrezorFailure, match="Firmware downgrade protection"):
        flows.pq_install(unit, ctx, fx.bundle("release-B", "universal"), confirm=False)
