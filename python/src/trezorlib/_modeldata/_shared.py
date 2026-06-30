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

"""Key sets shared across multiple models.

Dev keys are identical for every core model, and the legacy dev set is shared
by the One. Keeping them here avoids copying the same blob into every per-model
file. Mirrors ``TREZOR_CORE_DEV`` / ``LEGACY_V3_DEV`` in firmware/models.py."""

from . import KeySet, keys

# Shared dev keys for all STM32-based (core) models.
TREZOR_CORE_DEV = KeySet(
    boardloader_keys=keys(
        "db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d",
        "2152f8d19b791d24453242e15f2eab6cb7cffa7b6a5ed30097960e069881db12",
        "22fc297792f0b6ffc0bfcfdb7edb0c0aa14e025a365ec0e342e86e3829cb74b6",
    ),
    boardloader_sigs_needed=2,
    bootloader_keys=keys(
        "d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48",
        "6355691c178a8ff91007a7478afb955ef7352c63e7b25703984cf78b26e21a56",
        "ee93a4f66f8d16b819bb9beb9ffccdfcdc1412e87fee6a324c2a99a1e0e67148",
    ),
    bootloader_sigs_needed=2,
    secmon_keys=keys(
        "db995fe25169d141cab9bbba92baa01f9f2e1ece7df4cb2ac05190f37fcc1f9d",
        "2152f8d19b791d24453242e15f2eab6cb7cffa7b6a5ed30097960e069881db12",
        "22fc297792f0b6ffc0bfcfdb7edb0c0aa14e025a365ec0e342e86e3829cb74b6",
    ),
    secmon_sigs_needed=2,
    nrf_keys=keys(
        "d759793bbc13a2819a827c76adb6fba8a49aee007f49f2d0992d99b825ad2c48",
        "6355691c178a8ff91007a7478afb955ef7352c63e7b25703984cf78b26e21a56",
    ),
)

# Shared dev keys for the legacy Trezor One (firmware-only signing).
LEGACY_V3_DEV = KeySet(
    firmware_keys=keys(
        "037308e14077161c365dea0f5c80aa6c5dba34719e825bd23ae5f7e7d2988adb0f",
        "039c1b2460e343712e982e0732e7ed17f60de4c933065b7170d99c6e7fe7cc7f4b",
        "03152b37fdf126111274c894c348dcc975b57c115ee24ceb19b5190ac7f7b65173",
    ),
    firmware_sigs_needed=2,
)
