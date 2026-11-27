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
        AMOUNT,
        CONFIRM,
        DANGER,
        DETAILS,
        NOTE,
        STRONG,
        TEXT,
    )


class Layout:
    """A stand-in for a layout context: entered and left, but never drawn."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return None


class Screens:
    """The `trezormodui` screens, recorded instead of drawn; anything else is
    the real module's."""

    def __init__(self) -> None:
        self.calls = []

    def __getattr__(self, name):
        return getattr(trezormodui, name)

    def _record(self, name, kwargs):
        self.calls.append((name, kwargs))
        return Layout()

    def review(self, **kwargs):
        return self._record("review", kwargs)

    def extra(self, **kwargs):
        return self._record("extra", kwargs)

    def danger(self, **kwargs):
        return self._record("danger", kwargs)


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
    """A text source that records every range it is asked for."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.reads = []

    async def read(self, offset: int, length: int) -> bytes:
        self.reads.append((offset, length))
        return self.data[offset : offset + length]


def text_source(text: str, label: str = "d"):
    """A `text_source` field over `text`, and its source."""
    source = FakeSource(text.encode())
    return modui.text_source(label, len(source.data), source.read), source


def read_all(pager) -> "list[str]":
    """The values of every page the pager gives, to the last."""
    values = []
    while True:
        page, last = run(pager.next())
        values.append(page[0][2])
        if last:
            return values


if utils.USE_APP_LOADING:

    class TestFields(unittest.TestCase):
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

        def test_a_review_needs_a_fact(self):
            with self.assertRaises(ValueError):
                pages.check([], [], CONFIRM)

        def test_one_text_source_per_review(self):
            one = [text_source("a")[0]]
            pages.check(one, [], CONFIRM)
            with self.assertRaises(ValueError):
                pages.check(one * 2, [], CONFIRM)

        def test_a_text_source_cannot_be_in_an_extra(self):
            one = [text_source("a")[0]]
            with self.assertRaises(ValueError):
                pages.check(self.FACTS, [modui.Extra("x", one)], CONFIRM)

    class TestPager(unittest.TestCase):
        def test_each_fact_is_a_page_and_a_text_source_a_page_per_chunk(self):
            field, _ = text_source("x" * 2000)
            pager = pages.Pager([modui.text("a", "b"), field, modui.note("n")])
            self.assertEqual(run(pager.next()), ([(TEXT, "a", "b")], False))
            chunks = [run(pager.next()) for _ in range(3)]
            self.assertEqual([len(page[0][2]) for page, _ in chunks], [768, 768, 464])
            self.assertEqual("".join(page[0][2] for page, _ in chunks), "x" * 2000)
            self.assertFalse(any(last for _, last in chunks))
            # Only the last fact is the last page.
            self.assertEqual(run(pager.next()), ([(NOTE, None, "n")], True))

        def test_a_source_is_read_in_order_each_range_once(self):
            field, source = text_source("x" * 2000)
            read_all(pages.Pager([field]))
            self.assertEqual(source.reads, [(0, 768), (768, 768), (1536, 464)])

        def test_a_character_cut_by_a_chunk_goes_to_the_next_page(self):
            # "é" is two bytes: the first chunk ends between them.
            text = "x" * 767 + "é" + "y" * 10
            field, _ = text_source(text)
            chunks = read_all(pages.Pager([field]))
            self.assertEqual(chunks, ["x" * 767, "é" + "y" * 10])

        def test_text_that_is_not_utf8_is_refused(self):
            # Bad bytes inside the text, and a character cut by its end.
            for data in (b"ab\xff" + b"c" * 800, "é".encode()[:1]):
                source = FakeSource(data)
                field = modui.text_source("d", len(data), source.read)
                with self.assertRaises(ValueError):
                    read_all(pages.Pager([field]))

    class TestReview(unittest.TestCase):
        def setUp(self):
            self.screens = Screens()
            self.saved = (pages.trezormodui, pages.interact, pages.interact_with_menu)
            pages.trezormodui = self.screens

        def tearDown(self):
            pages.trezormodui, pages.interact, pages.interact_with_menu = self.saved

        def test_a_strong_review_holds_only_on_its_last_page(self):
            pages.interact = Answers(*[trezorui_api.CONFIRMED] * 3)
            facts = [text_source("x" * 2000)[0]]
            run(modui.review("app/send", "Send", facts).confirm_strong())
            reviews = [kwargs for name, kwargs in self.screens.calls]
            self.assertEqual([r["hold"] for r in reviews], [False, False, True])
            self.assertEqual(
                [r["verb"] for r in reviews],
                [TR.buttons__continue, TR.buttons__continue, None],
            )
            # Every page sends the step's ButtonRequest.
            self.assertEqual(pages.interact.names, ["app/send"] * 3)

        def test_only_a_yes_counts_as_one(self):
            facts = [modui.text("a", "b")]
            for answer in ("confirm", "confirm_strong", "confirm_danger"):
                pages.interact = Answers(trezorui_api.INFO)
                with self.assertRaises(RuntimeError):
                    run(getattr(modui.review("s", "t", facts), answer)())

        def test_a_menu_value_answers_only_details(self):
            facts = [modui.text("a", "b")]
            extras = [modui.Extra("Account", facts)]
            pages.interact_with_menu = Answers(MenuResult(None, True))
            with self.assertRaises(RuntimeError):
                run(modui.review("s", "t", facts).extras(extras).confirm())

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
