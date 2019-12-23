from common import *


class TestUnittest(unittest.TestCase):

    def test_debug(self):
        if not __debug__:
            # Fail the test if debug is turned off, because `assert` is not executed then.
            self.assertTrue(False)


if __name__ == "__main__":
    unittest.main()
