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

"""Trezor Safe 3 (T2B1) — single-file model definition."""

import hashlib

from . import HashParams, KeySet, Layout, ModelClass, ModelData, keys
from ._shared import TREZOR_CORE_DEV

MODEL = ModelData(
    internal_name="T2B1",
    name="Safe 3",
    hw_model=b"T2B1",
    minimum_version=(2, 6, 3),
    aliases=("r", "safe3", "s3"),
    model_class=ModelClass.CORE,
    layout=Layout.CAESAR,
    ble_capable=False,
    prod_keys=KeySet(
        production=True,
        boardloader_keys=keys(
            "549a45557008d5518a9a151dc6a3568cf73830a7fe419f2626d9f30d024b2bec",
            "c16c7027f8a3962607bf24cdec2e3cd2344e1f6071e8260b3dda52b1a5107cb7",
            "87180f933178b2832bee2d7046c7f4b98300ca7d7fb2e4567169c8730a1c4020",
        ),
        boardloader_sigs_needed=2,
        bootloader_keys=keys(
            "bf4e6f004fcb32cec683f22c88c1a86c1518c6de8ac97002d84a63bea3e375dd",
            "d2def691c1e9d809d8190cf7af935c10688f68983479b4ee9abac19104878ec1",
            "07c85134946bf89fa19bdc2c5e5ff9ce01296508ee0863d0ff6d63331d1a2516",
        ),
        bootloader_sigs_needed=2,
    ),
    dev_keys=TREZOR_CORE_DEV,
    hash_params=HashParams(
        hash_function=hashlib.blake2s,
        chunk_size=1024 * 128,
        padding_byte=None,
    ),
)
