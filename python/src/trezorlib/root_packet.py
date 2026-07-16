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

    # ---- higher-level, flag-like abstraction ----

    def has_ring(self, index: int) -> bool:
        """Whether ring `index` is present in the mask."""
        return bool(self.ring_mask & (1 << index))

    @property
    def ring_indices(self) -> list[int]:
        """Ring indices present in the mask, ascending (0..MAX_RINGS-1)."""
        return [i for i in range(self.MAX_RINGS) if self.has_ring(i)]

    def ring(self, index: int) -> bytes:
        """The 32-byte root for ring `index`."""
        if not self.has_ring(index):
            raise KeyError(f"ring {index} not present in mask {self.ring_mask:#04x}")
        # array is stored ascending by ring index; position = set bits below `index`
        pos = bin(self.ring_mask & ((1 << index) - 1)).count("1")
        return self.root_rings[pos]

    @property
    def rings(self) -> dict[int, bytes]:
        """Mapping {ring_index: 32-byte root} for all present rings."""
        return {i: self.ring(i) for i in self.ring_indices}

    def sanity_check(self, image: bytes, errors: t.Sequence[str] = ()) -> None:
        _errors: list[str] = list(errors)

        # `root_rings` length must equal the number of set mask bits
        expected = bin(self.ring_mask).count("1")
        if len(self.root_rings) != expected:
            _errors.append(
                f"root_rings length {len(self.root_rings)} does not match "
                f"mask popcount {expected} (mask {self.ring_mask:#04x})"
            )

        # no bits set above MAX_RINGS
        if self.ring_mask >> self.MAX_RINGS:
            _errors.append(
                f"ring_mask {self.ring_mask:#04x} has bits set above "
                f"MAX_RINGS={self.MAX_RINGS}"
            )

        super().sanity_check(image, _errors)
