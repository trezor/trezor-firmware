from common import *
from trezor.pin import pin_to_int
from trezor import config
from storage import device


class TestConfig(unittest.TestCase):

    def test_counter(self):
        config.init()
        config.wipe()
        for i in range(150):
            self.assertEqual(device.next_u2f_counter(), i)
        device.set_u2f_counter(350)
        for i in range(351, 500):
            self.assertEqual(device.next_u2f_counter(), i)
        device.set_u2f_counter(0)
        self.assertEqual(device.next_u2f_counter(), 1)
        device.set_u2f_counter(None)
        self.assertEqual(device.next_u2f_counter(), 0)


if __name__ == '__main__':
    unittest.main()
