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
