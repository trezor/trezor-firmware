# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""Prodtest ``tropic-*`` command tests.

These tests run against a dedicated prodtest emulator with its own Tropic model
(the ``tropic_prodtest`` fixture), rather than the shared session emulator. The
fixture starts the Tropic model automatically — nothing has to be launched by
hand. The general pattern is:

  1. start the emulator + Tropic model (entering the context manager),
  2. issue ``tropic-*`` commands via ``session.client``,
  3. leave the context so the Tropic model flushes its final state, then
  4. (optionally) assert on ``session.state()``.

The tests seed the Tropic model with the default device-test config
(``tests/tropic_model/config.yml``), which represents an already-paired device.
Commands that need a fresh/unpaired chip (``tropic-pair``) or device-specific
certificates are covered only where they succeed; some are exercised through
their error paths instead (e.g. the TRNG, which the model drives from a
constant, and firmware update against a mismatched chip revision).
"""

from __future__ import annotations

import pytest

from trezorlib.prodtest.prodtest_client import Cmd, ProdtestCommand

from . import (
    PRODTEST_ERR_TROPIC_TEST_RNG_REPEAT,
    PRODTEST_ERR_TROPIC_UPDATE_WRONG_REVISION,
    assert_command_fails,
    assert_hexdata,
)
from .tropic_utils import TropicProdtest

# Fixed response sizes reported by libtropic (vendor/libtropic/include).
_CHIP_ID_SIZE = 128  # TR01_L2_GET_INFO_CHIP_ID_SIZE
_FW_VERSION_SIZE = 4  # TR01_L2_GET_INFO_{RISCV,SPECT}_FW_SIZE

# ECC-key and user-data slots populated by the default Tropic model config,
# used to check what ``tropic-erase-all-slots`` clears.
_ECC_KEY_SLOT = 0
_USER_DATA_SLOTS = (3, 4, 6)

# The distribution-version slot ``lock`` writes, and its always-erased backup.
_DISTRIBUTION_VERSION_SLOT = 6
_BACKUP_DISTRIBUTION_VERSION_SLOT = 7

# Arbitrary non-default sensors config: 8 hex digits = big-endian uint32.
_SENSORS_CONFIG_VALUE = "0000000F"

# Reversible-config keys that ``lock`` is expected to change.
_LOCK_CHANGED_R_CONFIG_KEYS = {"cfg_start_up"}


# --- info / read-only commands ---------------------------------------------


@pytest.mark.requires_command(Cmd.TROPIC_GET_CHIP_ID)
def test_tropic_get_chip_id(tropic_prodtest: TropicProdtest) -> None:
    """A chip-ID query returns a well-formed, fixed-size chip ID."""
    with tropic_prodtest() as session:
        resp = session.client.command_ok(ProdtestCommand(Cmd.TROPIC_GET_CHIP_ID))

    # Structural check only: the value is device-specific, but its length is not.
    assert_hexdata(resp, _CHIP_ID_SIZE)


@pytest.mark.requires_command(Cmd.TROPIC_GET_RISCV_FW_VERSION)
def test_tropic_get_riscv_fw_version(tropic_prodtest: TropicProdtest) -> None:
    """The RISC-V firmware version is a well-formed, fixed-size value."""
    with tropic_prodtest() as session:
        resp = session.client.command_ok(
            ProdtestCommand(Cmd.TROPIC_GET_RISCV_FW_VERSION)
        )

    assert_hexdata(resp, _FW_VERSION_SIZE)


@pytest.mark.requires_command(Cmd.TROPIC_GET_SPECT_FW_VERSION)
def test_tropic_get_spect_fw_version(tropic_prodtest: TropicProdtest) -> None:
    """The SPECT firmware version is a well-formed, fixed-size value."""
    with tropic_prodtest() as session:
        resp = session.client.command_ok(
            ProdtestCommand(Cmd.TROPIC_GET_SPECT_FW_VERSION)
        )

    assert_hexdata(resp, _FW_VERSION_SIZE)


@pytest.mark.requires_command(Cmd.TROPIC_LOCK_CHECK)
def test_tropic_lock_check(tropic_prodtest: TropicProdtest, is_emulator: bool) -> None:
    """``lock-check`` reports a yes/no answer.

    On the emulator this is always ``NO``: ``lock-check`` returns ``NO`` as soon
    as the MCU has no stored Tropic public key, which is the case for a freshly
    started emulator — the pairing process was never run against it. On real
    hardware either answer is valid depending on provisioning, so we only check
    the shape there.
    """
    with tropic_prodtest() as session:
        resp = session.client.command_ok(ProdtestCommand(Cmd.TROPIC_LOCK_CHECK))

    assert resp.args in ("YES", "NO")
    if is_emulator:
        assert resp.args == "NO"


@pytest.mark.requires_command(Cmd.TROPIC_READ_CONFIGS)
def test_tropic_read_configs(tropic_prodtest: TropicProdtest) -> None:
    """Reading the whole I/R configuration over a privileged session succeeds."""
    with tropic_prodtest() as session:
        session.client.command_ok(ProdtestCommand(Cmd.TROPIC_READ_CONFIGS))


@pytest.mark.requires_command(Cmd.TROPIC_READ_SENSORS)
def test_tropic_read_sensors(
    tropic_prodtest: TropicProdtest, is_emulator: bool
) -> None:
    """Reading the sensors config returns a 32-bit value as ``0x`` + 8 hex."""
    with tropic_prodtest() as session:
        resp = session.client.command_ok(ProdtestCommand(Cmd.TROPIC_READ_SENSORS))

    # Structural: "0x%08X" of a uint32 -> parseable and in range on any device.
    assert resp.args.startswith("0x"), f"unexpected sensors format: {resp.args!r}"
    value = int(resp.args, 16)
    assert 0 <= value <= 0xFFFFFFFF
    if is_emulator:
        # The freshly seeded model reports the default all-enabled value.
        assert value == 0x00000000


# --- self-test / diagnostic commands ---------------------------------------

# These exercise the Tropic over a session and clean up after themselves; each
# runs against its own fresh model, so we only assert they complete successfully.
_SELF_TEST_COMMANDS = [
    pytest.param(command, marks=pytest.mark.requires_command(command))
    for command in (
        Cmd.TROPIC_BENCHMARK,
        Cmd.TROPIC_STRESS_INIT,
        Cmd.TROPIC_STRESS_SESSION,
        Cmd.TROPIC_STRESS_MAC_AND_DESTROY,
        Cmd.TROPIC_STRESS_TEST,
        Cmd.TROPIC_TEST_MAC_AND_DESTROY,
        Cmd.TROPIC_TEST_RMEM,
        Cmd.TROPIC_TEST_SIGN,
        Cmd.TROPIC_TESTS_CLEANUP,
    )
]


@pytest.mark.parametrize("command", _SELF_TEST_COMMANDS)
def test_tropic_self_tests(tropic_prodtest: TropicProdtest, command: str) -> None:
    """Each self-test/diagnostic command runs to completion on the model."""
    with tropic_prodtest() as session:
        session.client.command_ok(ProdtestCommand(command))


# --- state-changing commands (inspected via the model output) --------------


@pytest.mark.requires_command(Cmd.TROPIC_ERASE_ALL_SLOTS)
def test_tropic_erase_all_slots(tropic_prodtest: TropicProdtest) -> None:
    """``erase-all-slots`` clears ECC keys and data slots, keeps pairing keys."""
    with tropic_prodtest() as session:
        session.client.command_ok(ProdtestCommand(Cmd.TROPIC_ERASE_ALL_SLOTS))

    state = session.state()

    # Pairing keys are explicitly preserved.
    assert state.pairing_key_state(1) == "written"
    assert state.pairing_key_state(2) == "written"

    # ECC keys and user-data slots seeded by the config are gone.
    assert not state.ecc_key_is_present(_ECC_KEY_SLOT)
    for slot in _USER_DATA_SLOTS:
        assert state.slot_is_erased(slot), f"slot {slot} not erased"


@pytest.mark.requires_command(Cmd.TROPIC_SET_SENSORS)
def test_tropic_set_sensors(tropic_prodtest: TropicProdtest) -> None:
    """``set-sensors`` writes the requested value into the R-config."""
    with tropic_prodtest() as session:
        session.client.command_ok(
            ProdtestCommand(Cmd.TROPIC_SET_SENSORS, _SENSORS_CONFIG_VALUE)
        )

    state = session.state()
    assert state.r_config.get("cfg_sensors") == int(_SENSORS_CONFIG_VALUE, 16)


@pytest.mark.requires_command(Cmd.TROPIC_TEST_COUNTER)
def test_tropic_test_counter(tropic_prodtest: TropicProdtest) -> None:
    """``test-counter`` initializes the monotonic counters on the model."""
    with tropic_prodtest() as session:
        session.client.command_ok(ProdtestCommand(Cmd.TROPIC_TEST_COUNTER))

    state = session.state()
    assert state.mcounters, "no monotonic counters were initialized"


@pytest.mark.requires_command(Cmd.TROPIC_LOCK)
def test_tropic_lock(tropic_prodtest: TropicProdtest) -> None:
    """``tropic-lock`` writes the expected config and distribution version.

    ``lock`` is irreversible, but each Tropic test runs against its own
    throwaway model, so locking it is safe. It rewrites the reversible config to
    the expected "locked" values, writes the distribution version into its slot,
    erases the backup slot, and leaves the pairing keys untouched. We capture a
    fresh (unlocked) model as a baseline to show the reversible config actually
    changed.
    """
    with tropic_prodtest() as baseline_session:
        pass  # fresh model, no commands issued
    baseline = baseline_session.state()

    with tropic_prodtest() as session:
        session.client.command_ok(ProdtestCommand(Cmd.TROPIC_LOCK))
    locked = session.state()

    # Locking rewrites the reversible config to the expected locked values.
    # Reporting the full diff on failure.
    r_config_diff = {
        key: (baseline.r_config.get(key), locked.r_config.get(key))
        for key in baseline.r_config.keys() | locked.r_config.keys()
        if baseline.r_config.get(key) != locked.r_config.get(key)
    }
    assert (
        set(r_config_diff) == _LOCK_CHANGED_R_CONFIG_KEYS
    ), f"unexpected r_config changes: {r_config_diff}"

    assert locked.i_config == baseline.i_config

    # The distribution version is written (4-byte big-endian) and its backup
    # slot is left erased.
    version = locked.slot_value(_DISTRIBUTION_VERSION_SLOT)
    assert version is not None and len(version) == 4
    assert locked.slot_is_erased(_BACKUP_DISTRIBUTION_VERSION_SLOT)

    # Pairing keys survive the lock.
    assert locked.pairing_key_state(1) == "written"
    assert locked.pairing_key_state(2) == "written"


# --- error paths (specific prodtest error codes) ---------------------------


@pytest.mark.requires_command(Cmd.TROPIC_TEST_RNG)
def test_tropic_test_rng_rejects_constant_rng(tropic_prodtest: TropicProdtest) -> None:
    """``test-rng``'s sanity check flags the model's constant TRNG output."""
    with tropic_prodtest() as session:
        resp = assert_command_fails(
            session.client, ProdtestCommand(Cmd.TROPIC_TEST_RNG)
        )

    assert resp.error_code == PRODTEST_ERR_TROPIC_TEST_RNG_REPEAT


@pytest.mark.requires_command(Cmd.TROPIC_UPDATE_FW)
def test_tropic_update_fw_rejects_wrong_revision(
    tropic_prodtest: TropicProdtest,
) -> None:
    """``update-fw`` refuses the model's mismatched chip silicon revision."""
    with tropic_prodtest() as session:
        resp = assert_command_fails(
            session.client, ProdtestCommand(Cmd.TROPIC_UPDATE_FW)
        )

    assert resp.error_code == PRODTEST_ERR_TROPIC_UPDATE_WRONG_REVISION
