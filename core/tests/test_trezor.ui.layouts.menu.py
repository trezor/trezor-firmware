# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api
from trezor.ui.layouts import menu as menu_module
from trezor.ui.layouts.menu import (
    Menu,
    MenuLeaf,
    MenuResult,
    cancel_leaf,
    confirm_with_menu,
    interact_with_menu,
    leaf_from_layout,
    show_menu,
)
from trezor.wire import ActionCancelled

STANDARD = trezorui_api.MenuItemIntent.STANDARD
DANGER = trezorui_api.MenuItemIntent.DANGER


# These tests never build a layout and never render anything.
#
# `menu.py` reaches the screen through exactly two module globals:
#
#     import trezorui_api                             # select_menu() builds a layout
#     from trezor.ui.layouts.common import interact   # runs it, returns what the user did
#
# `MenuTestCase` replaces both for the duration of each test, which cuts the
# wire above the UI: no LayoutObj is allocated, no display or event loop is
# needed, and the tests run on any model. `FakeApi` stands in for what is
# *shown*, the scripted `interact()` for what the user *does* about it.


class FakeLayout:
    """Stand-in for a `LayoutContext`.

    `menu.py` only ever uses a layout as `with layout_factory() as obj:` before
    handing it to `interact()` - which is faked as well - so nothing here is
    ever placed, painted or asked for a result.
    """

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeApi:
    """Replaces `trezorui_api` inside `menu.py`.

    `select_menu()` records what it was asked to show instead of building a
    layout, so `self.shown` becomes the assertion surface for navigation: which
    menus appeared, in what order, with which entry preselected.

    The sentinels are the *real* ones on purpose. `menu.py` compares them by
    identity (`result is trezorui_api.CANCELLED`) and the tests import the real
    module directly, so both sides have to be looking at the same objects.

    Faking this also keeps the file model-agnostic - e.g. the real Bolt `select_menu`
    refuses more than three entries, this one has no limit.

    This enables us to test the data structure and control flow of the menu system without ever touching the screen or event loop.
    """

    CONFIRMED = trezorui_api.CONFIRMED
    CANCELLED = trezorui_api.CANCELLED
    INFO = trezorui_api.INFO
    BACK = trezorui_api.BACK
    MenuItemIntent = trezorui_api.MenuItemIntent

    def __init__(self):
        self.shown = []

    def select_menu(self, items, current):
        self.shown.append((items, current))
        return FakeLayout()


def value_leaf(name, value, intent=STANDARD):
    """A leaf that produces `value`, without going through a layout."""

    async def _interact():
        return value

    return MenuLeaf(name, _interact, intent=intent)


def info_leaf(name, intent=STANDARD):
    """A leaf that resumes the tree, as the information-only entries do."""
    return value_leaf(name, None, intent=intent)


class MenuTestCase(unittest.TestCase):
    def setUp(self):
        # `menu.py` resolves `trezorui_api` and `interact` from its own module
        # dict at call time, so rebinding the entries there redirects the calls.
        # Only `menu.py` sees the fakes; every other module keeps the real ones.
        self.api = FakeApi()
        self._real_api = menu_module.trezorui_api
        self._real_interact = menu_module.interact
        menu_module.trezorui_api = self.api

    def tearDown(self):
        menu_module.trezorui_api = self._real_api
        menu_module.interact = self._real_interact

    def script(self, *results):
        """Make `interact()` hand out `results`, one per call, in order.

        This is the second half of the fake: `FakeApi` decides what is "shown",
        this decides what the user does about it. `script(1, CONFIRMED)` reads
        as "pick the entry at index 1, then close the menu".

        The real `interact()` cannot run here at all - it starts the layout,
        paints it and then suspends on the event loop until a touch arrives.

        Only leaves built by `leaf_from_layout()` consume a slot; the
        `value_leaf()` helpers above are plain coroutines that never call
        `interact()`.

        The long parameter list exists only so that one fake matches all four
        call shapes in `menu.py`, some positional and some by keyword.
        """
        pending = list(results)

        async def _interact(
            layout, br_name=None, br_code=None, raise_on_cancel=None, layout_type=None
        ):
            if not pending:
                raise AssertionError("interact() called more often than scripted")
            return pending.pop(0)

        menu_module.interact = _interact
        self.pending = pending

    def assertScriptConsumed(self):
        """Assert the code asked for exactly as many interactions as scripted.

        `self.pending` is the same list the fake pops from, so anything left
        over means the code stopped early, while asking for one too many raises
        inside the fake. Together they pin down the *number* of interactions,
        not just the final result.
        """
        self.assertEqual(len(self.pending), 0)

    def labels(self, index=0):
        """Labels of the `index`-th menu that was shown."""
        items, _current = self.api.shown[index]
        return [name for name, _intent in items]


