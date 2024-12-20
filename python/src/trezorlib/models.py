# This file is part of the Trezor project.
#
# Copyright (C) 2012-2022 SatoshiLabs and contributors
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

import warnings
from dataclasses import dataclass
from typing import Collection, Tuple

from . import mapping

UsbId = Tuple[int, int]

VENDORS = ("bitcointrezor.com", "trezor.io")


@dataclass(eq=True, frozen=True)
class TrezorModel:
    name: str
    internal_name: str
    minimum_version: Tuple[int, int, int]
    vendors: Collection[str]
    usb_ids: Collection[UsbId]
    default_mapping: mapping.ProtobufMapping


# ==== internal names ====

USBID_TREZOR_ONE = (0x534C, 0x0001)
USBID_TREZOR_CORE = (0x1209, 0x53C1)
USBID_TREZOR_CORE_BOOTLOADER = (0x1209, 0x53C0)


T1B1 = TrezorModel(
    name="1",
    internal_name="T1B1",
    minimum_version=(1, 8, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_ONE,),
    default_mapping=mapping.DEFAULT_MAPPING,
)

T2T1 = TrezorModel(
    name="T",
    internal_name="T2T1",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

T2B1 = TrezorModel(
    name="Safe 3",
    internal_name="T2B1",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

T3T1 = TrezorModel(
    name="Safe 5",
    internal_name="T3T1",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

T3B1 = TrezorModel(
    name="Safe 3",
    internal_name="T3B1",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

T3W1 = TrezorModel(
    name="T3W1",
    internal_name="T3W1",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

DISC1 = TrezorModel(
    name="DISC1",
    internal_name="D001",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

DISC2 = TrezorModel(
    name="DISC2",
    internal_name="D002",
    minimum_version=(2, 1, 0),
    vendors=VENDORS,
    usb_ids=(USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER),
    default_mapping=mapping.DEFAULT_MAPPING,
)

# ==== unknown model ====

UNKNOWN_MODEL = TrezorModel(
    name="Unknown Trezor model",
    internal_name="????",
    minimum_version=(0, 0, 0),
    vendors=VENDORS,
    usb_ids=(),
    default_mapping=mapping.DEFAULT_MAPPING,
)
"""Unknown model is a placeholder for detected devices that respond to the Trezor wire
protocol, but are not in the list of known models -- presumably models newer than the
current library version."""

# ==== model based names ====

TREZOR_ONE = T1B1
TREZOR_T = T2T1
TREZOR_R = T2B1
TREZOR_SAFE3 = T2B1
TREZOR_SAFE5 = T3T1
TREZOR_DISC1 = DISC1
TREZOR_DISC2 = DISC2

TREZORS = frozenset({T1B1, T2T1, T2B1, T3T1, T3B1, T3W1, DISC1, DISC2})


def by_name(name: str | None) -> TrezorModel:
    if name is None:
        return T1B1
    for model in TREZORS:
        if model.name == name:
            return model
    return UNKNOWN_MODEL


def by_internal_name(name: str) -> TrezorModel:
    if name is None:
        warnings.warn("by_internal_name will no longer accept None", stacklevel=2)
        return None  # type: ignore [incompatible with "TrezorModel"]
    for model in TREZORS:
        if model.internal_name == name:
            return model
    return UNKNOWN_MODEL
