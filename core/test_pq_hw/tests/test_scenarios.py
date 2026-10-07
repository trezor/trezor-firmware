"""Short scenario rows: the host wipe in the PQ bootloader and the legacy side
of the one-way door. Plan cases in the docstrings."""

from __future__ import annotations

import pytest
from pqhw import flows
from pqhw.device import Unit
from pqhw.fixtures import Fixtures

from trezorlib import exceptions

pytestmark = pytest.mark.hw


def test_bootloader_wipe_leaves_an_empty_unit(unit: Unit, fx: Fixtures) -> None:
    """WP-01: WipeDevice in the PQ bootloader clears firmware_type with the
    firmware, so the unit reads empty and takes an official release unattended,
    without the old seed."""
    ctx = flows.baseline_pq_installed(unit, fx, "release-A", "universal")
    ctx = flows.enter_bootloader(unit, ctx)
    ctx = flows.wipe_in_bootloader(unit, ctx)
    f = ctx.features
    assert not f.firmware_present
    assert not f.firmware_corrupted
    assert not f.fw_vendor
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert not report.prompted, "a wiped unit must read empty"
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(unit, ctx) is None


def test_legacy_bootloader_refuses_a_pq_image(unit: Unit, fx: Fixtures) -> None:
    """MG-19 (legacy half): the legacy bootloader does not take a PQ firmware
    image, and the legacy firmware still boots with its seed. (The PQ half is
    test_tamper.py::test_bare_phase2_refused.)"""
    ctx = flows.baseline_legacy(unit, fx, "universal")
    flows.load_seed(unit, ctx)
    seed = flows.seed_fingerprint(unit, ctx)
    ctx = flows.enter_bootloader(unit, ctx)
    data = fx.bundle("release-A", "universal").firmware.data
    with pytest.raises(exceptions.TrezorFailure):
        flows.legacy_install(unit, ctx, data, confirm=False)
    unit.step("legacy bootloader refused the PQ image")
    flows.close(ctx)
    unit.reset()
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 13, 0)
    assert flows.seed_fingerprint(unit, ctx) == seed
