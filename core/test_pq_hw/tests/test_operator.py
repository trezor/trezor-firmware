"""Flows with a PIN at boot. A T3W1 is not on USB until its boot lockscreen is
unlocked, so a person enters the PIN; the test checks what follows."""

from __future__ import annotations

import pytest
from pqhw import flows
from pqhw.device import Unit
from pqhw.fixtures import Fixtures

from trezorlib import device

pytestmark = [pytest.mark.hw, pytest.mark.operator]


def install_intermediary_with_pin(
    unit: Unit, fx: Fixtures, wipe_code: str | None = None
) -> str:
    ctx = flows.baseline_legacy(unit, fx, "universal")
    flows.load_seed(unit, ctx, pin=flows.PIN)
    if wipe_code:
        ctx.use_pin_sequence([flows.PIN, wipe_code, wipe_code])
        device.change_wipe_code(ctx.get_seedless_session())
        unit.step(f"wipe code set ({wipe_code})")
    ctx.use_pin_sequence([flows.PIN])
    seed = flows.seed_fingerprint(unit, ctx)
    assert seed is not None
    ctx.use_pin_sequence([flows.PIN])
    ctx = flows.enter_bootloader(unit, ctx)
    flows.legacy_install(unit, ctx, fx.intermediary("universal").read_bytes())
    return seed


def test_pin_gates_the_swap(unit: Unit, fx: Fixtures, operator) -> None:
    """MG-02, MG-04: nothing moves until the PIN is entered; the seed survives."""
    seed = install_intermediary_with_pin(unit, fx)
    operator(
        "The device should show the lockscreen reading 'Unlock to continue "
        "upgrade'. Wait 20 seconds and do NOT unlock."
    )
    assert not unit.present(), "the intermediary must not come up before unlock"
    operator(f"Tap the lockscreen and enter PIN {flows.PIN}.")
    ctx = flows.wait_pq_bootloader(unit)
    flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    operator(f"Unlock release A with PIN {flows.PIN}.")
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    ctx.use_pin_sequence([flows.PIN])
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_wipe_code_at_the_intermediary(unit: Unit, fx: Fixtures, operator) -> None:
    """MG-07: the wipe code erases storage; the legacy bootloader shows the wipe
    screen and reboots; the empty intermediary swaps without asking. The unit
    is stamped, not empty, so release A then asks, and installs uninitialised."""
    install_intermediary_with_pin(unit, fx, wipe_code=flows.WIPE_CODE)
    operator(f"Tap the lockscreen and enter the WIPE CODE {flows.WIPE_CODE}.")
    ctx = flows.wait_pq_bootloader(unit)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.prompted
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(unit, ctx) is None
