# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor.ui import display
from trezorui_api import backlight_set


class TestDisplay(unittest.TestCase):
    def test_refresh(self):
        display.refresh()

    def test_bar(self):
        display.bar(0, 0, 10, 10, 0xFFFF)

    def test_orientation(self):
        for o in [0, 90, 180, 270]:
            display.orientation(o)

    def test_backlight(self):
        for b in range(256):
            backlight_set(b)

    def test_raw(self):
        pass

    def test_save(self):
        pass


if __name__ == "__main__":
    unittest.main()
