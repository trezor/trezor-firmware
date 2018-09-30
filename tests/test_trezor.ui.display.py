from common import *

from trezor.ui import display


class TestDisplay(unittest.TestCase):

    def test_clear(self):
        display.clear()

    def test_refresh(self):
        display.refresh()

    def test_bar(self):
        display.bar(0, 0, 10, 10, 0xFFFF)

    def test_bar_radius(self):
        display.bar_radius(0, 0, 10, 10, 0xFFFF, 0x0000, 16)

    def test_image(self):
        pass

    def test_icon(self):
        pass

    def test_text(self):
        display.text(120, 120, 'Test', 0, 0xFFFF, 0x0000)

    def test_text_center(self):
        display.text_center(120, 120, 'Test', 0, 0xFFFF, 0x0000)

    def test_text_right(self):
        display.text_right(120, 120, 'Test', 0, 0xFFFF, 0x0000)

    def test_text_width(self):
        display.text_width('Test', 0)

    def test_qrcode(self):
        display.qrcode(0, 0, 'Test', 4)

    def test_loader(self):
        display.loader(333, 0, 0xFFFF, 0x0000)

    def test_orientation(self):
        for o in [0, 90, 180, 270]:
            display.orientation(o)

    def test_backlight(self):
        for b in range(256):
            display.backlight(b)

    def test_offset(self):
        for x in range(-4, 5):
            for y in range(-4, 5):
                o = (x * 57, y * 57)
                display.offset(o)
                o2 = display.offset()
                self.assertEqual(o, o2)

    def test_raw(self):
        pass

    def test_save(self):
        pass


if __name__ == '__main__':
    unittest.main()
