"""Flows with a PIN at boot. Debug builds start USB and debuglink before the
boot PIN prompt, so the PIN (or the wipe code) is entered over debuglink."""

from __future__ import annotations

import time

import pytest
from pqhw import flows
from pqhw.device import Unit, read_screen, unlock_lockscreen
from pqhw.fixtures import Fixtures

from trezorlib import device

pytestmark = pytest.mark.hw

# How long a locked intermediary is watched for a swap it must not start.
LOCKED_WATCH = 20


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


def test_pin_gates_the_swap(unit: Unit, fx: Fixtures) -> None:
    """With a PIN set, the intermediary does nothing until the PIN is entered:
    it stays up on the same USB enumeration for 20 s. Then
    the PIN goes in over debuglink, it swaps to the PQ bootloader, release A
    installs, and the seed survives behind the same PIN. [MG-02, MG-04]"""
    seed = install_intermediary_with_pin(unit, fx)
    _, ident = read_screen(unit, timeout=flows.REBOOT)
    unit.step(f"intermediary locked; watching {LOCKED_WATCH} s for a swap")
    time.sleep(LOCKED_WATCH)
    _, ident_after = read_screen(unit, timeout=30)
    # A swap reboots into the bootloader, which re-enumerates.
    assert ident_after == ident, "the intermediary rebooted (swapped) before unlock"
    unlock_lockscreen(unit, flows.PIN)
    ctx = flows.wait_pq_bootloader(unit)
    flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    unlock_lockscreen(unit, flows.PIN, timeout=flows.REBOOT)
    ctx = flows.wait_firmware(unit)
    ctx.use_pin_sequence([flows.PIN])
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_wipe_code_at_the_intermediary(unit: Unit, fx: Fixtures) -> None:
    """Entering the wipe code at the intermediary's PIN prompt erases storage;
    the empty intermediary then swaps, and the install of release A asks for
    confirmation on the now empty unit. [MG-07]"""
    install_intermediary_with_pin(unit, fx, wipe_code=flows.WIPE_CODE)
    unlock_lockscreen(unit, flows.WIPE_CODE, timeout=flows.REBOOT)
    ctx = flows.wait_pq_bootloader(unit)
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    assert report.prompted
    ctx = flows.wait_firmware(unit)
    assert flows.seed_fingerprint(unit, ctx) is None
