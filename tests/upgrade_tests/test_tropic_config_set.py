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
    ROOT,
    TROPIC_MODEL_CURRENT_CONFIG,
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
    set_version_slot,
    slot_is_erased,
    slot_value,
)

INCOMPARABLE_I_CONFIG = "incomparable_i"
INCOMPARABLE_R_CONFIG = "incomparable_r"


@dataclass(frozen=True)
class TropicBootScenario:
    id: str
    chip_distribution: int
    initial_i_config: int | str
    initial_r_config: int | str
    distribution_slot: int | None
    backup_slot: int | None
    expect_failure: bool
    expected_i_version: int | None = None
    expected_r_version: int | None = None
    expected_distribution_version: int | None = None
    expect_backup_erased: bool | None = None


TROPIC_BOOT_SCENARIOS = [
    TropicBootScenario(
        id="v0-pass",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=0,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=0,
        expected_distribution_version=0,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="v1-pass",
        chip_distribution=1,
        initial_i_config=1,
        initial_r_config=1,
        distribution_slot=1,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="v0-chip-with-v1-distribution",
        chip_distribution=0,
        initial_i_config=1,
        initial_r_config=1,
        distribution_slot=1,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="v0-to-v1",
        chip_distribution=1,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=0,
        backup_slot=0,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="none-to-v0",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=None,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=0,
        expected_distribution_version=0,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="none-to-v0-maintenance",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=None,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=0,
        expected_r_version=1,
        expected_distribution_version=0,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="none-to-v1",
        chip_distribution=1,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=None,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="none-to-v1-maintenance",
        chip_distribution=1,
        initial_i_config=0,
        initial_r_config=1,
        distribution_slot=None,
        backup_slot=None,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="none-to-v1-backup-older",
        chip_distribution=1,
        initial_i_config=0,
        initial_r_config=0,
        distribution_slot=None,
        backup_slot=0,
        expect_failure=False,
        expected_i_version=1,
        expected_r_version=1,
        expected_distribution_version=1,
        expect_backup_erased=True,
    ),
    TropicBootScenario(
        id="incomparable-i-configs",
        chip_distribution=1,
        initial_i_config=INCOMPARABLE_I_CONFIG,
        initial_r_config=0,
        distribution_slot=0,
        backup_slot=0,
        expect_failure=True,
    ),
    TropicBootScenario(
        id="none-to-v0-backup-newer-fails",
        chip_distribution=0,
        initial_i_config=1,
        initial_r_config=1,
        distribution_slot=None,
        backup_slot=1,
        expect_failure=True,
    ),
    TropicBootScenario(
        id="none-to-v0-incomparable-r-configs",
        chip_distribution=0,
        initial_i_config=0,
        initial_r_config=INCOMPARABLE_R_CONFIG,
        distribution_slot=None,
        backup_slot=None,
        expect_failure=True,
    ),
]


def _initial_config(config_type: str, version_or_name: int | str) -> dict[str, int]:
    if isinstance(version_or_name, int):
        return expected_config(config_type, version_or_name)

    if version_or_name == INCOMPARABLE_I_CONFIG:
        config = expected_config("irreversible_configurations", 0)
        config["cfg_uap_mac_and_destroy"] = 4244438268
        return config

    if version_or_name == INCOMPARABLE_R_CONFIG:
        config = expected_config("reversible_configurations", 0)
        config["cfg_start_up"] = 2
        return config

    raise ValueError(f"Unknown Tropic config scenario: {version_or_name}")


def _build_tropic_model_config(scenario: TropicBootScenario) -> dict:
    config = yaml.safe_load(TROPIC_MODEL_CURRENT_CONFIG.read_text())
    set_chip_distribution(config, scenario.chip_distribution)
    config["i_config"] = _initial_config(
        "irreversible_configurations", scenario.initial_i_config
    )
    config["r_config"] = _initial_config(
        "reversible_configurations", scenario.initial_r_config
    )
    set_version_slot(
        config, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT, scenario.distribution_slot
    )
    set_version_slot(
        config, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT, scenario.backup_slot
    )
    return config


def _check_tropic_model_output(
    output_path: Path,
    expected_i_version: int,
    expected_r_version: int,
    expected_distribution_version: int,
    expect_backup_erased: bool,
) -> None:
    assert output_path.exists(), (
        f"Tropic model output file was not generated: {output_path}. "
        f"Profile contents: {sorted(path.name for path in output_path.parent.iterdir())}"
    )

    output = yaml.safe_load(output_path.read_text())
    assert output["i_config"] == expected_config(
        "irreversible_configurations", expected_i_version
    )
    assert output["r_config"] == expected_config(
        "reversible_configurations", expected_r_version
    )

    assert slot_value(
        output, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT
    ) == expected_distribution_version.to_bytes(4, "big")
    if expect_backup_erased:
        assert slot_is_erased(output, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT)


@model_only("T3W1")
@pytest.mark.parametrize("scenario", TROPIC_BOOT_SCENARIOS, ids=lambda s: s.id)
def test_tropic_boot(scenario: TropicBootScenario) -> None:
    with tempfile.TemporaryDirectory(
        prefix="trezor-tropic-config-", delete=delete_profile()
    ) as temp_dir:
        config_path = Path(temp_dir) / "tropic_model_config.yml"
        output_path = Path(temp_dir) / "tropic_model_config_output.yml"
        config_path.write_text(
            yaml.safe_dump(_build_tropic_model_config(scenario), sort_keys=False)
        )

        # using the default port - needs similar mechanism as device tests if we want
        # parallel execution of test cases (currently not supported for upgrade tests)
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

        if not scenario.expect_failure:
            assert scenario.expected_i_version is not None
            assert scenario.expected_r_version is not None
            assert scenario.expected_distribution_version is not None
            assert scenario.expect_backup_erased is not None
            _check_tropic_model_output(
                output_path,
                scenario.expected_i_version,
                scenario.expected_r_version,
                scenario.expected_distribution_version,
                scenario.expect_backup_erased,
            )
