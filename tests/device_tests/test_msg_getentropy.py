# This file is part of the TREZOR project.
#
# Copyright (C) 2012-2016 Marek Palatinus <slush@satoshilabs.com>
# Copyright (C) 2012-2016 Pavol Rusnak <stick@satoshilabs.com>
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import unittest
import common
import math

import trezorlib.messages_pb2 as proto
import trezorlib.types_pb2 as proto_types

def entropy(data):
    counts = {}
    for c in data:
        if c in counts:
            counts[c] += 1
        else:
            counts[c] = 1
    e = 0
    for _, v in counts.items():
        p = 1.0 * v / len(data)
        e -= p * math.log(p, 256)
    return e

class TestMsgGetentropy(common.TrezorTest):

    def test_entropy(self):
        for l in [0, 1, 2, 3, 4, 5, 8, 9, 16, 17, 32, 33, 64, 65, 128, 129, 256, 257, 512, 513, 1024]:
            with self.client:
                self.client.set_expected_responses([proto.ButtonRequest(code=proto_types.ButtonRequest_ProtectCall), proto.Entropy()])
                ent = self.client.get_entropy(l)
                self.assertTrue(len(ent) == l)
                print('entropy = ', entropy(ent))

if __name__ == '__main__':
    unittest.main()
