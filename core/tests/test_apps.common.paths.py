from common import *
from trezor.utils import ensure
from apps.common.paths import *


class TestPaths(unittest.TestCase):
    def test_is_hardened(self):
        self.assertTrue(is_hardened(H_(44)))
        self.assertTrue(is_hardened(H_(0)))
        self.assertTrue(is_hardened(H_(99999)))

        self.assertFalse(is_hardened(44))
        self.assertFalse(is_hardened(0))
        self.assertFalse(is_hardened(99999))

    def test_path_is_hardened(self):
        self.assertTrue(path_is_hardened([H_(44), H_(1), H_(0)]))
        self.assertTrue(path_is_hardened([H_(0)]))

        self.assertFalse(path_is_hardened([44, H_(44), H_(0)]))
        self.assertFalse(path_is_hardened([0]))
        self.assertFalse(path_is_hardened([H_(44), H_(1), H_(0), H_(0), 0]))


class TestPathSchemas(unittest.TestCase):
    def assertMatch(self, schema, path):
        self.assertTrue(
            schema.match(path),
            "Expected schema {!r} to match path {}".format(
                schema, address_n_to_str(path)
            ),
        )

    def assertMismatch(self, schema, path):
        self.assertFalse(
            schema.match(path),
            "Expected schema {!r} to not match path {}".format(
                schema, address_n_to_str(path)
            ),
        )

    def assertEqualSchema(self, schema_a, schema_b):
        def is_equal(a, b):
            if isinstance(a, range) and isinstance(b, range):
                return a.start == b.start and a.step == b.step and a.stop == b.stop
            return a == b

        ensure(
            all(is_equal(a, b) for a, b in zip(schema_a.schema, schema_b.schema))
            and is_equal(schema_a.trailing_components, schema_b.trailing_components),
            "Schemas differ:\nA = {!r}\nB = {!r}".format(schema_a, schema_b),
        )

    def test_always_never_matching(self):
        paths = [
            [],
            [0],
            [H_(0)],
            [44],
            [H_(44)],
            [H_(44), H_(0), H_(0), 0, 0],
            [H_(44), H_(0), H_(0), H_(0), H_(0)],
            [H_(44), H_(0), H_(0), H_(0), H_(0)] * 10,
        ]
        for path in paths:
            self.assertMatch(SCHEMA_ANY_PATH, path)
            self.assertMismatch(SCHEMA_NO_MATCH, path)

    def test_pattern_fixed(self):
        pattern = "m/44'/0'/0'/0/0"
        schema = PathSchema(pattern, 0)

        self.assertMatch(schema, [H_(44), H_(0), H_(0), 0, 0])

        paths = [
            [],
            [0],
            [H_(0)],
            [44],
            [H_(44)],
            [44, 0, 0, 0, 0],
            [H_(44), H_(0), H_(0), H_(0), H_(0)],
            [H_(44), H_(0), H_(0), H_(0), H_(0)] * 10,
        ]
        for path in paths:
            self.assertMismatch(schema, path)

    def test_ranges_sets(self):
        pattern_ranges = "m/44'/[100-109]'/[0-20]"
        pattern_sets = "m/44'/[100,105,109]'/[0,10,20]"
        schema_ranges = PathSchema(pattern_ranges, 0)
        schema_sets = PathSchema(pattern_sets, 0)

        paths_good = [
            [H_(44), H_(100), 0],
            [H_(44), H_(100), 10],
            [H_(44), H_(100), 20],
            [H_(44), H_(105), 0],
            [H_(44), H_(105), 10],
            [H_(44), H_(105), 20],
            [H_(44), H_(109), 0],
            [H_(44), H_(109), 10],
            [H_(44), H_(109), 20],
        ]
        for path in paths_good:
            self.assertMatch(schema_ranges, path)
            self.assertMatch(schema_sets, path)

        paths_bad = [
            [H_(44), H_(100)],
            [H_(44), H_(100), 0, 0],
            [H_(44), 100, 0],
            [H_(44), 100, H_(0)],
            [H_(44), H_(99), 0],
            [H_(44), H_(110), 0],
            [H_(44), H_(100), 21],
        ]
        for path in paths_bad:
            self.assertMismatch(schema_ranges, path)
            self.assertMismatch(schema_sets, path)

        self.assertMatch(schema_ranges, [H_(44), H_(104), 19])
        self.assertMismatch(schema_sets, [H_(44), H_(104), 19])

    def test_brackets(self):
        pattern_a = "m/[0]'/[0-5]'/[0,1,2]'/[0]/[0-5]/[0,1,2]"
        pattern_b = "m/0'/0-5'/0,1,2'/0/0-5/0,1,2"
        schema_a = PathSchema(pattern_a, 0)
        schema_b = PathSchema(pattern_b, 0)
        self.assertEqualSchema(schema_a, schema_b)

    def test_wildcard(self):
        pattern = "m/44'/0'/*"
        schema = PathSchema(pattern, 0)

        paths_good = [
            [H_(44), H_(0)],
            [H_(44), H_(0), 0],
            [H_(44), H_(0), 0, 1, 2, 3, 4, 5, 6, 7, 8],
        ]
        for path in paths_good:
            self.assertMatch(schema, path)

        paths_bad = [
            [H_(44)],
            [H_(44), H_(0), H_(0)],
            [H_(44), H_(0), 0, 1, 2, 3, 4, 5, 6, 7, H_(8)],
        ]
        for path in paths_bad:
            self.assertMismatch(schema, path)

    def test_substitutes(self):
        pattern_sub = "m/44'/coin_type'/account'/change/address_index"
        pattern_plain = "m/44'/19'/0-100'/0,1/0-1000000"
        schema_sub = PathSchema(pattern_sub, slip44_id=19)
        # use wrong slip44 id to ensure it doesn't affect anything
        schema_plain = PathSchema(pattern_plain, slip44_id=0)

        self.assertEqualSchema(schema_sub, schema_plain)


if __name__ == "__main__":
    unittest.main()
