from common import *

from mock_storage import mock_storage

import storage

from trezor import io
from trezor.crypto import random
from trezor.messages import BackupType
from trezor.sdappdata import SdAppData


class TestTrezorSdAppData(unittest.TestCase):

    def setUp(self):
        self.sd = io.SDCard()
        self.sd.power(True)
        self.fs = io.FatFS()
        self.fs.mkfs()
        self.sd.power(False)

    @mock_storage
    def test_set_get(self):
        storage.device.store_mnemonic_secret(b"abcd", BackupType.Bip39)
        appdata = SdAppData("test1")
        for _ in range(16):
            key = random.bytes(128)
            value = random.bytes(1024)
            appdata.set(key, value)
            self.assertEqual(appdata.get(key), value)

    @mock_storage
    def test_set_del_get(self):
        storage.device.store_mnemonic_secret(b"efgh", BackupType.Bip39)
        appdata = SdAppData("test2")
        for _ in range(16):
            key = random.bytes(128)
            value = random.bytes(1024)
            appdata.set(key, value)
            appdata.delete(key)
            with self.assertRaises(KeyError):
                appdata.get(key)

if __name__ == '__main__':
    unittest.main()
