from common import *

from trezorio import sdcard, fatfs


class TestTrezorIoFatfs(unittest.TestCase):
    def setUp(self):
        sdcard.power_on()
        fatfs.mkfs()
        fatfs.mount()

    def tearDown(self):
        fatfs.unmount()
        sdcard.power_off()

    def _filename(self, suffix=""):
        return "FILE%s.TXT" % suffix

    def _dirname(self, suffix=""):
        return "TREZOR%s" % suffix

    def test_basic(self):
        # test just the stuff in setup and teardown
        pass

    def test_mkdir(self):
        fatfs.mkdir("/%s" % self._dirname())
        s = fatfs.stat("/%s" % self._dirname())
        self.assertEqual(s, (0, "---d-", self._dirname()))

    def test_listdir(self):
        fatfs.mkdir("/%s" % self._dirname())
        with fatfs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        with fatfs.open("/%s/%s" % (self._dirname(), self._filename("2")), "w") as f:
            f.write(bytearray(b"testtest"))
        l = [e for e in fatfs.listdir("/")]
        self.assertEqual(
            l, [(0, "---d-", self._dirname()), (4, "----a", self._filename())]
        )
        l = [e for e in fatfs.listdir("/%s" % self._dirname())]
        self.assertEqual(l, [(8, "----a", self._filename("2"))])

    def test_unlink(self):
        fatfs.mkdir("/%s" % self._dirname())
        with fatfs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        s = fatfs.stat("/%s" % self._dirname())
        self.assertEqual(s, (0, "---d-", self._dirname()))
        s = fatfs.stat("/%s" % self._filename())
        self.assertEqual(s, (4, "----a", self._filename()))
        fatfs.unlink("/%s" % self._dirname())
        fatfs.unlink("/%s" % self._filename())
        with self.assertRaises(fatfs.FatFSError):
            fatfs.stat("/%s" % self._dirname())
        with self.assertRaises(fatfs.FatFSError):
            self.assertRaises(fatfs.stat("/%s" % self._filename()))

    def test_rename(self):
        fatfs.mkdir("/%s" % self._dirname())
        with fatfs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        s = fatfs.stat("/%s" % self._dirname())
        self.assertEqual(s, (0, "---d-", self._dirname()))
        s = fatfs.stat("/%s" % self._filename())
        self.assertEqual(s, (4, "----a", self._filename()))
        fatfs.rename("/%s" % self._dirname(), "/%s" % self._dirname("2"))
        fatfs.rename("/%s" % self._filename(), "/%s" % self._filename("2"))
        with self.assertRaises(fatfs.FatFSError):
            fatfs.stat("/%s" % self._dirname())
        with self.assertRaises(fatfs.FatFSError):
            self.assertRaises(fatfs.stat("/%s" % self._filename()))
        s = fatfs.stat("/%s" % self._dirname("2"))
        self.assertEqual(s, (0, "---d-", self._dirname("2")))
        s = fatfs.stat("/%s" % self._filename("2"))
        self.assertEqual(s, (4, "----a", self._filename("2")))

    def test_open_rw(self):
        with fatfs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test"))
        with fatfs.open("/%s" % self._filename(), "r") as f:
            b = bytearray(100)
            r = f.read(b)
            self.assertEqual(r, 4)
            self.assertEqual(bytes(b[:4]), b"test")

    def test_open_a(self):
        with fatfs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test" * 200))
        with fatfs.open("/%s" % self._filename(), "a") as f:
            f.seek(800)
            f.write(bytearray(b"TEST" * 200))
        with fatfs.open("/%s" % self._filename(), "r") as f:
            b = bytearray(2000)
            r = f.read(b)
            self.assertEqual(r, 1600)
            self.assertEqual(bytes(b[:1600]), b"test" * 200 + b"TEST" * 200)

    def test_seek(self):
        with fatfs.open("/%s" % self._filename(), "w+") as f:
            f.write(bytearray(b"test" * 10))
            f.seek(2)
            b = bytearray(8)
            r = f.read(b)
            self.assertEqual(r, 8)
            self.assertEqual(bytes(b[:8]), b"sttestte")

    def test_truncate(self):
        with fatfs.open("/%s" % self._filename(), "w") as f:
            f.write(bytearray(b"test" * 100))
        s = fatfs.stat("/%s" % self._filename())
        self.assertEqual(s, (400, "----a", self._filename()))
        with fatfs.open("/%s" % self._filename(), "a") as f:
            f.seek(111)
            f.truncate()
        s = fatfs.stat("/%s" % self._filename())
        self.assertEqual(s, (111, "----a", self._filename()))


