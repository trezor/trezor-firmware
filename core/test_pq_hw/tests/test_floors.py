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
    """VR-03: under B-fix (fix 2.1.20), installing A (2.1.19) wipes, never
    silently: the confirm is forced."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B-fix", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.prompted
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(unit, ctx) is None


def test_fix_version_keeps_at(unit: Unit, fx: Fixtures) -> None:
    """VR-03: under B-fix, installing B (2.1.20, at the floor) keeps the seed."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B-fix", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_install(unit, ctx, fx.bundle("release-B", "universal"))
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_min_prev_refused_below(unit: Unit, fx: Fixtures) -> None:
    """VR-04: C needs an installed bootloader >= 2.1.20; A has 2.1.19. Refused
    in phase 1 before any prompt, and the unit still runs A with its seed."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    with pytest.raises(exceptions.TrezorFailure):
        flows.pq_install(
            unit, ctx, fx.bundle("release-C-minprev", "universal"), confirm=False
        )
    flows.close(ctx)
    unit.reset()
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 0)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_min_prev_accepted_at(unit: Unit, fx: Fixtures) -> None:
    """VR-04: from B (2.1.20) the same release installs."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-B", "universal")
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_install(unit, ctx, fx.bundle("release-C-minprev", "universal"))
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 3)
    assert flows.seed_fingerprint(unit, ctx) == seed


@pytest.mark.burns
def test_monotonic_refuses_older_bootloader(unit: Unit, fx: Fixtures) -> None:
    """VR-01: E burns bootloader monotonic 4; B (monotonic 3) is then refused
    before the confirm. The next baseline's flash-erase resets the counter."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    flows.pq_install(unit, ctx, fx.bundle("release-E-mono", "universal"))
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 4)
    ctx = flows.enter_bootloader(unit, ctx)
    with pytest.raises(exceptions.TrezorFailure):
        flows.pq_install(unit, ctx, fx.bundle("release-B", "universal"), confirm=False)
