# This file is part of the Trezor project.
#
# Copyright (C) 2012-2018 SatoshiLabs and contributors
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

import math

import pytest

from trezorlib import messages as m, misc

ENTROPY_LENGTHS_POW2 = [2 ** l for l in range(10)]
ENTROPY_LENGTHS_POW2_1 = [2 ** l + 1 for l in range(10)]

ENTROPY_LENGTHS = ENTROPY_LENGTHS_POW2 + ENTROPY_LENGTHS_POW2_1


def entropy(data):
    counts = {}
    for c in data:
        counts[c] = counts.get(c, 0) + 1
    e = 0
    for v in counts.values():
        p = v / len(data)
        e -= p * math.log(p, 256)
    return e


@pytest.mark.parametrize("entropy_length", ENTROPY_LENGTHS)
def test_entropy(client, entropy_length):
    with client:
        client.set_expected_responses(
            [m.ButtonRequest(code=m.ButtonRequestType.ProtectCall), m.Entropy()]
        )
        ent = misc.get_entropy(client, entropy_length)
        assert len(ent) == entropy_length
        print("{} bytes: entropy = {}".format(entropy_length, entropy(ent)))
