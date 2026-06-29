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

import logging
import typing as t

import construct as c

from .firmware.sanity_struct import SanityCheckedStruct

LOG = logging.getLogger(__name__)
TREZOR_ROOT_PACKET = b"TRRP"
MLDSA_SIG = c.Bytes(2420)


class RootPacket(SanityCheckedStruct):
    NAME: t.ClassVar[str] = "root packet"

    MAX_RINGS: t.ClassVar[int] = 3

    ring_mask: int
    timestamp: int
    sigmask: int
    root_rings: list[bytes]
    signature_0: bytes
    signature_1: bytes

    SUBCON = c.Struct(
        "_magic" / c.Const(TREZOR_ROOT_PACKET, c.Bytes(4)),
        "_version" / c.Const(b"\x01", c.Bytes(1)),
        "ring_mask" / c.Byte,
        "timestamp" / c.Int32ul,
        "sigmask" / c.Byte,
        "root_rings" / c.Array(lambda ctx: bin(ctx.ring_mask).count("1"), c.Bytes(32)),
        "signature_0" / MLDSA_SIG,
        "signature_1" / MLDSA_SIG,
    )
