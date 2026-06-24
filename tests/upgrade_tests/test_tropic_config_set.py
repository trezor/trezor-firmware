# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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


import json
import tempfile
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from tests.emulators import (
    ROOT,
    TROPIC_MODEL_CONFIGFILE,
    EmulatorWrapper,
    delete_profile,
    get_logfile,
)
from trezorlib._internal.emulator import TropicModel

from . import model_only

TROPIC_CONFIGS_JSON = (
    ROOT / "core" / "embed" / "sec" / "tropic" / "config" / "tropic_configs.json"
)
TROPIC_MODEL_DIR = TROPIC_MODEL_CONFIGFILE.parent
TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT = 6
TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT = 7
CHIP_ID_BATCH_ID_OFFSET = 96
BATCH_ID_V0 = bytes([0x19, 0x0A, 0x08, 0x10, 0x10])
BATCH_ID_V1 = bytes([0x19, 0x07, 0x1F, 0x0A, 0x04])
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


def _config_to_numbers(config: dict, irreversible: bool) -> dict[str, int]:
    numbers = {}
    for category, category_config in config.items():
        number = 0xFFFFFFFF if irreversible else 0
        settings = category_config["setting"]

        if "uap" not in category:
            for details in settings.values():
                if irreversible:
                    if not details["value"]:
                        number &= ~(1 << details["bit"])
                elif details["value"]:
                    number |= 1 << details["bit"]
        else:
            for i in range(4):
                for details in settings[f"pairing_key_{i}"].values():
                    if irreversible:
                        if not details["value"]:
                            number &= ~(1 << details["bit"])
                    elif details["value"]:
                        number |= 1 << details["bit"]

        numbers[category] = number
    return numbers


def _expected_config(config_type: str, version: int) -> dict[str, int]:
    configs = json.loads(TROPIC_CONFIGS_JSON.read_text())
    config_versions = configs[config_type]
    irreversible = config_type == "irreversible_configurations"

    for versioned_config in config_versions:
        if versioned_config["version"] == version:
            return _config_to_numbers(versioned_config["config"], irreversible)

    raise ValueError(f"Missing Tropic {config_type} version {version}")


def _initial_config(config_type: str, version_or_name: int | str) -> dict[str, int]:
    if isinstance(version_or_name, int):
        return _expected_config(config_type, version_or_name)

    if version_or_name == INCOMPARABLE_I_CONFIG:
        config = _expected_config("irreversible_configurations", 0)
        config["cfg_uap_mac_and_destroy"] = 4244438268
        return config

    if version_or_name == INCOMPARABLE_R_CONFIG:
        config = _expected_config("reversible_configurations", 0)
        config["cfg_start_up"] = 2
        return config

    raise ValueError(f"Unknown Tropic config scenario: {version_or_name}")


def _set_chip_distribution(config: dict, distribution_version: int) -> None:
    batch_id = BATCH_ID_V1 if distribution_version == 1 else BATCH_ID_V0
    chip_id = bytearray(config["chip_id"])
    chip_id[CHIP_ID_BATCH_ID_OFFSET : CHIP_ID_BATCH_ID_OFFSET + len(batch_id)] = (
        batch_id
    )
    config["chip_id"] = bytes(chip_id)


def _set_slot(config: dict, slot: int, value: int | None) -> None:
    r_user_data = config.setdefault("r_user_data", {})
    if value is None:
        r_user_data.pop(slot, None)
        return

    r_user_data[slot] = {"value": value.to_bytes(4, "big")}


def _build_tropic_model_config(scenario: TropicBootScenario) -> dict:
    config = yaml.safe_load(TROPIC_MODEL_CONFIGFILE.read_text())
    _set_chip_distribution(config, scenario.chip_distribution)
    config["i_config"] = _initial_config(
        "irreversible_configurations", scenario.initial_i_config
    )
    config["r_config"] = _initial_config(
        "reversible_configurations", scenario.initial_r_config
    )
    _set_slot(
        config, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT, scenario.distribution_slot
    )
    _set_slot(
        config, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT, scenario.backup_slot
    )
    config["s_t_priv"] = str(TROPIC_MODEL_DIR / config["s_t_priv"])
    config["s_t_pub"] = str(TROPIC_MODEL_DIR / config["s_t_pub"])
    config["x509_certificate"] = str(TROPIC_MODEL_DIR / config["x509_certificate"])
    return config


def _slot_config(config: dict, slot: int) -> dict | None:
    return (config.get("r_user_data") or {}).get(slot)


def _slot_value(config: dict, slot: int) -> bytes | None:
    slot_config = _slot_config(config, slot)
    if not slot_config:
        return None
    return slot_config.get("value")


def _slot_is_erased(config: dict, slot: int) -> bool:
    slot_config = _slot_config(config, slot)
    if not slot_config:
        return True
    if slot_config.get("free") is True:
        return True

    value = slot_config.get("value")
    if value in (None, b""):
        return True
    return all(byte == 0xFF for byte in value)


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
    assert output["i_config"] == _expected_config(
        "irreversible_configurations", expected_i_version
    )
    assert output["r_config"] == _expected_config(
        "reversible_configurations", expected_r_version
    )

    assert _slot_value(
        output, TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT
    ) == expected_distribution_version.to_bytes(4, "big")
    if expect_backup_erased:
        assert _slot_is_erased(output, TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT)


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
