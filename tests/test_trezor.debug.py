from common import *

from trezor import debug

class TestDebug(unittest.TestCase):

    def test_memaccess(self):
        data = debug.memaccess(0, 1024)
        # don't access contents (will segfault), just the length of the returned data
        self.assertEqual(len(data), 1024)

if __name__ == '__main__':
    unittest.main()
