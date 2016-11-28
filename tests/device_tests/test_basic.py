import unittest
import common

from trezorlib import messages_pb2 as messages

class TestBasic(common.TrezorTest):

    def test_features(self):
        features = self.client.call(messages.Initialize())
        self.assertEqual(features, self.client.features)

    def test_ping(self):
        ping = self.client.call(messages.Ping(message='ahoj!'))
        self.assertEqual(ping, messages.Success(message='ahoj!'))

    def test_device_id_same(self):
        id1 = self.client.get_device_id()
        self.client.init_device()
        id2 = self.client.get_device_id()

        # ID must be at least 12 characters
        self.assertTrue(len(id1) >= 12)

        # Every resulf of UUID must be the same
        self.assertEqual(id1, id2)

    def test_device_id_different(self):
        id1 = self.client.get_device_id()
        self.client.wipe_device()
        id2 = self.client.get_device_id()

        # Device ID must be fresh after every reset
        self.assertNotEqual(id1, id2)

if __name__ == '__main__':
    unittest.main()
