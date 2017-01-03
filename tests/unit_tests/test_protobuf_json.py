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

import common
import unittest

from trezorlib.protobuf_json import json2pb, pb2json
import trezorlib.messages_pb2 as msg


class TestProtobufJson(unittest.TestCase):

    def test_pb2json(self):
        m = msg.Features()
        m.device_id = '1234'
        j = pb2json(m)
        self.assertEqual(j, {'device_id': u'1234'} )


if __name__ == '__main__':
    unittest.main()
