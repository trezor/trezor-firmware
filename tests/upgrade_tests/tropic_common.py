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

import json

from tests.emulators import ROOT

TROPIC_CONFIGS_JSON = (
    ROOT / "core" / "embed" / "sec" / "tropic" / "config" / "tropic_configs.json"
)

TROPIC_CONFIG_DISTRIBUTION_VERSION_SLOT = 6
TROPIC_CONFIG_BACKUP_DISTRIBUTION_VERSION_SLOT = 7

CHIP_ID_BATCH_ID_OFFSET = 96
BATCH_ID_V0 = bytes([0x19, 0x0A, 0x08, 0x10, 0x10])
BATCH_ID_V1 = bytes([0x19, 0x07, 0x1F, 0x0A, 0x04])


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


def expected_config(config_type: str, version: int) -> dict[str, int]:
    configs = json.loads(TROPIC_CONFIGS_JSON.read_text())
    config_versions = configs[config_type]
    irreversible = config_type == "irreversible_configurations"

    for versioned_config in config_versions:
        if versioned_config["version"] == version:
            return _config_to_numbers(versioned_config["config"], irreversible)

    raise ValueError(f"Missing Tropic {config_type} version {version}")


def set_chip_id_field(config: dict, offset: int, value: bytes) -> None:
    chip_id = bytearray(config["chip_id"])
    chip_id[offset : offset + len(value)] = value
    config["chip_id"] = bytes(chip_id)


def set_chip_distribution(config: dict, distribution_version: int) -> None:
    batch_id = BATCH_ID_V1 if distribution_version == 1 else BATCH_ID_V0
    set_chip_id_field(config, CHIP_ID_BATCH_ID_OFFSET, batch_id)


def set_slot(config: dict, slot: int, value: bytes | None) -> None:
    r_user_data = config.setdefault("r_user_data", {})
    if value is None:
        r_user_data.pop(slot, None)
        return

    r_user_data[slot] = {"value": value}


def set_version_slot(config: dict, slot: int, version: int | None) -> None:
    """Write a 4-byte big-endian version into `slot`, or erase it."""
    set_slot(config, slot, None if version is None else version.to_bytes(4, "big"))


def _slot_config(config: dict, slot: int) -> dict | None:
    return (config.get("r_user_data") or {}).get(slot)


def slot_value(config: dict, slot: int) -> bytes | None:
    slot_config = _slot_config(config, slot)
    if not slot_config:
        return None
    return slot_config.get("value")


def slot_is_erased(config: dict, slot: int) -> bool:
    slot_config = _slot_config(config, slot)
    if not slot_config:
        return True
    if slot_config.get("free") is True:
        return True

    value = slot_config.get("value")
    if value in (None, b""):
        return True
    return all(byte == 0xFF for byte in value)
