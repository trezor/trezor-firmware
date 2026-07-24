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

from dataclasses import dataclass
from typing import Collection, Tuple

from . import _modeldata as _md
from . import mapping, messages
from ._modeldata import registry as _registry

UsbId = Tuple[int, int]

VENDORS = ("bitcointrezor.com", "trezor.io")


@dataclass(eq=True, frozen=True)
class TrezorModel:
    """Runtime/wire view of a model, built from a single-source
    :class:`._modeldata.ModelData` via :func:`_build`.

    ``ModelData`` is the protobuf-free source of truth (it also carries the
    firmware-verification keys/hashes) and deliberately sits *below* this module
    so ``trezorlib.firmware.models`` can consume it without pulling in protobuf.
    ``TrezorModel`` is the derived wrapper that adds the protobuf mapping and
    transport fields (``default_mapping``, ``usb_ids``, ``vendors``); the fields
    shared with ``ModelData`` are populated from it, not duplicated."""

    name: str
    internal_name: str
    minimum_version: tuple[int, int, int]
    vendors: Collection[str]
    usb_ids: Collection[UsbId]
    default_mapping: mapping.ProtobufMapping

    is_unknown: bool = False
    # UI layout name (matches debuglink.LayoutType members), BLE capability, and
    # CLI aliases. Sourced from the single-source model registry; None/empty for
    # ad-hoc unknown models.
    layout: str | None = None
    ble_capable: bool = False
    aliases: tuple[str, ...] = ()


# ==== internal names ====

USBID_TREZOR_ONE = (0x534C, 0x0001)
USBID_TREZOR_CORE = (0x1209, 0x53C1)
USBID_TREZOR_CORE_BOOTLOADER = (0x1209, 0x53C0)


def _usb_ids(model_class: _md.ModelClass) -> tuple[UsbId, ...]:
    if model_class is _md.ModelClass.LEGACY:
        return (USBID_TREZOR_ONE,)
    return (USBID_TREZOR_CORE, USBID_TREZOR_CORE_BOOTLOADER)


def _build(data: _md.ModelData) -> TrezorModel:
    """Build a TrezorModel from a single-source model definition. Constant
    fields (vendors, usb_ids, default_mapping) are injected here rather than
    stored per model."""
    return TrezorModel(
        name=data.name,
        internal_name=data.internal_name,
        minimum_version=data.minimum_version,
        vendors=VENDORS,
        usb_ids=_usb_ids(data.model_class),
        default_mapping=mapping.DEFAULT_MAPPING,
        layout=data.layout.value,
        ble_capable=data.ble_capable,
        aliases=data.aliases,
    )


_BY_INTERNAL = {d.internal_name: _build(d) for d in _registry.ALL}

T1B1 = _BY_INTERNAL["T1B1"]
T2T1 = _BY_INTERNAL["T2T1"]
T2B1 = _BY_INTERNAL["T2B1"]
T3T1 = _BY_INTERNAL["T3T1"]
T3T2 = _BY_INTERNAL["T3T2"]
T3B1 = _BY_INTERNAL["T3B1"]
T3W1 = _BY_INTERNAL["T3W1"]
D001 = _BY_INTERNAL["D001"]
D002 = _BY_INTERNAL["D002"]
D003 = _BY_INTERNAL["D003"]

# ==== model based names ====

TREZOR_ONE = T1B1
TREZOR_T = T2T1
TREZOR_R = T2B1
TREZOR_SAFE3 = T2B1
TREZOR_SAFE5 = T3T1
TREZOR_DISC1 = D001
TREZOR_DISC2 = D002
TREZOR_DISC3 = D003

# deprecated aliases: the discovery boards used to be exposed under DISC1/DISC2,
# but the canonical handle is now the internal name (D001/D002), like every
# other model. Kept for backwards compatibility.
DISC1 = D001
DISC2 = D002
DISC3 = D003

LEGACY_MODELS = frozenset(
    _BY_INTERNAL[d.internal_name]
    for d in _registry.ALL
    if d.model_class is _md.ModelClass.LEGACY
)
CORE_MODELS = frozenset(
    _BY_INTERNAL[d.internal_name]
    for d in _registry.ALL
    if d.model_class is _md.ModelClass.CORE
)
ALL_MODELS = LEGACY_MODELS | CORE_MODELS


def by_name(name: str | None) -> TrezorModel | None:
    """Try to find a TrezorModel by its name.

    This is a fallback function in case `internal_model` is not available. For general
    model detection, prefer `detect()`.
    """
    if name is None:
        return T1B1
    for model in ALL_MODELS:
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
    for model in ALL_MODELS:
        if model.internal_name == name:
            return model
    return None


def unknown_model(name: str | None, internal_name: str | None) -> TrezorModel:
    return TrezorModel(
        name=name or "Unknown",
        internal_name=internal_name or "????",
        minimum_version=(0, 0, 0),
        vendors=VENDORS,
        usb_ids=(),
        default_mapping=mapping.DEFAULT_MAPPING,
        is_unknown=True,
    )


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

    return unknown_model(features.model, features.internal_model)
