# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils

if utils.USE_APP_LOADING:
    import trezormodui
    import trezorui_api
    from trezor import TR
    from trezor.ui import modui
    from trezor.ui.layouts.menu import MenuResult
    from trezor.ui.modui import pages
    from trezormodui import (
        ADDRESS,
        AMOUNT,
        CONFIRM,
        DANGER,
        DATA,
        DETAILS,
        NOTE,
        STRONG,
        TEXT,
        WARNING,
    )


class Layout:
    """A stand-in for a layout context: entered and left, but never drawn."""

    def __init__(self, kwargs) -> None:
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return None


class Screens:
    """The `trezormodui` screens, recorded instead of drawn, and the limits the
    checks read."""

    def __init__(self) -> None:
        self.calls = []
        self.max_extras = trezormodui.max_extras
        self.MAX_DATA_FIELDS = trezormodui.MAX_DATA_FIELDS

    def _screen(self, name):
        def screen(**kwargs):
            self.calls.append((name, kwargs))
            return Layout(kwargs)

        return screen

    def review(self, **kwargs):
        return self._screen("review")(**kwargs)

    def extra(self, **kwargs):
        return self._screen("extra")(**kwargs)

    def danger(self, **kwargs):
        return self._screen("danger")(**kwargs)


class Answers:
    """An async stand-in for `interact`: records the ButtonRequest names, then
    answers with each of `results` in turn."""

    def __init__(self, *results) -> None:
        self.results = list(results)
        self.names = []

    async def __call__(self, layout, name, *args, **kwargs):
        self.names.append(name)
        return self.results.pop(0)


def run(coro):
    """Run `coro` to completion; the stand-ins never wait."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise AssertionError("the coroutine waited")


class FakeSource:
    """A data source that records every range it is asked for."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.reads = []

    async def read(self, offset: int, length: int) -> bytes:
        self.reads.append((offset, length))
        return self.data[offset : offset + length]


if utils.USE_APP_LOADING:

    class TestFields(unittest.TestCase):
        def test_each_kind_names_what_it_is(self):
            self.assertEqual(
                modui.text("Resource", "Energy"), (TEXT, "Resource", "Energy")
            )
            self.assertEqual(modui.address("To", "TQ"), (ADDRESS, "To", "TQ"))
            self.assertEqual(modui.data("Data", b"\x01"), (DATA, "Data", b"\x01"))
            self.assertEqual(modui.note("Sure?"), (NOTE, None, "Sure?"))
            self.assertEqual(modui.warning("Risky"), (WARNING, None, "Risky"))

        def test_an_amount_joins_its_ticker(self):
            self.assertEqual(
                modui.amount("Amount", "1.5", "TRX"), (AMOUNT, "Amount", "1.5 TRX")
            )

    class TestCheck(unittest.TestCase):
        FACTS = [modui.text("a", "b")]

        def extras(self, offered: int):
            return [modui.Extra("x", self.FACTS)] * offered + [modui.Extra("e", [])]

        def test_each_answer_has_its_own_room_for_extras(self):
            for answer, room in ((CONFIRM, 5), (STRONG, 5), (DETAILS, 4), (DANGER, 0)):
                offered = pages.check(self.FACTS, self.extras(room), answer)
                self.assertEqual(len(offered), room)
                with self.assertRaises(ValueError):
                    pages.check(self.FACTS, self.extras(room + 1), answer)

        def test_an_empty_extra_is_not_offered(self):
            self.assertEqual(pages.check(self.FACTS, self.extras(0), DANGER), [])

        def test_one_data_field_per_list(self):
            two = [modui.data("a", b"\x01"), modui.data("b", b"\x02")]
            with self.assertRaises(ValueError):
                pages.check(two, [], CONFIRM)
            with self.assertRaises(ValueError):
                pages.check(self.FACTS, [modui.Extra("x", two)], CONFIRM)

    class TestPager(unittest.TestCase):
        def test_bytes_in_hand_page_by_chunk(self):
            pager = pages.Pager([modui.text("a", "b"), modui.data("d", bytes(1000))])
            chunks = []
            while True:
                page, last = run(pager.next())
                self.assertEqual(page[0], (TEXT, "a", "b"))
                chunks.append(len(page[1][2]))
                if last:
                    break
            self.assertEqual(chunks, [384, 384, 232])

        def test_a_source_is_read_in_order_each_range_once(self):
            source = FakeSource(bytes(range(256)) * 4)
            field = modui.data_source("d", 1024, source.read)
            pager = pages.Pager([field])
            while not run(pager.next())[1]:
                pass
            self.assertEqual(source.reads, [(0, 384), (384, 384), (768, 256)])

        def test_no_data_is_one_page(self):
            pager = pages.Pager([modui.note("n")])
            self.assertEqual(run(pager.next()), ([(NOTE, None, "n")], True))

    class TestReview(unittest.TestCase):
        def setUp(self):
            self.screens = Screens()
            self.saved = (pages.trezormodui, pages.interact, pages.interact_with_menu)
            pages.trezormodui = self.screens

        def tearDown(self):
            pages.trezormodui, pages.interact, pages.interact_with_menu = self.saved

        def test_a_strong_review_holds_only_on_its_last_page(self):
            pages.interact = Answers(*[trezorui_api.CONFIRMED] * 3)
            facts = [modui.data("d", bytes(1000))]
            run(modui.review("app/send", "Send", facts).confirm_strong())
            reviews = [kwargs for name, kwargs in self.screens.calls]
            self.assertEqual([r["hold"] for r in reviews], [False, False, True])
            self.assertEqual(
                [r["verb"] for r in reviews],
                [TR.buttons__continue, TR.buttons__continue, None],
            )
            # One ButtonRequest per step, on its first page.
            self.assertEqual(pages.interact.names, ["app/send", None, None])

        def test_extras_open_a_menu(self):
            pages.interact_with_menu = Answers(trezorui_api.CONFIRMED)
            extras = [modui.Extra("Account", [modui.text("a", "b")])]
            run(modui.review("s", "t", [modui.text("a", "b")]).extras(extras).confirm())
            self.assertTrue(self.screens.calls[0][1]["menu"])

        def test_details_is_show_all_or_a_yes(self):
            facts = [modui.text("a", "b")]
            pages.interact_with_menu = Answers(MenuResult(None, True))
            self.assertTrue(run(modui.review("s", "t", facts).details()))
            pages.interact_with_menu = Answers(trezorui_api.CONFIRMED)
            self.assertFalse(run(modui.review("s", "t", facts).details()))

        def test_a_danger_is_drawn_as_one(self):
            pages.interact = Answers(trezorui_api.CONFIRMED)
            run(modui.review("s", "t", [modui.note("n")]).confirm_danger())
            self.assertEqual(self.screens.calls[0][0], "danger")

        def test_a_summary_needs_an_amount_or_a_fee(self):
            with self.assertRaises(ValueError):
                run(modui.summary("s", "Send").confirm_strong())


if __name__ == "__main__":
    unittest.main()
