# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils


class TestUtils(unittest.TestCase):
    def test_chunks(self):
        c = list(utils.chunks(range(100), 7))
        for i in range(15):
            # need to check start, stop, step attrs until https://github.com/micropython/micropython/issues/2600 is resolved
            self.assertEqual(c[i].start, i * 7)
            self.assertEqual(c[i].stop, 100 if (i == 14) else (i + 1) * 7)
            self.assertEqual(c[i].step, 1)

    def test_truncate_utf8(self):
        self.assertEqual(utils.truncate_utf8("", 3), "")
        self.assertEqual(utils.truncate_utf8("a", 3), "a")
        self.assertEqual(utils.truncate_utf8("ab", 3), "ab")
        self.assertEqual(utils.truncate_utf8("abc", 3), "abc")
        self.assertEqual(utils.truncate_utf8("abcd", 3), "abc")
        self.assertEqual(utils.truncate_utf8("abcde", 3), "abc")
        self.assertEqual(utils.truncate_utf8("a\u0123", 3), "a\u0123")  # b'a\xc4\xa3'
        self.assertEqual(utils.truncate_utf8("a\u1234", 3), "a")  # b'a\xe1\x88\xb4'
        self.assertEqual(utils.truncate_utf8("ab\u0123", 3), "ab")  # b'ab\xc4\xa3'
        self.assertEqual(utils.truncate_utf8("ab\u1234", 3), "ab")  # b'ab\xe1\x88\xb4'
        self.assertEqual(utils.truncate_utf8("abc\u0123", 3), "abc")  # b'abc\xc4\xa3'
        self.assertEqual(
            utils.truncate_utf8("abc\u1234", 3), "abc"
        )  # b'abc\xe1\x88\xb4'
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 0), ""
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 1), ""
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 2), ""
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 3), "\u1234"
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 4), "\u1234"
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 5), "\u1234"
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 6), "\u1234\u5678"
        )  # b'\xe1\x88\xb4\xe5\x99\xb8
        self.assertEqual(
            utils.truncate_utf8("\u1234\u5678", 7), "\u1234\u5678"
        )  # b'\xe1\x88\xb4\xe5\x99\xb8

    def test_firmware_hash(self):
        if utils.INTERNAL_MODEL in (  # pylint: disable=internal-model-tuple-comparison
            "D002",
            "T3W1",
        ):
            self.assertEqual(
                utils.firmware_hash(),
                b"R\x17\x04\xaaC\x12\x8e\xbb\xa3RP\x83'J\x899'\xc2[\xa8\xac\x8a\x100&\x06\xba\xa2'C\xdb\x19",
            )
            self.assertEqual(
                utils.firmware_hash(b"0123456789abcdef"),
                b"\xc3?\x7f\x0c0\xf1\xb8\xe5]0\xb7\xfd\x05!\xde\xab\xb6^\xd2R\xba\x18nw\x0c\x99\xc9\x1a(\x8b\xb1\xeb",
            )
        else:
            self.assertEqual(
                utils.firmware_hash(),
                b"\xd2\xdb\x90\xa7jV6\xa7\x00N\xc3\xb4\x8eq\xa9U\xe0\xcb\xb2\xcbZo\xd7\xae\x9f\xbe\xf8F\xbc\x16l\x8c",
            )
            self.assertEqual(
                utils.firmware_hash(b"0123456789abcdef"),
                b"\xa0\x93@\x98\xa6\x80\xdb\x07m\xdf~\xe2'E\xf1\x19\xd8\xfd\xa4`\x10H\xf0_\xdbf\xa6N\xdd\xc0\xcf\xed",
            )


if __name__ == "__main__":
    unittest.main()
