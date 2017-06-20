from common import *

from trezor.crypto import random

from trezor import config

class TestConfig(unittest.TestCase):

    def test_init(self):
        config.init()
        config.init()
        config.init()

    def test_wipe(self):
        config.init()
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
        self.assertEqual(v0, bytes())
        self.assertEqual(v1, bytes())

    def test_set_get(self):
        config.init()
        config.wipe()
        for _ in range(64):
            appid, key = random.uniform(256), random.uniform(256)
            value = random.bytes(128)
            config.set(appid, key, value)
            value2 = config.get(appid, key)
            self.assertEqual(value, value2)

    def test_get_default(self):
        config.init()
        config.wipe()
        for _ in range(64):
            appid, key = random.uniform(256), random.uniform(256)
            value = config.get(appid, key)
            self.assertEqual(value, bytes())

if __name__ == '__main__':
    unittest.main()
