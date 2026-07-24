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

"""Trezor Safe 5 (T3T1) — single-file model definition."""

import hashlib

from . import HashParams, KeySet, Layout, ModelClass, ModelData, keys
from ._shared import TREZOR_CORE_DEV

MODEL = ModelData(
    internal_name="T3T1",
    name="Safe 5",
    hw_model=b"T3T1",
    minimum_version=(2, 7, 2),
    aliases=("safe5", "s5"),
    model_class=ModelClass.CORE,
    layout=Layout.DELIZIA,
    ble_capable=False,
    prod_keys=KeySet(
        production=True,
        boardloader_keys=keys(
            "76af426e61406bad7c077b409c66fde39fb817919313ae1e4c02535c80beed96",
            "619751dc8d2d09d7e5dfb99e41f606debdf419f85a8143e8e5399ea67a3988c7",
            "abf94b6615a7dde2a871f7d62c38efc7d9d8f6010d8846bee636e4f3e658a38c",
        ),
        boardloader_sigs_needed=2,
        bootloader_keys=keys(
            "338b949b7e3b26470d4fe3696fd6fff28757265d14cca48ebf2db97b4f5bc039",
            "28682027730b783201b05a8c9d11685447c17297db71b8a60dc693a44610751d",
            "9fbf31b4e351a4cc81c75995b2257f0a7169268da5a44e94b6a5590d434e32da",
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
