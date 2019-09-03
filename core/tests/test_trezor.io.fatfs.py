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

    def _filename(self, suffix=""):
        return "FILE%s.TXT" % suffix

    def _dirname(self, suffix=""):
        return "TREZOR%s" % suffix

    def test_basic(self):
        # test just the stuff in setup and teardown
        pass

    def test_mkdir(self):
        self.fs.mkdir("/%s" % self._dirname())
        s = self.fs.stat("/%s" % self._dirname())
        self.assertEqual(s, (0, "---d-", self._dirname()))

    def test_listdir(self):
        self.fs.mkdir("/%s" % self._dirname())
        with self.fs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        with self.fs.open("/%s/%s" % (self._dirname(), self._filename("2")), "w") as f:
            f.write(bytearray(b"testtest"))
        l = [e for e in self.fs.listdir("/")]
        self.assertEqual(l, [(0, "---d-", self._dirname()), (4, "----a", self._filename())])
        l = [e for e in self.fs.listdir("/%s" % self._dirname())]
        self.assertEqual(l, [(8, "----a", self._filename("2"))])

    def test_unlink(self):
        self.fs.mkdir("/%s" % self._dirname())
        with self.fs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        s = self.fs.stat("/%s" % self._dirname())
        self.assertEqual(s, (0, "---d-", self._dirname()))
        s = self.fs.stat("/%s" % self._filename())
        self.assertEqual(s, (4, "----a", self._filename()))
        self.fs.unlink("/%s" % self._dirname())
        self.fs.unlink("/%s" % self._filename())
        with self.assertRaises(OSError):
            self.fs.stat("/%s" % self._dirname())
        with self.assertRaises(OSError):
            self.assertRaises(self.fs.stat("/%s" % self._filename()))

    def test_rename(self):
        self.fs.mkdir("/%s" % self._dirname())
        with self.fs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        s = self.fs.stat("/%s" % self._dirname())
        self.assertEqual(s, (0, "---d-", self._dirname()))
        s = self.fs.stat("/%s" % self._filename())
        self.assertEqual(s, (4, "----a", self._filename()))
        self.fs.rename("/%s" % self._dirname(), "/%s" % self._dirname("2"))
        self.fs.rename("/%s" % self._filename(), "/%s" % self._filename("2"))
        with self.assertRaises(OSError):
            self.fs.stat("/%s" % self._dirname())
        with self.assertRaises(OSError):
            self.assertRaises(self.fs.stat("/%s" % self._filename()))
        s = self.fs.stat("/%s" % self._dirname("2"))
        self.assertEqual(s, (0, "---d-", self._dirname("2")))
        s = self.fs.stat("/%s" % self._filename("2"))
        self.assertEqual(s, (4, "----a", self._filename("2")))

    def test_open_rw(self):
        with self.fs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        with self.fs.open("/%s" % self._filename(), "r") as f:
            b = bytearray(100)
            r = f.read(b)
            self.assertEqual(r, 4)
            self.assertEqual(bytes(b[:4]), b"test")

    def test_open_a(self):
        with self.fs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test" * 200))
        with self.fs.open("/%s" % self._filename(), "a") as f:
            f.seek(800)
            f.write(bytearray(b"TEST" * 200))
        with self.fs.open("/%s" % self._filename(), "r") as f:
            b = bytearray(2000)
            r = f.read(b)
            self.assertEqual(r, 1600)
            self.assertEqual(bytes(b[:1600]), b"test" * 200 + b"TEST" * 200)

    def test_seek(self):
        with self.fs.open("/%s" % self._filename(), "w+") as f:
            f.write(bytearray(b"test" * 10))
            f.seek(2)
            b = bytearray(8)
            r = f.read(b)
            self.assertEqual(r, 8)
            self.assertEqual(bytes(b[:8]), b"sttestte")

    def test_truncate(self):
        with self.fs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test" * 100))
        s = self.fs.stat("/%s" % self._filename())
        self.assertEqual(s, (400, "----a", self._filename()))
        with self.fs.open("/%s" % self._filename(), "a") as f:
            f.seek(111)
            f.truncate()
        s = self.fs.stat("/%s" % self._filename())
        self.assertEqual(s, (111, "----a", self._filename()))


class TestTrezorIoFatfsLfn(TestTrezorIoFatfs):

    def _filename(self, suffix=""):
        return "reallylongfilename%s.textfile" % suffix

    def _dirname(self, suffix=""):
        return "reallylongdirname%s" % suffix


if __name__ == "__main__":
    unittest.main()
