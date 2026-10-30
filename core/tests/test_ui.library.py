# flake8: noqa: F403,F405
from common import *  # isort:skip

import trezorui_api
from trezor import TR, loop
from trezor.ui import Shutdown
from trezor.ui.library import (
    CANCELLED,
    CONFIRMED,
    SHOW_DETAILS,
    confirm,
    run,
    success,
    verify,
)
from trezor.ui.library.fields import (
    ADDRESS,
    AMOUNT,
    DATA,
    DATA_CHUNK_BYTES,
    NOTE,
    TEXT,
    WARNING,
    Pager,
    button_request_name,
    details_items,
    has_warning,
    items,
    notes,
    set_data_puller,
    values,
)
from trezor.wire import ActionCancelled, context
from trezor.wire.errors import DataError

from apps.extapp.session import Session

APP = "tron.trezor.com"

# A decoded fact, as an app sends it: `(kind, label, value)`.
TEXT_FACT = (TEXT, "Recipient", "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE")
AMOUNT_FACT = (AMOUNT, "Amount", "1.5 TRX")
ADDRESS_FACT = (ADDRESS, "From", "TQn9Y2khEsLJW1ChVWFMSMeRDow5KcbLSE")
DATA_FACT = (DATA, "Data", (3, 0, b"\x01\x02\xff"))
NOTE_FACT = (NOTE, None, "Only send to people you trust.")
WARNING_FACT = (WARNING, None, "This cannot be undone.")

FACTS = [TEXT_FACT, AMOUNT_FACT]
EXTRAS = [("Account info", [(TEXT, "Account", "TRX #1")])]

# Decoded requests, one per `TrezorUiEnum` discriminant.
REVIEW = (0, "send", "Send", FACTS, EXTRAS, False)
REVIEW_FINAL = (0, "send", "Send", FACTS, EXTRAS, True)
DANGER = (1, "risky", "Risky", FACTS)
DETAILS = (2, "details", "Details", FACTS)
VERIFY_ADDRESS = (3, "address", ADDRESS_FACT[2], "TRX #1", "m/44'/195'/0'/0/0")
VERIFY_PUBKEY = (4, "pubkey", "02abc", None, None)
DONE = (5, "done", "All done")


class Screen:
    """An async stand-in for one screen function: records its call, then answers."""

    def __init__(self) -> None:
        self.calls = []
        self.result = None
        self.error = None

    async def __call__(self, *args):
        self.calls.append(args)
        if self.error is not None:
            raise self.error
        return self.result


