from common import *
from apps.common import storage
from storage import mock_storage
from trezor.crypto import random
from trezor.messages import BackupType

from trezor import io
from trezor.sdkvs import SdKvs


class TestTrezorSdKvs(unittest.TestCase):

    def setUp(self):
        self.sd = io.SDCard()
        self.sd.power(True)
        self.fs = io.FatFS()
        self.fs.mkfs()
        self.sd.power(False)

    @mock_storage
    def test_put_get(self):
        storage.device.store_mnemonic_secret(b"abcd", BackupType.Bip39)
        kvs = SdKvs("test1")
        for _ in range(16):
            key = random.bytes(128)
            value = random.bytes(1024)
            kvs.put(key, value)
            self.assertEqual(kvs.get(key), value)

    @mock_storage
    def test_put_del_get(self):
        storage.device.store_mnemonic_secret(b"abcd", BackupType.Bip39)
        kvs = SdKvs("test2")
        for _ in range(16):
            key = random.bytes(128)
            value = random.bytes(1024)
            kvs.put(key, value)
            kvs.delete(key)
            with self.assertRaises(KeyError):
                kvs.get(key)

if __name__ == '__main__':
    unittest.main()
