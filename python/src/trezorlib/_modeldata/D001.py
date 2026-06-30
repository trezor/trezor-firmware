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

"""Discovery board DISC1 (D001) — single-file model definition.

Dev board: it has no dedicated production keys, so its "production" slot reuses
the shared core dev keys (production=False), exactly like firmware/models.py."""

import hashlib

from . import HashParams, Layout, ModelClass, ModelData
from ._shared import TREZOR_CORE_DEV

MODEL = ModelData(
    internal_name="D001",
    name="DISC1",
    hw_model=b"D001",
    minimum_version=(2, 3, 0),
    aliases=(),
    model_class=ModelClass.CORE,
    layout=Layout.BOLT,
    ble_capable=False,
    prod_keys=TREZOR_CORE_DEV,
    dev_keys=TREZOR_CORE_DEV,
    hash_params=HashParams(
        hash_function=hashlib.blake2s,
        chunk_size=1024 * 128,
        padding_byte=None,
    ),
)
