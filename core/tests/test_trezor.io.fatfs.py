from common import *

from trezor import io


class TestTrezorIoFatfs(unittest.TestCase):

    def setUp(self):
        self.sd = io.SDCard()
        self.sd.power(True)
        self.fs = io.FatFS()
        self.fs.mkfs()
        self.fs.mount()

    def tearDown(self):
        self.fs.unmount()
        self.sd.power(False)

    def test_basic(self):
        # test just the stuff in setup and teardown
        pass

    def test_mkdir(self):
        self.fs.mkdir("/TREZOR")
        s = self.fs.stat("/TREZOR")
        self.assertEqual(s, (0, "---d-", "TREZOR"))

    def test_listdir(self):
        self.fs.mkdir("/DIR")
        with self.fs.open("/FILE.TXT", "w") as f:
            f.write(bytearray(b"test"))
        with self.fs.open("/DIR/FILE2.TXT", "w") as f:
            f.write(bytearray(b"testtest"))
        l = [e for e in self.fs.listdir("/")]
        self.assertEqual(l, [(0, "---d-", "DIR"), (4, "----a", "FILE.TXT")])
        l = [e for e in self.fs.listdir("/DIR")]
        self.assertEqual(l, [(8, "----a", "FILE2.TXT")])

    def test_unlink(self):
        self.fs.mkdir("/DIR")
        with self.fs.open("/FILE.TXT", "w") as f:
            f.write(bytearray(b"test"))
        s = self.fs.stat("/DIR")
        self.assertEqual(s, (0, "---d-", "DIR"))
        s = self.fs.stat("/FILE.TXT")
        self.assertEqual(s, (4, "----a", "FILE.TXT"))
        self.fs.unlink("/DIR")
        self.fs.unlink("/FILE.TXT")
        with self.assertRaises(OSError):
            self.fs.stat("/DIR")
        with self.assertRaises(OSError):
            self.assertRaises(self.fs.stat("/FILE.TXT"))

    def test_rename(self):
        self.fs.mkdir("/DIR")
        with self.fs.open("/FILE.TXT", "w") as f:
            f.write(bytearray(b"test"))
        s = self.fs.stat("/DIR")
        self.assertEqual(s, (0, "---d-", "DIR"))
        s = self.fs.stat("/FILE.TXT")
        self.assertEqual(s, (4, "----a", "FILE.TXT"))
        self.fs.rename("/DIR", "/DIR2")
        self.fs.rename("/FILE.TXT", "/FILE2.TXT")
        with self.assertRaises(OSError):
            self.fs.stat("/DIR")
        with self.assertRaises(OSError):
            self.assertRaises(self.fs.stat("/FILE.TXT"))
        s = self.fs.stat("/DIR2")
        self.assertEqual(s, (0, "---d-", "DIR2"))
        s = self.fs.stat("/FILE2.TXT")
        self.assertEqual(s, (4, "----a", "FILE2.TXT"))

    def test_open_rw(self):
        with self.fs.open("/FILE.TXT", "w") as f:
            f.write(bytearray(b"test"))
        with self.fs.open("/FILE.TXT", "r") as f:
            b = bytearray(100)
            r = f.read(b)
            self.assertEqual(r, 4)
            self.assertEqual(bytes(b[:4]), b"test")

    def test_open_a(self):
        with self.fs.open("/FILE.TXT", "w") as f:
            f.write(bytearray(b"test" * 200))
        with self.fs.open("/FILE.TXT", "a") as f:
            f.seek(800)
            f.write(bytearray(b"TEST" * 200))
        with self.fs.open("/FILE.TXT", "r") as f:
            b = bytearray(2000)
            r = f.read(b)
            self.assertEqual(r, 1600)
            self.assertEqual(bytes(b[:1600]), b"test" * 200 + b"TEST" * 200)

    def test_seek(self):
        with self.fs.open("/FILE.TXT", "w+") as f:
            f.write(bytearray(b"test" * 10))
            f.seek(2)
            b = bytearray(8)
            r = f.read(b)
            self.assertEqual(r, 8)
            self.assertEqual(bytes(b[:8]), b"sttestte")

    def test_truncate(self):
        with self.fs.open("/FILE.TXT", "w") as f:
            f.write(bytearray(b"test" * 100))
        s = self.fs.stat("/FILE.TXT")
        self.assertEqual(s, (400, "----a", "FILE.TXT"))
        with self.fs.open("/FILE.TXT", "a") as f:
            f.seek(111)
            f.truncate()
        s = self.fs.stat("/FILE.TXT")
        self.assertEqual(s, (111, "----a", "FILE.TXT"))


if __name__ == "__main__":
    unittest.main()
