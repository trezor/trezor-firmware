# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api
from trezor import io, utils

STANDARD = trezorui_api.MenuItemIntent.STANDARD
DANGER = trezorui_api.MenuItemIntent.DANGER


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

    # a cancel entry is an ordinary item asking for the `DANGER` intent;
    # it is selected by index like any other.
    ITEMS = [("Alpha", STANDARD), ("Beta", STANDARD), ("Cancel", DANGER)]

    def make_menu(self, items=None):
        if items is None:
            items = self.ITEMS
        layout = trezorui_api.select_menu(
            items=items,
            current=0,
        )
        layout.paint()
        return layout

    def test_select_first_item(self):
        layout = self.make_menu()
        self.assertEqual(click(layout, CENTER_X, SLOT_TOP_Y), 0)

    def test_select_middle_item(self):
        layout = self.make_menu()
        self.assertEqual(click(layout, CENTER_X, SLOT_MIDDLE_Y), 1)

    def test_select_danger_item(self):
        # a `DANGER` entry only looks different; it still returns its index
        layout = self.make_menu()
        self.assertEqual(click(layout, CENTER_X, SLOT_BOTTOM_Y), 2)

    def test_close_button(self):
        layout = self.make_menu()
        # top-right corner button closes the menu without selecting anything
        self.assertIs(
            click(layout, CLOSE_BUTTON_X, CLOSE_BUTTON_Y), trezorui_api.CONFIRMED
        )

    def test_all_standard_items(self):
        # a menu without a `DANGER` entry indexes exactly the same
        items = [("Alpha", STANDARD), ("Beta", STANDARD)]
        layout = self.make_menu(items=items)
        self.assertEqual(click(layout, CENTER_X, SLOT_TOP_Y), 0)
        layout = self.make_menu(items=items)
        self.assertEqual(click(layout, CENTER_X, SLOT_MIDDLE_Y), 1)
        layout = self.make_menu(items=items)
        self.assertIsNone(click(layout, CENTER_X, SLOT_BOTTOM_Y))

    def test_single_button_takes_one_slot(self):
        # a lone button sits in the top slot and does not stretch
        items = [("Cancel", DANGER)]
        layout = self.make_menu(items=items)
        self.assertIsNone(click(layout, CENTER_X, SLOT_BOTTOM_Y))
        layout = self.make_menu(items=items)
        self.assertEqual(click(layout, CENTER_X, SLOT_TOP_Y), 0)

    def test_three_items_fit(self):
        # the cancel entry no longer reserves a slot of its own, so three
        # entries - danger or not - now fit where two plus a cancel used to
        layout = self.make_menu(
            items=[("Alpha", STANDARD), ("Beta", STANDARD), ("Gamma", STANDARD)]
        )
        self.assertEqual(click(layout, CENTER_X, SLOT_BOTTOM_Y), 2)

    def test_buttons_clamped_to_three_slots(self):
        # four entries exceed the three available slots
        with self.assertRaises(NotImplementedError):
            self.make_menu(
                items=[
                    ("Alpha", STANDARD),
                    ("Beta", STANDARD),
                    ("Gamma", STANDARD),
                    ("Delta", STANDARD),
                ]
            )

    def test_too_many_items(self):
        # beyond MAX_MENU_ITEMS the list is rejected before it reaches the layout,
        # so this is an OverflowError rather than this model's NotImplementedError
        with self.assertRaises(OverflowError):
            self.make_menu(items=[("Item", STANDARD)] * 7)

    def test_unknown_intent(self):
        with self.assertRaises(OverflowError):
            self.make_menu(items=[("Alpha", 42)])

    def test_malformed_item(self):
        # each item must be a (label, intent) pair
        with self.assertRaises(ValueError):
            self.make_menu(items=["Alpha"])

    def test_trace(self):
        layout = self.make_menu()
        parts = []
        layout.trace(parts.append)
        trace = "".join(parts)
        self.assertIn('"SelectMenu"', trace)
        for name, _intent in self.ITEMS:
            self.assertIn(name, trace)


if __name__ == "__main__":
    unittest.main()
