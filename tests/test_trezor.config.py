from common import *

from trezor.crypto import random

from trezor import config

class TestConfig(unittest.TestCase):

    def test_wipe(self):
        config.wipe()
        config.set(0, 0, b'hello')
        config.set(1, 1, b'world')
        v0 = config.get(0, 0)
        v1 = config.get(1, 1)
        self.assertEqual(v0, b'hello')
        self.assertEqual(v1, b'world')
        config.wipe()
        v0 = config.get(0, 0)
        v1 = config.get(1, 1)
        self.assertIsNone(v0)
        self.assertIsNone(v1)

    def test_set_get(self):
        config.wipe()
        for _ in range(128):
           appid, key = random.uniform(256), random.uniform(256)
           value = random.bytes(128)
           config.set(appid, key, value)
           value2 = config.get(appid, key)
           self.assertEqual(value, value2)

    def test_get_default(self):
        config.wipe()
        for _ in range(128):
           appid, key = random.uniform(256), random.uniform(256)
           value = random.bytes(128)
           value2 = config.get(appid, key, value)
           self.assertEqual(value, value2)

if __name__ == '__main__':
    unittest.main()
