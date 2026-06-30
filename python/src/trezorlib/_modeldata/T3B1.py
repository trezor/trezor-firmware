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

"""Trezor Safe 3 / rev2 (T3B1) — single-file model definition."""

import hashlib

from . import HashParams, KeySet, Layout, ModelClass, ModelData, keys
from ._shared import TREZOR_CORE_DEV

MODEL = ModelData(
    internal_name="T3B1",
    name="Safe 3",
    hw_model=b"T3B1",
    minimum_version=(2, 3, 0),
    aliases=(),
    model_class=ModelClass.CORE,
    layout=Layout.CAESAR,
    ble_capable=False,
    prod_keys=KeySet(
        production=True,
        boardloader_keys=keys(
            "bbc21adbc1b44d6bfe10c5223de33c28429e52680707d3249007ed42dcc5be13",
            "22e42a301f3b6ff4f2e6926bce4359e83fc83f0f4a84a7338959c1fd0e29dc13",
            "7f478f5fb78d8c054b720d8104bf2f6487e452402458979b5525c290dc344d32",
        ),
        boardloader_sigs_needed=2,
        bootloader_keys=keys(
            "41d9884801377cff04b0b459fc9b56af1b51f47343a3a6e4fdc1eacabcad7756",
            "23ec4ec4674d68ac5431e8ba84d7ac24cb5a66702ec565014d164a72182a66c7",
            "8a7dac53e1be46607231920b0c71056a27be16b67a2fc0d8644d5f8708a28dd1",
        ),
        bootloader_sigs_needed=2,
    ),
    dev_keys=TREZOR_CORE_DEV,
    hash_params=HashParams(
        hash_function=hashlib.sha256,
        chunk_size=1024 * 128,
        padding_byte=None,
    ),
)
