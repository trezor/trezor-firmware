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

"""Trezor Safe 7 (T3W1) — single-file model definition.

Exercises every axis: secmon keys, NRF/BLE keys, BLE capability, Eckhart
layout, 256K hash chunk. Mirrors core/embed/models/T3W1/."""

import hashlib

from . import HashParams, KeySet, Layout, ModelClass, ModelData, keys
from ._shared import TREZOR_CORE_DEV

MODEL = ModelData(
    internal_name="T3W1",
    name="Safe 7",
    hw_model=b"T3W1",
    minimum_version=(2, 9, 3),
    aliases=(),
    model_class=ModelClass.CORE,
    layout=Layout.ECKHART,
    ble_capable=True,
    prod_keys=KeySet(
        production=True,
        boardloader_keys=keys(
            "e8912f81b3e780ee650ed3856db5326e0b9eff10364b339193e7a8f10f7621b9",
            "bde70a38eee633d26f434eee2f536df457b8deb8bd988294f4a0c8d9054903d2",
            "a85b601dfbda1d22ccb5dd492d26034d87f67f2a0b8584b7774439461fc471a9",
        ),
        boardloader_sigs_needed=2,
        bootloader_keys=keys(
            "320e111e9dded5fe7f5d41fd372ef0e91b2dfa4c6cdc9fe5221bfb16aaf91775",
            "2e349f8d06b2334262ecb603ed04cb5a7cc0b660ebe3cd5c2972b5cd1f38ef85",
            "ab0d3f91a4adf744719dba661783ec549f73a4e45457cb6d02752a40fb63d3bf",
        ),
        bootloader_sigs_needed=2,
        secmon_keys=keys(
            "7da3dd4769fef0f9489d5ff7fba8be122aef0f60778302557ba2cc67ff2a6d9e",
            "4ae3bf88b0e5226322d867432940265b4bef46e5c45b64730e26ca32ee653e0b",
            "6c1640f38d037c57e86960863505ef70ff60f98157440cf25f1c133b4a15960e",
        ),
        secmon_sigs_needed=2,
        nrf_keys=keys(
            "d1bad5e8c73dfe183ba1bd5464b2c96f1d1de66d53c95026d17169148d096f3e",
            "585f0635efc6518c490228a72ae1f5d0808ebe77f1c12516eb6d525821eb1e21",
            "065ee19b0de4eec3be70938935313ca2949cc3808b2bf3ad7ef0ac419a974191",
        ),
    ),
    dev_keys=TREZOR_CORE_DEV,
    hash_params=HashParams(
        hash_function=hashlib.sha256,
        chunk_size=1024 * 256,
        padding_byte=None,
    ),
)