class Layout:
    """A stand-in for a layout context: entered and left, but never drawn."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, tb):
        return None


class Layouts:
    """The `trezorui_api` factories `review()` draws with, recorded instead."""

    # the decision `review()` compares against, as the real module's
    CONFIRMED = trezorui_api.CONFIRMED

    def __init__(self) -> None:
        self.calls = []

    def confirm_action(self, **kwargs):
        self.calls.append(kwargs)
        return Layout()


class TestFieldKinds(unittest.TestCase):
    def test_discriminants(self):
        # the wire's `FieldKind`, as the renderers take it
        self.assertEqual(TEXT, 0)
        self.assertEqual(AMOUNT, 1)
        self.assertEqual(ADDRESS, 2)
        self.assertEqual(DATA, 3)
        self.assertEqual(NOTE, 4)
        self.assertEqual(WARNING, 5)


class TestButtonRequestName(unittest.TestCase):
    def test_app_id_is_the_prefix(self):
        self.assertEqual(
            button_request_name("tron.trezor.com", "send"), "tron.trezor.com/send"
        )

    def test_step_is_never_bare(self):
        name = button_request_name(APP, "confirm")
        self.assertEqual(name, f"{APP}/confirm")
        self.assertNotEqual(name, "confirm")

    def test_empty_step(self):
        self.assertEqual(button_request_name(APP, ""), f"{APP}/")


class TestItems(unittest.TestCase):
    def test_items_keep_order_and_kind(self):
        # `(label, value, kind)`, in the order the app sent them
        self.assertEqual(
            items([TEXT_FACT, ADDRESS_FACT]),
            [
                ("Recipient", TEXT_FACT[2], TEXT),
                ("From", ADDRESS_FACT[2], ADDRESS),
            ],
        )

    def test_sentences_have_no_key(self):
        self.assertEqual(
            items([NOTE_FACT, WARNING_FACT]),
            [
                (None, NOTE_FACT[2], NOTE),
                (None, WARNING_FACT[2], WARNING),
            ],
        )

    def test_data_value_is_its_current_chunk(self):
        # only the renderers turn data into hex; the item keeps the bytes
        self.assertEqual(items([DATA_FACT]), [(DATA_FACT[1], b"\x01\x02\xff", DATA)])


class TestDetailsItems(unittest.TestCase):
    def test_bytes_become_hex(self):
        self.assertEqual(
            details_items([DATA_FACT]),
            [("0102ff", True)],
        )

    def test_only_data_is_mono(self):
        # an address keeps the plain style, as core's own details screens do
        self.assertEqual(
            details_items([TEXT_FACT, AMOUNT_FACT, ADDRESS_FACT, NOTE_FACT]),
            [
                (TEXT_FACT[2], False),
                (AMOUNT_FACT[2], False),
                (ADDRESS_FACT[2], False),
                (NOTE_FACT[2], False),
            ],
        )

    def test_label_is_dropped(self):
        self.assertEqual(details_items([TEXT_FACT]), [(TEXT_FACT[2], False)])

    def test_empty(self):
        self.assertEqual(details_items([]), [])


class TestValues(unittest.TestCase):
    def test_values_drop_sentences(self):
        self.assertEqual(
            values([TEXT_FACT, NOTE_FACT, WARNING_FACT, AMOUNT_FACT]),
            [TEXT_FACT, AMOUNT_FACT],
        )

    def test_values_empty(self):
        self.assertEqual(values([NOTE_FACT, WARNING_FACT]), [])


class TestHasWarning(unittest.TestCase):
    def test_warning(self):
        self.assertTrue(has_warning([TEXT_FACT, WARNING_FACT]))

    def test_note_is_not_a_warning(self):
        self.assertFalse(has_warning([TEXT_FACT, NOTE_FACT]))

    def test_empty(self):
        self.assertFalse(has_warning([]))


class TestNotes(unittest.TestCase):
    def test_sentences_join_one_per_line(self):
        self.assertEqual(
            notes([NOTE_FACT, TEXT_FACT, WARNING_FACT]),
            "Only send to people you trust.\nThis cannot be undone.",
        )

    def test_empty(self):
        self.assertEqual(notes([TEXT_FACT]), "")


class TestPager(unittest.TestCase):
    """`Pager` pulls a `data` fact one chunk at a time, and only when asked."""

    def puller(self, data: bytes, pulls: list):
        async def pull(index: int, offset: int, length: int) -> bytes:
            pulls.append((index, offset, length))
            return data[offset : offset + length]

        return pull

    def test_no_data_is_one_page(self):
        pulls = []
        set_data_puller(self.puller(b"", pulls))
        try:
            pages = Pager([TEXT_FACT])
            self.assertEqual(await_result(pages.next()), ([TEXT_FACT], True))
            self.assertIsNone(await_result(pages.next()))
        finally:
            set_data_puller(None)
        self.assertEqual(pulls, [])

    def test_data_is_pulled_page_by_page(self):
        data = bytes(range(200)) * 4  # 800 bytes: 384 + 384 + 32
        pulls = []
        set_data_puller(self.puller(data, pulls))
        try:
            pages = Pager([(DATA, "Data", (len(data), 0, b""))])
            chunked, last = await_result(pages.next())
            self.assertEqual(chunked[0][2], data[:DATA_CHUNK_BYTES])
            self.assertFalse(last)
            chunked, last = await_result(pages.next())
            self.assertEqual(
                chunked[0][2], data[DATA_CHUNK_BYTES : 2 * DATA_CHUNK_BYTES]
            )
            self.assertFalse(last)
            chunked, last = await_result(pages.next())
            self.assertEqual(chunked[0][2], data[2 * DATA_CHUNK_BYTES :])
            self.assertTrue(last)
            self.assertIsNone(await_result(pages.next()))
        finally:
            set_data_puller(None)
        self.assertEqual(
            pulls,
            [
                (0, 0, DATA_CHUNK_BYTES),
                (0, DATA_CHUNK_BYTES, DATA_CHUNK_BYTES),
                (0, 2 * DATA_CHUNK_BYTES, len(data) - 2 * DATA_CHUNK_BYTES),
            ],
        )

    def test_an_extra_starts_at_its_flat_index(self):
        data = bytes(400)
        pulls = []
        set_data_puller(self.puller(data, pulls))
        try:
            pages = Pager([(DATA, "Data", (len(data), 0, b""))], 2)
            chunked, last = await_result(pages.next())
            self.assertEqual(chunked[0][2], data[:DATA_CHUNK_BYTES])
            self.assertFalse(last)
        finally:
            set_data_puller(None)
        self.assertEqual(pulls, [(2, 0, DATA_CHUNK_BYTES)])


class TestAppId(unittest.TestCase):
    def session(self, image_id: str) -> Session:
        class Image:
            def id(self) -> str:
                return image_id

            def task_id(self) -> int:
                return 1

        return Session(Image(), "secp256k1", [])

    def test_the_whole_image_id(self):
        self.assertEqual(self.session("tron.trezor.com").app_id, "tron.trezor.com")
        self.assertEqual(self.session("testapp.trezor.io").app_id, "testapp.trezor.io")

    def test_the_display_name_is_not_the_id(self):
        # the image's `name()` is for people (`Test app`), never a prefix
        self.assertNotEqual(self.session("testapp.trezor.io").app_id, "Test app")


class TestDriver(unittest.TestCase):
    """`run()`'s dispatch, its answers and its refusals; no layout is created."""

    def setUp(self):
        self.review = Screen()
        self.danger = Screen()
        self.details = Screen()
        self.address = Screen()
        self.pubkey = Screen()
        self.show = Screen()
        self._originals = [
            (confirm, "review", confirm.review),
            (confirm, "danger", confirm.danger),
            (confirm, "details", confirm.details),
            (verify, "address", verify.address),
            (verify, "pubkey", verify.pubkey),
            (success, "show", success.show),
        ]
        confirm.review = self.review
        confirm.danger = self.danger
        confirm.details = self.details
        verify.address = self.address
        verify.pubkey = self.pubkey
        success.show = self.show

    def tearDown(self):
        for module, name, original in self._originals:
            setattr(module, name, original)

    def screens(self) -> "list[Screen]":
        return [
            self.review,
            self.danger,
            self.details,
            self.address,
            self.pubkey,
            self.show,
        ]

    def assert_only(self, called: "Screen | None") -> None:
        """No screen but `called` was asked to draw anything."""
        for screen in self.screens():
            if screen is not called:
                self.assertEqual(screen.calls, [])

    def test_result_discriminants(self):
        self.assertEqual(CONFIRMED, 0)
        self.assertEqual(CANCELLED, 1)
        self.assertEqual(SHOW_DETAILS, 5)

    def test_review(self):
        self.review.result = trezorui_api.CONFIRMED
        self.assertEqual(await_result(run(REVIEW, APP)), CONFIRMED)
        self.assertEqual(
            self.review.calls,
            [(f"{APP}/send", "Send", FACTS, EXTRAS, False)],
        )
        self.assert_only(self.review)

    def test_review_final_keeps_the_hold(self):
        self.review.result = trezorui_api.CONFIRMED
        self.assertEqual(await_result(run(REVIEW_FINAL, APP)), CONFIRMED)
        self.assertEqual(
            self.review.calls,
            [(f"{APP}/send", "Send", FACTS, EXTRAS, True)],
        )

    def test_review_cancelled_discriminant(self):
        # the layout said no, rather than raising: still `CANCELLED`
        self.review.result = trezorui_api.CANCELLED
        self.assertEqual(await_result(run(REVIEW, APP)), CANCELLED)

    def test_danger(self):
        self.danger.result = trezorui_api.CONFIRMED
        self.assertEqual(await_result(run(DANGER, APP)), CONFIRMED)
        self.assertEqual(self.danger.calls, [(f"{APP}/risky", "Risky", FACTS)])
        self.assert_only(self.danger)

    def test_details_show(self):
        self.details.result = True
        self.assertEqual(await_result(run(DETAILS, APP)), SHOW_DETAILS)
        self.assertEqual(self.details.calls, [(f"{APP}/details", "Details", FACTS)])
        self.assert_only(self.details)

    def test_details_skip(self):
        self.details.result = False
        self.assertEqual(await_result(run(DETAILS, APP)), CONFIRMED)
        self.assertEqual(self.details.calls, [(f"{APP}/details", "Details", FACTS)])

    def test_verify_address(self):
        self.assertEqual(await_result(run(VERIFY_ADDRESS, APP)), CONFIRMED)
        self.assertEqual(
            self.address.calls,
            [
                (
                    f"{APP}/address",
                    ADDRESS_FACT[2],
                    "TRX #1",
                    "m/44'/195'/0'/0/0",
                )
            ],
        )
        self.assert_only(self.address)

    def test_verify_address_without_account_and_path(self):
        request = (3, "address", ADDRESS_FACT[2], None, None)
        self.assertEqual(await_result(run(request, APP)), CONFIRMED)
        self.assertEqual(
            self.address.calls,
            [(f"{APP}/address", ADDRESS_FACT[2], None, None)],
        )

    def test_verify_pubkey(self):
        self.assertEqual(await_result(run(VERIFY_PUBKEY, APP)), CONFIRMED)
        self.assertEqual(
            self.pubkey.calls,
            [(f"{APP}/pubkey", "02abc", None, None)],
        )
        self.assert_only(self.pubkey)

    def test_done(self):
        self.assertEqual(await_result(run(DONE, APP)), CONFIRMED)
        self.assertEqual(self.show.calls, [(f"{APP}/done", "All done")])
        self.assert_only(self.show)

    def test_refusal_is_cancelled(self):
        # a refusal is an answer, not an error: `run()` does not raise
        requests = [
            (REVIEW, self.review),
            (DANGER, self.danger),
            (DETAILS, self.details),
            (VERIFY_ADDRESS, self.address),
            (VERIFY_PUBKEY, self.pubkey),
            (DONE, self.show),
        ]
        for request, screen in requests:
            screen.error = ActionCancelled()
            self.assertEqual(await_result(run(request, APP)), CANCELLED)
            screen.error = None

    def test_unexpected_layout_result_is_data_error(self):
        # anything but yes or no is a bug in the caller, never a yes
        self.review.result = trezorui_api.INFO
        with self.assertRaises(DataError):
            await_result(run(REVIEW, APP))
        self.danger.result = trezorui_api.INFO
        with self.assertRaises(DataError):
            await_result(run(DANGER, APP))

    def test_data_error_passes_through(self):
        self.review.error = DataError("Cannot draw this")
        with self.assertRaises(DataError):
            await_result(run(REVIEW, APP))

    def test_unknown_kind_is_data_error(self):
        for kind in (6, 7, 99):
            request = (kind, "send", "Send", FACTS, EXTRAS, False)
            with self.assertRaises(DataError):
                await_result(run(request, APP))
        self.assert_only(None)

    def test_workflow_exceptions_pass_through(self):
        for exception in (
            Shutdown(),
            loop.TaskClosed(),
            context.UnexpectedMessageException(None),
        ):
            self.review.error = exception
            with self.assertRaises(exception.__class__):
                await_result(run(REVIEW, APP))
            self.review.error = None

    # The SDK refuses more than one `data` fact before sending, so an app never
    # reaches this; core checks again rather than trust it.
    def test_two_data_fields_is_data_error(self):
        facts = [DATA_FACT, DATA_FACT]
        with self.assertRaises(DataError):
            await_result(run((0, "send", "Send", facts, [], False), APP))


