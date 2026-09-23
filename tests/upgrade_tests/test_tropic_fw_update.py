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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

import tempfile
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.emulators import (
    TROPIC_MODEL_CONFIGFILE,
    EmulatorWrapper,
    delete_profile,
    get_logfile,
)
from trezorlib._internal.emulator import TropicModel

from . import model_only
from .tropic_common import (
    TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
    TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
    expected_config,
    set_chip_distribution,
    set_chip_id_field,
    set_slot,
    set_version_slot,
    slot_is_erased,
    slot_value,
)

TROPIC_FW_VERSION_SLOT = 8
CHIP_ID_SILICON_REV_OFFSET = 28
SILICON_REV_ACAB = b"ACAB"
SILICON_REV_ABAB = b"ABAB"

MAINTENANCE_ENA_BIT = 3
MAINTENANCE_FORBIDDEN_I_CONFIG = "maintenance_forbidden_i"


def _bundled_fw_version_slot() -> bytes:
    """The versions `tropic_write_fw_slot()` records after a successful update.

    Taken from the generated model config, which `generate_tropic_model_config.py`
    fills from the images bundled by `core/embed/sec/tropic/build.rs`. A firmware
    bump therefore only has to be followed by `make tropic_config`.
    """
    config = yaml.safe_load(TROPIC_MODEL_CONFIGFILE.read_text())
    value = slot_value(config, TROPIC_FW_VERSION_SLOT)
    assert value is not None, f"Missing FW version slot in {TROPIC_MODEL_CONFIGFILE}"
    return value


def _shift_majors(slot: bytes, delta: int) -> bytes:
    """Shift the major version of both halves of a FW version slot.

    Both have to move: `fw_version_is_older()` is OR-ed over the two, so leaving
    one half pinned would eventually make it older than the bundled image and
    flip the scenario it belongs to.
    """
    version = bytearray(slot)
    version[3] += delta  # RISC-V major
    version[7] += delta  # SPECT major
    return bytes(version)


BUNDLED_FW_VERSION_SLOT = _bundled_fw_version_slot()
# An older version makes `fw_version_is_older()` report that an update is due.
OLDER_FW_VERSION_SLOT = _shift_majors(BUNDLED_FW_VERSION_SLOT, -1)
# A newer version must be left alone -- no downgrades.
NEWER_FW_VERSION_SLOT = _shift_majors(BUNDLED_FW_VERSION_SLOT, +1)
# Only the RISC-V half written: a short slot is indistinguishable from an empty
# one and triggers an update.
TRUNCATED_FW_VERSION_SLOT = BUNDLED_FW_VERSION_SLOT[:4]


@dataclass(frozen=True)
class TropicFwUpdateScenario:
    id: str
    chip_distribution: int
    initial_i_config: int | str
    initial_r_config: int
    distribution_slot: int | None
    backup_slot: int | None
    fw_version_slot: bytes | None
    expect_failure: bool
    silicon_revision: bytes = SILICON_REV_ACAB
    expected_i_version: int | None = None
    expected_r_version: int | None = None
    expected_distribution_version: int | None = None
    expected_fw_version_slot: bytes | None = None


TROPIC_FW_UPDATE_SCENARIOS = [
    TropicFwUpdateScenario(
        id="already-updated",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=BUNDLED_FW_VERSION_SLOT,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="slot-empty",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=None,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="older-version",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=OLDER_FW_VERSION_SLOT,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="newer-version",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=NEWER_FW_VERSION_SLOT,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=NEWER_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="truncated-slot",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=TRUNCATED_FW_VERSION_SLOT,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="maintenance-already-on",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=None,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="older-version-maintenance-on",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=OLDER_FW_VERSION_SLOT,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="interrupted-update",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=None,
        backup_slot=0,
        fw_version_slot=None,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="interrupted-update-v1",
        chip_distribution=1,
        initial_i_config=1,
        initial_r_config=0,
        distribution_slot=None,
        backup_slot=1,
        fw_version_slot=None,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="distribution-ahead",
        chip_distribution=0,
        initial_i_config=1,
        initial_r_config=1,
        distribution_slot=1,
        backup_slot=None,
        fw_version_slot=OLDER_FW_VERSION_SLOT,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="interrupted-update-distribution-ahead",
        chip_distribution=0,
        initial_i_config=1,
        initial_r_config=0,
        distribution_slot=None,
        backup_slot=1,
        fw_version_slot=None,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expected_fw_version_slot=BUNDLED_FW_VERSION_SLOT,
    ),
    TropicFwUpdateScenario(
        id="maintenance-forbidden",
        chip_distribution=0,
        initial_i_config=MAINTENANCE_FORBIDDEN_I_CONFIG,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=None,
        expect_failure=True,
    ),
    TropicFwUpdateScenario(
        id="wrong-silicon-revision",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=None,
        expect_failure=True,
        silicon_revision=SILICON_REV_ABAB,
    ),
    TropicFwUpdateScenario(
        id="wrong-silicon-revision-maintenance-on",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=0,
        backup_slot=None,
        fw_version_slot=None,
        expect_failure=True,
        silicon_revision=SILICON_REV_ABAB,
    ),
]