class TestTrezorIoFatfsLfn(TestTrezorIoFatfs):
    def _filename(self, suffix=""):
        return "reallylongfilename%s.textfile" % suffix

    def _dirname(self, suffix=""):
        return "reallylongdirname%s" % suffix


class TestTrezorIoFatfsMounting(unittest.TestCase):
    MOUNTED_METHODS = [
        ("open", ("hello.txt", "w")),
        ("listdir", ("",)),
        ("mkdir", ("testdir",)),
        ("unlink", ("hello.txt",)),
        ("stat", ("testdir",)),
        ("rename", ("testdir", "newdir")),
        ("setlabel", ("label",)),
    ]
    UNMOUNTED_METHODS = [
        ("mkfs", ()),
    ]

    def setUp(self):
        sdcard.power_on()

    def tearDown(self):
        sdcard.power_off()

    def test_mount_unmount(self):
        fatfs.mkfs()

        self.assertFalse(fatfs.is_mounted())
        fatfs.mount()
        self.assertTrue(fatfs.is_mounted())
        fatfs.mount()
        self.assertTrue(fatfs.is_mounted())
        fatfs.unmount()
        self.assertFalse(fatfs.is_mounted())

    def test_no_filesystem(self):
        # trash FAT table
        sdcard.write(0, bytes([0xFF] * sdcard.BLOCK_SIZE))

        self.assertFalse(fatfs.is_mounted())
        try:
            fatfs.mount()
            self.fail("should have raised")
        except fatfs.FatFSError as e:
            self.assertIsInstance(e, fatfs.NoFilesystem)
            # check that the proper error code is set on the NoFilesystem subclass
            self.assertEqual(e.args[0], fatfs.FR_NO_FILESYSTEM)
        self.assertFalse(fatfs.is_mounted())

    def test_mounted(self):
        fatfs.mkfs()
        fatfs.mount()
        self.assertTrue(fatfs.is_mounted())

        for name, call in self.MOUNTED_METHODS:
            function = getattr(fatfs, name)
            function(*call)

        for name, call in self.UNMOUNTED_METHODS:
            function = getattr(fatfs, name)
            try:
                function(*call)
                self.fail("should have raised")
            except fatfs.FatFSError as e:
                self.assertEqual(e.args[0], fatfs.FR_LOCKED)

    def test_unmounted(self):
        fatfs.unmount()
        fatfs.mkfs()
        self.assertFalse(fatfs.is_mounted())

        for name, call in self.UNMOUNTED_METHODS:
            function = getattr(fatfs, name)
            function(*call)
            self.assertFalse(fatfs.is_mounted())

        for name, call in self.MOUNTED_METHODS:
            function = getattr(fatfs, name)
            try:
                function(*call)
                self.fail("should have raised")
            except fatfs.FatFSError as e:
                self.assertIsInstance(e, fatfs.NotMounted)
                # check that the proper error code is set on the NotMounted subclass
                self.assertEqual(e.args[0], fatfs.FR_NOT_READY)


class TestTrezorIoFatfsAndSdcard(unittest.TestCase):
    def test_sd_power(self):
        sdcard.power_off()
        self.assertFalse(fatfs.is_mounted())
        self.assertRaises(fatfs.FatFSError, fatfs.mount)

        sdcard.power_on()
        self.assertFalse(fatfs.is_mounted())
        fatfs.mkfs()
        fatfs.mount()
        self.assertTrue(fatfs.is_mounted())

        sdcard.power_off()
        self.assertFalse(fatfs.is_mounted())


if __name__ == "__main__":
    unittest.main()
