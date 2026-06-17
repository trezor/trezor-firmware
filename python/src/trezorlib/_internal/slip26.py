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

from __future__ import annotations

from enum import IntEnum


# SLIP-26 purposes.
class Purpose(IntEnum):
    BOOTLOADER = 0
    VENDOR_HEADER = 1
    FIRMWARE = 2
    DEFINITIONS = 3
    PRODTEST = 4
    CA_FIRMWARE = 5
    FIDO_AUTHORITY = 6
    FIDO_BACKUP = 7
    BITCOIN_ONLY = 8
    TRANSLATIONS = 9
    SECURE_MONITOR = 10
    NRF_FIRMWARE = 11
    FIRMWARE_ROOT_2025 = 12


# Purpose strings used in fingerprints files ("<model>_<purpose>: HEX").
PURPOSE_TO_STR: dict[Purpose, str] = {
    Purpose.BOOTLOADER: "bootloader",
    Purpose.VENDOR_HEADER: "vendorheader",
    Purpose.FIRMWARE: "universal",
    Purpose.DEFINITIONS: "definitions",
    Purpose.PRODTEST: "prodtest",
    Purpose.CA_FIRMWARE: "ca",
    Purpose.BITCOIN_ONLY: "btconly",
    Purpose.TRANSLATIONS: "translations",
    Purpose.SECURE_MONITOR: "secmon",
    Purpose.NRF_FIRMWARE: "nrf",
    Purpose.FIRMWARE_ROOT_2025: "firmware_root_2025",
}
STR_TO_PURPOSE: dict[str, Purpose] = {v: k for k, v in PURPOSE_TO_STR.items()}

# Vendor-header text -> purpose, for classifying a vendor firmware image.
VENDOR_TEXT_TO_PURPOSE: dict[str, Purpose] = {
    "SatoshiLabs": Purpose.FIRMWARE,
    "Trezor": Purpose.FIRMWARE,
    "UNSAFE, FACTORY TEST ONLY": Purpose.PRODTEST,
    "Internal CA": Purpose.CA_FIRMWARE,
    "Trezor Bitcoin-only": Purpose.BITCOIN_ONLY,
}


def make_label(model_int: int, purpose: Purpose) -> str:
    """Render a fingerprints-file label, e.g. (T3W1, BITCOIN_ONLY) -> "t3w1_btconly".

    ``model_int`` is the little-endian ASCII model integer, or 0 for model-agnostic
    objects (rendered as the bare label).
    """
    purpose_str = PURPOSE_TO_STR.get(purpose)
    if purpose_str is None:
        raise ValueError(f"purpose {purpose} has no label")

    if model_int == 0:
        # model-agnostic label, e.g. "translations"
        return purpose_str

    return f"{model_int.to_bytes(4, 'little').decode().lower()}_{purpose_str}"


def parse_label(label: str) -> tuple[int, Purpose]:
    """Inverse of `make_label`: "<model>_<purpose>" (or a bare, model-agnostic
    "<purpose>") -> (model, purpose).
    """
    if label in STR_TO_PURPOSE:
        return 0, STR_TO_PURPOSE[label]

    model_str, sep, purpose_str = label.partition("_")
    if sep and purpose_str in STR_TO_PURPOSE:
        model = int.from_bytes(model_str.upper().encode(), "little")
        return model, STR_TO_PURPOSE[purpose_str]

    raise ValueError(f"unknown label {label!r}")
