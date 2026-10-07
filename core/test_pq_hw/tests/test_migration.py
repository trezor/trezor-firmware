"""The legacy -> PQ migration, unattended (no PIN). Operator-driven PIN flows
are in test_operator.py."""

from __future__ import annotations

import pytest
from pqhw import flows
from pqhw.device import Unit
from pqhw.fixtures import VARIANTS, Fixtures

from trezorlib.messages import FirmwareScheme

pytestmark = pytest.mark.hw


def migrate(unit: Unit, fx: Fixtures, legacy_variant: str, seeded: bool = True):
    """Legacy baseline -> intermediary over the wire -> PQ bootloader. Returns
    (bootloader-mode context, seed fingerprint taken on the legacy firmware)."""
    ctx = flows.baseline_legacy(unit, fx, legacy_variant)
    assert ctx.features.firmware_scheme in (None, FirmwareScheme.Legacy)
    assert flows.version(ctx.features) == (2, 13, 0)
    seed = None
    if seeded:
        flows.load_seed(unit, ctx)
        seed = flows.seed_fingerprint(unit, ctx)
        assert seed is not None

    # MG-01: the legacy bootloader takes the legacy-signed intermediary
    ctx = flows.enter_bootloader(unit, ctx)
    flows.legacy_install(unit, ctx, fx.intermediary(legacy_variant).read_bytes())

    # MG-03/MG-09: with no PIN the intermediary unlocks silently and swaps the
    # bootloader on its first boot; it never comes up on USB on the way
    ctx = flows.wait_pq_bootloader(unit)
    assert flows.version(ctx.features) == (2, 1, 19)
    return ctx, seed


@pytest.mark.parametrize("variant", VARIANTS)
def test_migration_keeps_seed(unit: Unit, fx: Fixtures, variant: str) -> None:
    """Migrates a seeded legacy unit through the intermediary to the PQ
    bootloader and release A of the same variant: the seed must survive.
    [MG-01, MG-03, MG-04, MG-05]"""
    ctx, seed = migrate(unit, fx, variant)
    # stamped, so the unit is not empty: the install asks
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", variant))
    assert report.prompted
    assert report.served["code"] == 0, "the swapped-in bootloader is A's own"

    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert ctx.features.firmware_scheme == FirmwareScheme.PqSecure
    assert flows.version(ctx.features) == (2, 14, 0)
    assert flows.seed_fingerprint(unit, ctx) == seed


def test_migration_into_other_variant_wipes(unit: Unit, fx: Fixtures) -> None:
    """After migrating a universal unit, installing btc-only crosses storage
    domains: the seed is erased, so the intermediary's variant stamp
    matters."""
    ctx, _ = migrate(unit, fx, "universal")
    report = flows.pq_install(unit, ctx, fx.bundle("release-A", "btc-only"))
    assert report.prompted
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.seed_fingerprint(unit, ctx) is None


def test_unseeded_unit_migrates(unit: Unit, fx: Fixtures) -> None:
    """A legacy unit with no seed migrates with no interaction at all and ends
    on PQ release A, still empty. [MG-09]"""
    ctx, _ = migrate(unit, fx, "universal", seeded=False)
    flows.pq_install(unit, ctx, fx.bundle("release-A", "universal"))
    ctx = unit.context(bootloader=False, timeout=flows.REBOOT)
    assert flows.version(ctx.features) == (2, 14, 0)
    assert flows.seed_fingerprint(unit, ctx) is None
