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

from . import models

V1_SIGNATURE_SLOTS = 3

# === KEYS KEPT FOR COMPATIBILITY ===
# use `trezorlib.firmware.models` directly

V1_BOOTLOADER_KEYS = models.LEGACY_V1V2.firmware_keys
V2_BOARDLOADER_KEYS = models.T2T1.boardloader_keys
V2_BOARDLOADER_DEV_KEYS = models.TREZOR_CORE_DEV.boardloader_keys
V2_BOOTLOADER_KEYS = models.T2T1.bootloader_keys
V2_BOOTLOADER_DEV_KEYS = models.TREZOR_CORE_DEV.bootloader_keys

V2_SIGS_REQUIRED = models.T2T1.boardloader_sigs_needed
