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

import construct as c

from .firmware.sanity_struct import SanityCheckedStruct

LOG = logging.getLogger(__name__)
TREZOR_ROOT_PACKET = b"TRRP"
MLDSA_SIG = c.Bytes(2420)


RingMask = c.BitStruct(
    "_padding" / c.Const(0, c.BitsInteger(5)),
    "ring_2" / c.Flag,
    "ring_1" / c.Flag,
    "ring_0" / c.Flag,
)

Flags = c.BitStruct(
    "_padding" / c.Const(0, c.BitsInteger(6)),
    "is_dangerous" / c.Flag,
    "is_dev_signed" / c.Flag,
)


class RootPacket_AppRing0(SanityCheckedStruct):
    root_ring_0: bytes
    timestamp: int
    sigmask: int
    signature_0: bytes
    signature_1: bytes

    SUBCON = c.Struct(
        "_magic" / c.Const(TREZOR_ROOT_PACKET, c.Bytes(4)),
        "_version" / c.Const(b"\x01", c.Bytes(1)),
        "_ring_mask"
        / c.Const(
            c.Container(ring_2=False, ring_1=False, ring_0=True),
            RingMask,
        ),
        "root_ring_0" / c.Bytes(32),
        "timestamp" / c.Int32ul,
        "flags" / Flags,
        "sigmask" / c.Byte,
        "signature_0" / MLDSA_SIG,
        "signature_1" / MLDSA_SIG,
    )


class RootPacket_AppRing12(SanityCheckedStruct):
    root_ring_1: bytes
    root_ring_2: bytes
    timestamp: int
    sigmask: int
    signature_0: bytes
    signature_1: bytes

    SUBCON = c.Struct(
        "_magic" / c.Const(TREZOR_ROOT_PACKET, c.Bytes(4)),
        "_version" / c.Const(b"\x01", c.Bytes(1)),
        "_ring_mask"
        / c.Const(
            c.Container(ring_2=True, ring_1=True, ring_0=False),
            RingMask,
        ),
        "root_ring_1" / c.Bytes(32),
        "root_ring_2" / c.Bytes(32),
        "timestamp" / c.Int32ul,
        "flags" / Flags,
        "sigmask" / c.Byte,
        "signature_0" / MLDSA_SIG,
        "signature_1" / MLDSA_SIG,
    )
