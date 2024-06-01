from common import *  # isort:skip

from trezor import io
from trezor.crypto import hashlib


class TestTrezorIoFlashArea(unittest.TestCase):
    def test_firmware_hash(self):
        area = io.flash_area.FIRMWARE
        area.erase()
        self.assertEqual(
            area.hash(0, area.size()),
            b"\xd2\xdb\x90\xa7jV6\xa7\x00N\xc3\xb4\x8eq\xa9U\xe0\xcb\xb2\xcbZo\xd7\xae\x9f\xbe\xf8F\xbc\x16l\x8c",
        )
        self.assertEqual(
            area.hash(0, area.size(), b"0123456789abcdef"),
            b"\xa0\x93@\x98\xa6\x80\xdb\x07m\xdf~\xe2'E\xf1\x19\xd8\xfd\xa4`\x10H\xf0_\xdbf\xa6N\xdd\xc0\xcf\xed",
        )

    def test_write(self):
        # let's trash the firmware :shrug:
        area = io.flash_area.FIRMWARE
        size = area.size()

        area.write(0, b"")
        area.write(1024, b"")
        area.write(size, b"")
        with self.assertRaises(ValueError):
            area.write(size + 16, b"")

        # fill whole area
        area.write(0, b"\x01" * size)
        # do it again
        area.write(0, b"\x01" * size)
        # can't write more
        with self.assertRaises(ValueError):
            area.write(0, b"\x01" * (size + 16))

        with self.assertRaises(ValueError):
            area.write(1, b"\x01" * size)

    def test_overwrite(self):
        area = io.flash_area.FIRMWARE
        size = area.size()

        area.erase()
        area.write(0, b"\x00" * 1024)

        # try writing the same thing
        area.write(0, b"\x00" * 1024)

        # try writing some ones
        with self.assertRaises(ValueError):
            area.write(0, b"\x01" * 1024)

    def test_read_write(self):
        area = io.flash_area.FIRMWARE
        size = area.size()
        area.erase()

        buf = bytearray(256)
        for i in range(256):
            buf[i] = i

        for start in range(0, size, 256):
            area.write(start, buf)

        all_data = bytearray(size)
        area.read(0, all_data)
        for i in range(size):
            # avoid super-slow assertEqual
            if i % 256 != all_data[i]:
                self.fail(f"at {i} expected {i % 256}, found {all_data[i]}")

        chunk = bytearray(1024)
        for start in range(0, size, 1024):
            area.read(start, chunk)
            for j in range(1024):
                # avoid super-slow assertEqual
                if (start + j) % 256 != chunk[j]:
                    self.fail(
                        f"at {start + j} expected {(start + j) % 256}, found {chunk[j]}"
                    )

    def test_hash(self):
        area = io.flash_area.FIRMWARE
        size = area.size()


        all_data = bytearray(size)
        for i in range(size):
            all_data[i] = i % 256

        hasher = hashlib.blake2s()
        hasher.update(all_data)
        digest = hasher.digest()
        digest2 = area.hash(0, size)
        self.assertEqual(digest, digest2)

        hasher = hashlib.blake2s()
        digest = hasher.digest()
        digest2 = area.hash(0, 0)
        self.assertEqual(digest, digest2)

        hasher = hashlib.blake2s()
        hasher.update(all_data[1024:2048])
        digest = hasher.digest()
        digest2 = area.hash(1024, 1024)
        self.assertEqual(digest, digest2)


if __name__ == "__main__":
    unittest.main()
