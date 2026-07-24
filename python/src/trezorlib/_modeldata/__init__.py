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

"""Unified, single-source-of-truth model data.

This package holds one file per Trezor model. Each file declares a single
``MODEL`` of type :class:`ModelData` carrying *everything* trezorlib needs to
know about that model: identity, release metadata, UI layout, BLE capability,
and firmware-verification keys / hash parameters.

Design constraints that shaped this layout:

* **No protobuf dependency.** This module deliberately imports only the stdlib,
  so it sits *below* both ``trezorlib.models`` (high level, pulls in protobuf
  ``mapping``) and ``trezorlib.firmware.models`` (verification layer). Both can
  consume it without creating an import cycle or dragging protobuf into the
  firmware-parsing path.
* **Constant fields are not stored per model.** ``vendors``, ``usb_ids`` and
  ``default_mapping`` are identical across a model *class* (legacy vs. core), so
  the aggregator injects them; they don't belong in per-model files.
* **Shared dev keys are shared.** Every core model verifies against the same
  ``TREZOR_CORE_DEV`` dev keys, so those live here once, not copied into nine
  files.

Fields are annotated below with their eventual generation source once the
firmware-side codegen exists. Fields marked "sidecar" are NOT present anywhere
in ``core/embed/models`` today and would need a ``[trezorlib]`` block in
``model.toml`` (or a parallel metadata file) to feed the generator.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional, Tuple


def keys(*hexes: str) -> Tuple[bytes, ...]:
    """Helper: turn hex strings into a tuple of key bytes."""
    return tuple(bytes.fromhex(h) for h in hexes)


class ModelClass(Enum):
    """Coarse hardware family. Drives the constant fields the aggregator fills
    in (USB ids, image padding byte, which shared dev key set applies)."""

    LEGACY = "legacy"  # Trezor One
    CORE = "core"  # everything STM32-based


class Layout(Enum):
    """UI layout. Source: the ``layout_*`` feature in ``model.toml``."""

    T1 = "T1"
    BOLT = "Bolt"
    CAESAR = "Caesar"
    DELIZIA = "Delizia"
    ECKHART = "Eckhart"


@dataclass(frozen=True)
class KeySet:
    """Firmware-verification keys for one model.

    Production keys come from ``MODEL_*_KEYS`` in ``model_<NAME>.h``. The
    ``*_sigs_needed`` thresholds and ``nrf_keys`` are NOT in any model file
    today (sidecar). ``production`` is intrinsic to the key set (dev key sets,
    and the dev keys that discovery boards reuse, are not production)."""

    production: bool = False
    boardloader_keys: Tuple[bytes, ...] = ()
    boardloader_sigs_needed: int = -1
    bootloader_keys: Tuple[bytes, ...] = ()
    bootloader_sigs_needed: int = -1
    firmware_keys: Tuple[bytes, ...] = ()
    firmware_sigs_needed: int = -1
    secmon_keys: Tuple[bytes, ...] = ()
    secmon_sigs_needed: int = -1
    nrf_keys: Tuple[bytes, ...] = ()


@dataclass(frozen=True)
class HashParams:
    """Firmware image hashing. Source: ``IMAGE_HASH_*`` / ``IMAGE_CHUNK_SIZE``
    in ``model_<NAME>.h``; ``padding_byte`` follows from ``model_class``."""

    hash_function: Callable
    chunk_size: int
    padding_byte: Optional[bytes]


@dataclass(frozen=True)
class ModelData:
    # --- identity (source: model.toml dir name / MODEL_NAME in header) ---
    internal_name: str
    name: str
    hw_model: bytes
    # --- release / protocol metadata (sidecar: not in firmware files) ---
    minimum_version: Tuple[int, int, int]
    aliases: Tuple[str, ...] = ()
    # --- hardware / UI (source: model.toml features) ---
    model_class: ModelClass = ModelClass.CORE
    layout: Layout = Layout.BOLT
    ble_capable: bool = False
    # --- firmware verification ---
    prod_keys: KeySet = field(default_factory=KeySet)
    dev_keys: KeySet = field(default_factory=KeySet)
    hash_params: Optional[HashParams] = None
