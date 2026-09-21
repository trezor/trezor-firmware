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

from __future__ import annotations

# Curve25519 points of small order.
# Test vectors from https://www.ietf.org/archive/id/draft-irtf-cfrg-cpace-21.html#name-test-vectors-for-g_x25519sc.
# Vector u3_256 is the vector u3 with last bit set to 1. This bit is ignored as specified in RFC 7748. More vectors
# are tested in the CPace unit tests - they are not included here for performance reasons
LOW_ORDER_POINTS = {
    "u0": "0000000000000000000000000000000000000000000000000000000000000000",
    "u1": "0100000000000000000000000000000000000000000000000000000000000000",
    "u2": "ecffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff7f",
    "u3_256": "e0eb7a7c3b41b8ae1656e3faf19fc46ada098deb9c32b1fd866205165f49b880",
}
