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

import zlib

CHECKSUM_LENGTH = 4


def compute(data: bytes) -> bytes:
    """
    Returns a CRC-32 checksum of the provided `data`.
    """
    return zlib.crc32(data).to_bytes(CHECKSUM_LENGTH, "big")


def is_valid(checksum: bytes, data: bytes) -> bool:
    """
    Checks whether the CRC-32 checksum of the `data` is the same
    as the checksum provided in `checksum`.
    """
    data_checksum = compute(data)
    return checksum == data_checksum