class TestMenu(MenuTestCase):
    def test_defaults(self):
        root = Menu()
        self.assertEqual(root.name, "")
        self.assertEqual(root.children, ())

    def test_children_are_a_tuple(self):
        # the tree is built once and never mutated afterwards
        children = [info_leaf("Alpha")]
        root = Menu(children)
        self.assertIsInstance(root.children, tuple)
        children.append(info_leaf("Beta"))
        self.assertEqual(len(root.children), 1)

    def test_subtree_is_always_standard(self):
        self.assertIs(Menu().intent, STANDARD)


class TestShowMenu(MenuTestCase):
    def test_closing_the_root_produces_no_value(self):
        self.script(trezorui_api.CONFIRMED)
        self.assertIsNone(await_result(show_menu(Menu([info_leaf("Alpha")]))))
        self.assertEqual(len(self.api.shown), 1)
        self.assertScriptConsumed()

    def test_items_carry_name_and_intent(self):
        root = Menu([info_leaf("Alpha"), value_leaf("Stop", "x", intent=DANGER)])
        self.script(trezorui_api.CONFIRMED)
        await_result(show_menu(root))
        self.assertEqual(self.api.shown[0][0], [("Alpha", STANDARD), ("Stop", DANGER)])
        self.assertEqual(self.api.shown[0][1], 0)

    def test_leaf_value_leaves_the_tree(self):
        leaf = value_leaf("Beta", "beta")
        root = Menu([info_leaf("Alpha"), leaf])
        self.script(1)  # select the second entry
        result = await_result(show_menu(root))
        self.assertIsInstance(result, MenuResult)
        self.assertIs(result.leaf, leaf)
        self.assertEqual(result.value, "beta")
        # the leaf ended the tree, so the menu was shown exactly once
        self.assertEqual(len(self.api.shown), 1)
        self.assertScriptConsumed()

    def test_leaf_returning_none_resumes_the_tree(self):
        root = Menu([info_leaf("Alpha"), info_leaf("Beta")])
        # open the second entry, then close the menu it returns to
        self.script(1, trezorui_api.CONFIRMED)
        self.assertIsNone(await_result(show_menu(root)))
        self.assertEqual(len(self.api.shown), 2)
        # the entry that was just visited is preselected on the way back
        self.assertEqual(self.api.shown[0][1], 0)
        self.assertEqual(self.api.shown[1][1], 1)
        self.assertScriptConsumed()

    def test_walks_into_a_submenu(self):
        leaf = value_leaf("Gamma", "gamma")
        root = Menu([Menu([leaf], name="Sub"), info_leaf("Alpha")])
        self.script(0, 0)  # into the submenu, then its only entry
        result = await_result(show_menu(root))
        self.assertIs(result.leaf, leaf)
        self.assertEqual(self.labels(0), ["Sub", "Alpha"])
        self.assertEqual(self.labels(1), ["Gamma"])
        self.assertScriptConsumed()

    def test_closing_a_submenu_returns_to_its_parent(self):
        root = Menu([info_leaf("Alpha"), Menu([info_leaf("Gamma")], name="Sub")])
        # into the submenu, close it, then close the root
        self.script(1, trezorui_api.CONFIRMED, trezorui_api.CONFIRMED)
        self.assertIsNone(await_result(show_menu(root)))
        self.assertEqual(len(self.api.shown), 3)
        self.assertEqual(self.labels(1), ["Gamma"])
        # back at the root, with the submenu preselected
        self.assertEqual(self.labels(2), ["Alpha", "Sub"])
        self.assertEqual(self.api.shown[2][1], 1)
        self.assertScriptConsumed()

    def test_nested_leaf_value_leaves_the_whole_tree(self):
        leaf = value_leaf("Deep", "deep")
        root = Menu([Menu([Menu([leaf], name="Inner")], name="Outer")])
        self.script(0, 0, 0)
        result = await_result(show_menu(root))
        self.assertIs(result.leaf, leaf)
        self.assertEqual(result.value, "deep")

    def test_unexpected_result_is_rejected(self):
        # `select_menu` returns an index, or CONFIRMED when closed - nothing else
        self.script(trezorui_api.INFO)
        with self.assertRaises(RuntimeError):
            await_result(show_menu(Menu([info_leaf("Alpha")])))


