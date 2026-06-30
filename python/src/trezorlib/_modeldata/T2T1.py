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

"""Trezor T (T2T1) — single-file model definition."""

import hashlib

from . import HashParams, KeySet, Layout, ModelClass, ModelData, keys
from ._shared import TREZOR_CORE_DEV

MODEL = ModelData(
    internal_name="T2T1",
    name="T",
    hw_model=b"T2T1",
    minimum_version=(2, 3, 0),
    aliases=("t",),
    model_class=ModelClass.CORE,
    layout=Layout.BOLT,
    ble_capable=False,
    prod_keys=KeySet(
        production=True,
        boardloader_keys=keys(
            "0eb9856be9ba7e972c7f34eac1ed9b6fd0efd172ec00faf0c589759da4ddfba0",
            "ac8ab40b32c98655798fd5da5e192be27a22306ea05c6d277cdff4a3f4125cd8",
            "ce0fcd12543ef5936cf2804982136707863d17295faced72af171d6e6513ff06",
        ),
        boardloader_sigs_needed=2,
        bootloader_keys=keys(
            "c2c87a49c5a3460977fbb2ec9dfe60f06bd694db8244bd4981fe3b7a26307f3f",
            "80d036b08739b846f4cb77593078deb25dc9487aedcf52e30b4fb7cd7024178a",
            "b8307a71f552c60a4cbb317ff48b82cdbf6b6bb5f04c920fec7badf017883751",
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
