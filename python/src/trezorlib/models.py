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

from dataclasses import dataclass
from typing import Collection, Tuple

from . import mapping, messages

UsbId = Tuple[int, int]

VENDORS = ("bitcointrezor.com", "trezor.io")


@dataclass(eq=True, frozen=True)
class TrezorModel:
    name: str
    internal_name: str
    minimum_version: tuple[int, int, int]
    vendors: Collection[str]
    usb_ids: Collection[UsbId]
    default_mapping: mapping.ProtobufMapping

    is_unknown: bool = False


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

# ==== model based names ====

TREZOR_ONE = T1B1
TREZOR_T = T2T1
TREZOR_R = T2B1
TREZOR_SAFE3 = T2B1
TREZOR_SAFE5 = T3T1
TREZOR_DISC1 = DISC1
TREZOR_DISC2 = DISC2

TREZORS = frozenset({T1B1, T2T1, T2B1, T3T1, T3B1, T3W1, DISC1, DISC2})


def by_name(name: str | None) -> TrezorModel | None:
    """Try to find a TrezorModel by its name.

    This is a fallback function in case `internal_model` is not available. For general
    model detection, prefer `detect()`.
    """
    if name is None:
        return T1B1
    for model in TREZORS:
        if model.name == name:
            return model
    return None


def by_internal_name(name: str | None) -> TrezorModel | None:
    """Try to find a TrezorModel by its internal name.

    Used internally as part of `detect()` routine. For general model detection, prefer
    calling `detect()`.
    """
    if name is None:
        return None
    for model in TREZORS:
        if model.internal_name == name:
            return model
    return None


def detect(features: messages.Features) -> TrezorModel:
    """Detect Trezor model from its Features response.

    If `internal_name` is sent, tries to detect model based on it. If not (in older
    firmwares), falls back to `model` field.

    If no match is found, returns an ad-hoc TrezorModel instance whose fields are set
    based on the provided model and/or internal model. This can either represent a newer
    model that is not recognized by the current version of the library, or a fork that
    responds to Trezor wire protocol but is not actually a Trezor.
    """
    model = by_internal_name(features.internal_model)
    if model is not None:
        return model
    model = by_name(features.model)
    if model is not None:
        return model

    return TrezorModel(
        name=features.model or "Unknown",
        internal_name=features.internal_model or "????",
        minimum_version=(0, 0, 0),
        # Allowed vendors are the internal VENDORS list instead of trusting features.vendor.
        # That way, an unrecognized non-Trezor device will fail the check in TrezorClient.
        vendors=VENDORS,
        usb_ids=(),
        default_mapping=mapping.DEFAULT_MAPPING,
        is_unknown=True,
    )
