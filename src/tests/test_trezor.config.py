import sys
sys.path.append('..')
sys.path.append('../lib')
import unittest

from trezor import config
from trezor.crypto import random

class TestConfig(unittest.TestCase):

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