class TestLeafFromLayout(MenuTestCase):
    def leaf(self, **kwargs):
        return leaf_from_layout("Alpha", lambda: FakeLayout(), **kwargs)

    def test_result_is_discarded_by_default(self):
        self.script("payload")
        self.assertIsNone(await_result(self.leaf()._interact()))

    def test_result_is_returned_when_asked_for(self):
        self.script("payload")
        leaf = self.leaf(return_result=True)
        self.assertEqual(await_result(leaf._interact()), "payload")

    def test_cancelling_resumes_the_tree(self):
        # `raise_on_cancel` is None by default, so cancelling yields the sentinel;
        # it must not reach the caller as if it were a value
        self.script(trezorui_api.CANCELLED)
        leaf = self.leaf(return_result=True)
        self.assertIsNone(await_result(leaf._interact()))

    def test_cancelling_inside_a_tree_shows_the_menu_again(self):
        root = Menu([self.leaf(return_result=True)])
        self.script(0, trezorui_api.CANCELLED, trezorui_api.CONFIRMED)
        self.assertIsNone(await_result(show_menu(root)))
        self.assertEqual(len(self.api.shown), 2)
        self.assertScriptConsumed()

    def test_intent_defaults_to_standard(self):
        self.assertIs(self.leaf().intent, STANDARD)

    def test_intent_is_independent_of_the_result(self):
        # an entry may look dangerous and still produce a value
        leaf = self.leaf(return_result=True, intent=DANGER)
        self.assertIs(leaf.intent, DANGER)
        self.script("payload")
        self.assertEqual(await_result(leaf._interact()), "payload")


class TestCancelLeaf(MenuTestCase):
    def test_intent_is_danger(self):
        self.assertIs(cancel_leaf("Cancel").intent, DANGER)

    def test_raises_without_confirmation(self):
        self.script()
        with self.assertRaises(ActionCancelled):
            await_result(cancel_leaf("Cancel")._interact())

    def test_raises_the_given_exception(self):
        self.script()
        with self.assertRaises(EOFError):
            await_result(cancel_leaf("Cancel", EOFError)._interact())

    def test_declining_the_confirmation_resumes_the_tree(self):
        self.script(trezorui_api.CANCELLED)
        leaf = cancel_leaf("Cancel", confirm=lambda: FakeLayout())
        self.assertIsNone(await_result(leaf._interact()))
        self.assertScriptConsumed()

    def test_accepting_the_confirmation_raises(self):
        self.script(trezorui_api.CONFIRMED)
        leaf = cancel_leaf("Cancel", confirm=lambda: FakeLayout())
        with self.assertRaises(ActionCancelled):
            await_result(leaf._interact())

    def test_unexpected_confirmation_result_is_rejected(self):
        self.script(trezorui_api.INFO)
        leaf = cancel_leaf("Cancel", confirm=lambda: FakeLayout())
        with self.assertRaises(RuntimeError):
            await_result(leaf._interact())


class TestInteractWithMenu(MenuTestCase):
    def test_main_result_is_returned(self):
        self.script(trezorui_api.CONFIRMED)
        result = await_result(
            interact_with_menu(FakeLayout(), Menu([info_leaf("Alpha")]), None)
        )
        self.assertIs(result, trezorui_api.CONFIRMED)
        self.assertEqual(len(self.api.shown), 0)

    def test_info_opens_the_menu_and_comes_back(self):
        # main -> INFO, menu closed, main again -> CONFIRMED
        self.script(trezorui_api.INFO, trezorui_api.CONFIRMED, trezorui_api.CONFIRMED)
        result = await_result(
            interact_with_menu(FakeLayout(), Menu([info_leaf("Alpha")]), None)
        )
        self.assertIs(result, trezorui_api.CONFIRMED)
        self.assertEqual(len(self.api.shown), 1)
        self.assertScriptConsumed()

    def test_menu_value_is_returned_instead_of_the_main_result(self):
        leaf = value_leaf("Beta", "beta")
        self.script(trezorui_api.INFO, 0)
        result = await_result(interact_with_menu(FakeLayout(), Menu([leaf]), None))
        self.assertIsInstance(result, MenuResult)
        self.assertIs(result.leaf, leaf)
        self.assertEqual(result.value, "beta")
        self.assertScriptConsumed()


class TestConfirmWithMenu(MenuTestCase):
    def test_confirmed_is_accepted(self):
        self.script(trezorui_api.CONFIRMED)
        self.assertIsNone(
            await_result(
                confirm_with_menu(FakeLayout(), Menu([info_leaf("Alpha")]), None)
            )
        )

    @unittest.skipUnless(__debug__, "assertions are stripped in optimized builds")
    def test_other_results_are_rejected(self):
        self.script(trezorui_api.BACK)
        with self.assertRaises(AssertionError):
            await_result(
                confirm_with_menu(FakeLayout(), Menu([info_leaf("Alpha")]), None)
            )


if __name__ == "__main__":
    unittest.main()