def _initial_i_config(version_or_name: int | str) -> dict[str, int]:
    if isinstance(version_or_name, int):
        return expected_config("irreversible_configurations", version_or_name)

    if version_or_name == MAINTENANCE_FORBIDDEN_I_CONFIG:
        config = expected_config("irreversible_configurations", 0)
        config["cfg_start_up"] &= ~(1 << MAINTENANCE_ENA_BIT)
        return config

    raise ValueError(f"Unknown Tropic i_config scenario: {version_or_name}")


def _build_tropic_model_config(scenario: TropicFwUpdateScenario) -> dict:
    config = yaml.safe_load(TROPIC_MODEL_CONFIGFILE.read_text())
    set_chip_distribution(config, scenario.chip_distribution)
    set_chip_id_field(config, CHIP_ID_SILICON_REV_OFFSET, scenario.silicon_revision)
    config["i_config"] = _initial_i_config(scenario.initial_i_config)
    config["r_config"] = expected_config(
        "reversible_configurations", scenario.initial_r_config
    )
    set_version_slot(
        config, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT, scenario.distribution_slot
    )
    set_version_slot(
        config, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT, scenario.backup_slot
    )
    set_slot(config, TROPIC_FW_VERSION_SLOT, scenario.fw_version_slot)
    return config


def _check_tropic_model_output(
    output_path: Path, scenario: TropicFwUpdateScenario
) -> None:
    assert output_path.exists(), (
        f"Tropic model output file was not generated: {output_path}. "
        f"Profile contents: {sorted(path.name for path in output_path.parent.iterdir())}"
    )
    assert scenario.expected_i_version is not None
    assert scenario.expected_r_version is not None
    assert scenario.expected_distribution_version is not None
    assert scenario.expected_fw_version_slot is not None

    output = yaml.safe_load(output_path.read_text())
    assert output["i_config"] == expected_config(
        "irreversible_configurations", scenario.expected_i_version
    )
    assert output["r_config"] == expected_config(
        "reversible_configurations", scenario.expected_r_version
    )

    assert slot_value(
        output, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT
    ) == scenario.expected_distribution_version.to_bytes(4, "big")
    assert slot_is_erased(output, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT)
    assert (
        slot_value(output, TROPIC_FW_VERSION_SLOT) == scenario.expected_fw_version_slot
    )


def _check_tropic_model_unchanged(output_path: Path, initial_config: dict) -> None:
    output = yaml.safe_load(output_path.read_text())
    assert output["i_config"] == initial_config["i_config"]
    assert output["r_config"] == initial_config["r_config"]

    for slot in (
        TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT,
        TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT,
        TROPIC_FW_VERSION_SLOT,
    ):
        initial_value = slot_value(initial_config, slot)
        if initial_value is None:
            assert slot_is_erased(output, slot)
        else:
            assert slot_value(output, slot) == initial_value


@model_only("T3W1")
@pytest.mark.parametrize("scenario", TROPIC_FW_UPDATE_SCENARIOS, ids=lambda s: s.id)
def test_tropic_fw_update(scenario: TropicFwUpdateScenario) -> None:
    with tempfile.TemporaryDirectory(
        prefix="trezor-tropic-fw-update-", delete=delete_profile()
    ) as temp_dir:
        config_path = Path(temp_dir) / "tropic_model_config.yml"
        output_path = Path(temp_dir) / "tropic_model_config_output.yml"
        initial_config = _build_tropic_model_config(scenario)
        config_path.write_text(yaml.safe_dump(initial_config, sort_keys=False))

        with TropicModel(
            profile_dir=temp_dir,
            configfile=config_path,
            configfile_output=output_path,
            logfile=get_logfile("trezor-tropic-model.log", Path(temp_dir)),
        ) as tropic_model:
            tropic_model.start()

            if scenario.expect_failure:
                expectation = pytest.raises(RuntimeError, match="Emulator process died")
            else:
                expectation = nullcontext()

            # The emulator only answers once `bootscreen()` has finished, so this
            # covers the recovery at boot and the update after the unlock.
            with (
                expectation,
                EmulatorWrapper(
                    model="core",
                    profile_dir=temp_dir,
                    tropic_model_port=tropic_model.port,
                ),
            ):
                # wait for start, then exit immediately
                pass

        if scenario.expect_failure:
            _check_tropic_model_unchanged(output_path, initial_config)
        else:
            _check_tropic_model_output(output_path, scenario)