class TestReviewExtras(unittest.TestCase):
    """`review()`'s extras: an extra with no facts is never offered."""

    def setUp(self):
        self.layouts = Layouts()
        self.menu = Screen()
        self.menu.result = trezorui_api.CONFIRMED
        self._originals = [
            (confirm, "trezorui_api", confirm.trezorui_api),
            (confirm, "interact_with_menu", confirm.interact_with_menu),
        ]
        confirm.trezorui_api = self.layouts
        confirm.interact_with_menu = self.menu

    def tearDown(self):
        for module, name, original in self._originals:
            setattr(module, name, original)

    def review(self, extras):
        # a note-only review draws one action screen, then offers its extras
        return await_result(
            confirm.review(f"{APP}/send", "Send", [NOTE_FACT], extras, False)
        )

    def labels(self) -> "list[str]":
        """The entries of the menu the review drew."""
        (_layout, menu, _name) = self.menu.calls[0]
        return [leaf.name for leaf in menu.children]

    # The SDK refuses the same limit before sending, so an app never reaches
    # this; core checks again rather than trust it.
    def test_six_extras_is_data_error(self):
        extras = [(f"extra {i}", [(TEXT, "Account", f"TRX #{i}")]) for i in range(6)]
        with self.assertRaises(DataError):
            self.review(extras)
        # the limit is checked before anything is drawn
        self.assertEqual(self.layouts.calls, [])
        self.assertEqual(self.menu.calls, [])

    def test_empty_extra_is_not_offered(self):
        # an extra with no facts has nothing to show, so it is no entry
        extras = [
            ("empty", []),
            ("Account info", [(TEXT, "Account", "TRX #1")]),
            ("other", [(TEXT, "x", "y")]),
        ]
        self.assertEqual(self.review(extras), trezorui_api.CONFIRMED)
        self.assertEqual(self.labels(), ["Account info", "other", TR.buttons__cancel])
        # the step's own ButtonRequest is still sent, exactly once
        self.assertEqual(len(self.menu.calls), 1)
        self.assertEqual(self.menu.calls[0][2], f"{APP}/send")
        # one action screen, still offering the menu it now has
        self.assertEqual(len(self.layouts.calls), 1)
        self.assertTrue(self.layouts.calls[0]["external_menu"])

    def test_five_extras_with_one_empty_pass(self):
        # the empty extra is dropped before the count, so five still fit
        extras = [(f"extra {i}", [(TEXT, "Account", f"TRX #{i}")]) for i in range(5)]
        extras.append(("empty", []))
        self.assertEqual(self.review(extras), trezorui_api.CONFIRMED)
        self.assertEqual(
            self.labels(),
            [f"extra {i}" for i in range(5)] + [TR.buttons__cancel],
        )


if __name__ == "__main__":
    unittest.main()
