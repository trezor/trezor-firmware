from common import *

from trezor import strings


class TestStrings(unittest.TestCase):

    def test_format_amount(self):
        VECTORS = [
            (123456, 3, "123.456"),
            (4242, 7, "0.0004242"),
            (-123456, 3, "-123.456"),
            (-4242, 7, "-0.0004242"),
        ]
        for v in VECTORS:
            self.assertEqual(strings.format_amount(v[0], v[1]), v[2])

    def test_format_plural(self):
        VECTORS = [
            ("We need {count} more {plural}", 3, "share", "We need 3 more shares"),
            ("We need {count} more {plural}", 1, "share", "We need 1 more share"),
            ("We need {count} more {plural}", 1, "candy", "We need 1 more candy"),
            ("We need {count} more {plural}", 7, "candy", "We need 7 more candies"),
            ("We need {count} more {plural}", 1, "hash", "We need 1 more hash"),
            ("We need {count} more {plural}", 2, "hash", "We need 2 more hashes"),
            ("We need {count} more {plural}", 1, "fuzz", "We need 1 more fuzz"),
            ("We need {count} more {plural}", 2, "fuzz", "We need 2 more fuzzes"),
        ]
        for v in VECTORS:
            self.assertEqual(strings.format_plural(v[0], v[1], v[2]), v[3])

        with self.assertRaises(ValueError):
            strings.format_plural("Hello", 1, "share")

    def test_format_duration_ms(self):
        VECTORS = [
            (0, "0 milliseconds"),
            (1, "1 millisecond"),
            (999, "999 milliseconds"),
            (1000, "1 second"),
            (2345, "2 seconds"),
            (59999, "59 seconds"),
            (60 * 1000, "1 minute"),
            (119 * 1000, "1 minute"),
            (120 * 1000, "2 minutes"),
            (59 * 60 * 1000, "59 minutes"),
            (60 * 60 * 1000, "1 hour"),
            (119 * 60 * 1000, "1 hour"),
            (3 * 60 * 60 * 1000, "3 hours"),
            (48 * 60 * 60 * 1000, "48 hours"),
        ]

        for v in VECTORS:
            self.assertEqual(strings.format_duration_ms(v[0]), v[1])


if __name__ == '__main__':
    unittest.main()
