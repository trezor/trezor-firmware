# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api
from trezor import io, utils


def click(layout, x, y):
    layout.touch_event(io.TOUCH_START, x, y)
    if layout.touch_event(io.TOUCH_END, x, y) is not None:
        # the layout is done, fetch the result
        return layout.return_value()
    return None


# Coordinates are specific to the Bolt layout (240x240 screen).
# The menu shows at most 3 buttons in fixed 50px slots stacked from the
# top of the content area.
CENTER_X = 120
SLOT_TOP_Y = 81
SLOT_MIDDLE_Y = 137
SLOT_BOTTOM_Y = 193
CLOSE_BUTTON_X = 212
CLOSE_BUTTON_Y = 28


@unittest.skipUnless(utils.UI_LAYOUT == "BOLT", "Bolt layout only")
class TestSelectMenu(unittest.TestCase):

    ITEMS = ["Alpha", "Beta"]

    def make_menu(self, items=None, cancel="Cancel"):
        if items is None:
            items = self.ITEMS
        layout = trezorui_api.select_menu(
            items=items,
            current=0,
            cancel=cancel,
        )
        layout.paint()
        return layout

    def test_select_first_item(self):
        layout = self.make_menu()
        self.assertEqual(click(layout, CENTER_X, SLOT_TOP_Y), 0)

    def test_select_last_item(self):
        layout = self.make_menu()
        self.assertEqual(click(layout, CENTER_X, SLOT_MIDDLE_Y), 1)

    def test_select_cancel_item(self):
        layout = self.make_menu()
        self.assertIs(click(layout, CENTER_X, SLOT_BOTTOM_Y), trezorui_api.CANCELLED)

    def test_close_button(self):
        layout = self.make_menu()
        # top-right corner button closes the menu without cancelling
        self.assertIs(
            click(layout, CLOSE_BUTTON_X, CLOSE_BUTTON_Y), trezorui_api.CONFIRMED
        )

    def test_no_cancel_item(self):
        layout = self.make_menu(cancel=None)
        self.assertEqual(click(layout, CENTER_X, SLOT_TOP_Y), 0)
        layout = self.make_menu(cancel=None)
        self.assertEqual(click(layout, CENTER_X, SLOT_MIDDLE_Y), 1)

    def test_single_button_takes_one_slot(self):
        # a lone button sits in the top slot and does not stretch
        layout = self.make_menu(items=[])
        self.assertIsNone(click(layout, CENTER_X, SLOT_BOTTOM_Y))
        layout = self.make_menu(items=[])
        self.assertIs(click(layout, CENTER_X, SLOT_TOP_Y), trezorui_api.CANCELLED)

    def test_buttons_clamped_to_three_slots(self):
        # three choices plus a cancel button would exceed the three slots
        with self.assertRaises(NotImplementedError):
            self.make_menu(items=["Alpha", "Beta", "Gamma"])
        # four choices alone also exceed the limit
        with self.assertRaises(NotImplementedError):
            self.make_menu(items=["Alpha", "Beta", "Gamma", "Delta"], cancel=None)

    def test_trace(self):
        layout = self.make_menu()
        parts = []
        layout.trace(parts.append)
        trace = "".join(parts)
        self.assertIn('"SelectMenu"', trace)
        for name in self.ITEMS + ["Cancel"]:
            self.assertIn(name, trace)


if __name__ == "__main__":
    unittest.main()
