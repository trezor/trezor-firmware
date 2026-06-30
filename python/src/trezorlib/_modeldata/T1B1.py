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

"""Trezor One (T1B1) — single-file model definition."""

import hashlib

from . import HashParams, KeySet, Layout, ModelClass, ModelData, keys
from ._shared import LEGACY_V3_DEV

MODEL = ModelData(
    internal_name="T1B1",
    name="1",
    hw_model=b"T1B1",
    minimum_version=(1, 8, 0),
    aliases=("1", "one"),
    model_class=ModelClass.LEGACY,
    layout=Layout.T1,
    ble_capable=False,
    prod_keys=KeySet(
        production=True,
        firmware_keys=keys(
            "032300c1bb4539fcbfca2590bda3dd2093826f4ae437bddecc1a2e72520764ff7a",
            "0233baeaebc94a2a3e8b11f39a7133dbf427be292fcbceb887d71ef51e85395a19",
            "0357091fa254b55233d0bb4c48e106c91b92fd0788ebed9d3a916719f44c76c015",
        ),
        firmware_sigs_needed=2,
    ),
    dev_keys=LEGACY_V3_DEV,
    hash_params=HashParams(
        hash_function=hashlib.sha256,
        chunk_size=1024 * 64,
        padding_byte=b"\xff",
    ),
)
