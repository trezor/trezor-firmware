# This file is part of the Trezor project.
#
# Copyright (C) SatoshiLabs and contributors
#
# This library is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3
# as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the License along with this library.
# If not, see <https://www.gnu.org/licenses/lgpl-3.0.html>.

"""The modui layouts, driven through the testapp: what each one shows, how
the person confirms or backs out, and the menu every review carries."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure

from . import modui_ext, testapp_ext
from .modui_ext import (
    XPUB,
    address,
    amount,
    br_name,
    cancel_by_menu,
    cancel_danger,
    cancel_verify,
    confirm,
    confirm_hold,
    confirm_verify,
    data,
    extras,
    flat,
    go_on_past_danger,
    m,
    note,
    open_account_info,
    open_extra,
    open_extras_menu,
    page,
    read_all_pages,
    screen_text,
    show_all,
    text,
    text_extras,
    warning,
)
from .testapp_ext import SdkError

ADDRESS = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm"

EXTRAS = [
    ("Account info", (("Account", "Tron #1"), ("Path", "m/44'/195'/0'"))),
    ("Fee info", (("Fee limit", "100 TRX"),)),
]


@dataclass
class Case:
    """One review: how to ask for it, and what its screen shows."""

    request: Callable[..., m.Review]
    values: tuple[str, ...]
    labels: tuple[str, ...] = ()


# The reviews the review tests run on, each named after the facts it holds.
REVIEWS = {
    "note": Case(
        lambda **kw: m.Review(
            step="note",
            title="Approve",
            fields=[note("Approve the contract?")],
            **kw,
        ),
        values=("Approve the contract?",),
    ),
    "text": Case(
        lambda **kw: m.Review(
            step="text",
            title="Recipient",
            fields=[text("Recipient", "Hello value")],
            **kw,
        ),
        values=("Hello value",),
    ),
    # A note before one value: the value is drawn, and the note with it.
    "note+text": Case(
        lambda **kw: m.Review(
            step="note+text",
            title="Stake",
            fields=[note("Stake with Everstake?"), text("Resource", "Energy")],
            **kw,
        ),
        values=("Stake with Everstake?", "Energy"),
    ),
    "text+amount": Case(
        lambda **kw: m.Review(
            step="text+amount",
            title="Stake",
            fields=[text("Resource", "Energy"), amount("Amount", "1.5", "TRX")],
            **kw,
        ),
        values=("Energy", "1.5 TRX"),
        labels=("Resource", "Amount"),
    ),
    "address+warning": Case(
        lambda **kw: m.Review(
            step="address+warning",
            title="Claim",
            fields=[
                address("Owner address", ADDRESS),
                warning("This address is not yours."),
            ],
            **kw,
        ),
        values=(ADDRESS, "This address is not yours."),
        labels=("Owner address",),
    ),
    "data": Case(
        lambda **kw: m.Review(
            step="data",
            title="Data",
            fields=[data("Input data", bytes.fromhex("cafebabe"))],
            **kw,
        ),
        values=("cafebabe",),
    ),
}

ALL = pytest.mark.parametrize("name", list(REVIEWS))


def expect_one_button_request(step: str) -> list:
    """The responses of one layout: a single ButtonRequest, however long the
    person spends in its menu, then the app's answer."""
    return [messages.ButtonRequest(name=br_name(step)), messages.ExtAppResponse]


def menu_labels(debug) -> list[str]:
    """The labels a menu offers, whichever menu the model draws."""
    layout = debug.read_layout()
    menu = layout.find_unique_value_by_key("menu_items", default=None, only_type=dict)
    if menu is None:
        return layout.vertical_menu_content()
    labels = []
    while True:
        labels.extend(item.get("item", item.get("cancel")) for item in menu["current"])
        if not menu["has_next"]:
            return labels
        _prev, next_button = debug.screen_buttons.vertical_menu_prev_next()
        debug.click(next_button)
        menu = debug.read_layout().find_unique_value_by_key(
            key="menu_items", default=None, only_type=dict
        )


def read_extra_pages(debug, value: bytes) -> str:
    """Page an extra's screen until the whole value has been read.

    An extra's screen is one layout that pages itself. Delizia's own trace has
    no page count, so the value itself says when the last page has been read.
    """
    shown = flat("".join(debug.read_layout().text_content()))
    for _ in range(8):
        if value.hex() in shown:
            break
        page(debug)
        shown += flat("".join(debug.read_layout().text_content()))
    return shown


def check_review(debug, request: m.Review, case: Case) -> None:
    """Read a review's title, values and labels."""
    layout = debug.read_layout()
    assert request.title in layout.title()
    shown = flat(layout.text_content())
    for value in case.values:
        assert flat(value) in shown
    for label in case.labels:
        assert flat(label) in shown


# ============================================================================
# Review
# ============================================================================


@ALL
def test_review_confirm(session: Session, instance_id: int, name: str):
    """A review shows its title and facts, then confirms once."""
    case = REVIEWS[name]
    request = case.request()

    def input_flow():
        yield
        check_review(session.debug, request, case)
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_review_cancel(session: Session, instance_id: int, name: str):
    """A review backs out when the person refuses it."""
    request = REVIEWS[name].request()

    def input_flow():
        yield
        session.debug.press_no()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


@ALL
def test_review_strong_hold(session: Session, instance_id: int, name: str):
    """A strong review confirms only by the model's hold gesture."""
    case = REVIEWS[name]
    request = case.request(answer=m.Answer.Strong)

    def input_flow():
        yield
        check_review(session.debug, request, case)
        confirm_hold(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_review_extras(session: Session, instance_id: int, name: str):
    """Open an extra, look at it, come back and confirm: the layout still
    answers once, as if the menu had never been opened."""
    request = REVIEWS[name].request(extras=text_extras(EXTRAS))

    def input_flow():
        yield
        open_extra(session.debug, EXTRAS, 0)
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_review_strong_extras(session: Session, instance_id: int, name: str):
    """A strong review keeps its extras menu reachable while holding."""
    request = REVIEWS[name].request(answer=m.Answer.Strong, extras=text_extras(EXTRAS))

    def input_flow():
        yield
        open_extra(session.debug, EXTRAS, 0)
        confirm_hold(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_review_extras_cancel(session: Session, instance_id: int, name: str):
    """The menu's last item backs out of the review."""
    request = REVIEWS[name].request(extras=text_extras(EXTRAS))

    def input_flow():
        yield
        cancel_by_menu(session.debug, len(EXTRAS))

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


@ALL
def test_review_strong_extras_cancel(session: Session, instance_id: int, name: str):
    """A strong review's extras menu can still back out of it."""
    request = REVIEWS[name].request(answer=m.Answer.Strong, extras=text_extras(EXTRAS))

    def input_flow():
        yield
        cancel_by_menu(session.debug, len(EXTRAS))

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


def test_review_long_menu_one_button_request(session: Session, instance_id: int):
    """A full extras menu, walked through, is still one step: one ButtonRequest."""
    long_extras = [(f"Extra {i}", (("Key", f"Value {i}"),)) for i in range(5)]
    request = m.Review(
        step="long",
        title="Long menu",
        fields=[text("Resource", "Energy")],
        extras=text_extras(long_extras),
    )

    def input_flow():
        yield
        open_extra(session.debug, long_extras, 4)
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_an_empty_extra_is_not_offered(session: Session, instance_id: int):
    """An extra with no facts is dropped, so the menu offers only the rest."""
    request = m.Review(
        step="extras",
        title="Extras",
        fields=[text("Resource", "Energy")],
        extras=text_extras([EXTRAS[0], ("Empty info", ()), EXTRAS[1]]),
    )

    def input_flow():
        yield
        debug = session.debug
        open_extras_menu(debug)
        menu = menu_labels(debug)
        # The extras with facts, in order, and nothing else before the way out.
        assert menu[:-1] == [label for label, _ in EXTRAS]
        debug.click(debug.screen_buttons.menu())  # close the menu
        confirm(debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


# ============================================================================
# Danger
# ============================================================================

DANGER_FIELDS = [
    note("This contract is unknown. Continue only if you trust it."),
    address("Contract", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"),
]


def danger_request() -> m.Review:
    """A review of the risk, answered as a danger."""
    return m.Review(
        step="danger",
        title="Important",
        fields=DANGER_FIELDS,
        answer=m.Answer.Danger,
    )


def test_danger_confirm(session: Session, instance_id: int):
    """A danger shows what is risky and goes on only when told to."""
    request = danger_request()

    def input_flow():
        br = yield
        assert br.pages is not None
        layout = session.debug.read_layout()
        assert "Important" in layout.title()
        shown = flat("".join(read_all_pages(session.debug, br.pages)))
        assert flat("This contract is unknown. Continue only if you trust it.") in shown
        assert "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t" in shown
        go_on_past_danger(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_danger_cancel(session: Session, instance_id: int):
    """A danger's menu backs out, and the closing screen says so."""
    request = danger_request()

    def input_flow():
        yield
        cancel_danger(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


# ============================================================================
# Details
# ============================================================================

DETAIL_FIELDS = [
    text("Type", "Permit"),
    text("Contains", "owner, spender, value, deadline"),
]


def details_request(**kwargs) -> m.Review:
    """A review of the short version, answered by `details`."""
    return m.Review(
        step="details",
        title="Confirm message",
        fields=DETAIL_FIELDS,
        answer=m.Answer.Details,
        **kwargs,
    )


def test_details_show(session: Session, instance_id: int):
    """A details screen is a review whose menu offers "Show all", then the way
    out; picking "Show all" answers ShowDetails."""
    request = details_request()

    def input_flow():
        yield
        debug = session.debug
        layout = debug.read_layout()
        assert "Confirm message" in layout.title()
        shown = flat(layout.text_content())
        assert "Permit" in shown
        assert flat("owner, spender, value, deadline") in shown
        open_extras_menu(debug)
        assert menu_labels(debug) == ["Show all", "Cancel"]
        debug.button_actions.navigate_to_menu_item(0)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.ShowDetails


def test_details_labels(session: Session, instance_id: int):
    """A details screen shows each fact under its label, and confirming it
    accepts the short version without the details."""
    request = details_request()

    def input_flow():
        yield
        shown = flat(session.debug.read_layout().text_content())
        for fact in DETAIL_FIELDS:
            assert fact.label in shown
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_details_cancel(session: Session, instance_id: int):
    """A details screen's menu backs out of it, by the entry after "Show all"."""
    request = details_request()

    def input_flow():
        yield
        cancel_by_menu(session.debug, 1)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


def test_details_extras(session: Session, instance_id: int):
    """A details screen's menu holds its extras before "Show all": an extra comes
    back to the review, and "Show all" still answers ShowDetails."""
    request = details_request(extras=text_extras(EXTRAS))

    def input_flow():
        yield
        debug = session.debug
        open_extras_menu(debug)
        labels = [label for label, _ in EXTRAS]
        assert menu_labels(debug) == labels + ["Show all", "Cancel"]
        debug.click(debug.screen_buttons.menu())  # close the menu
        open_extra(debug, EXTRAS, 1)
        show_all(debug, len(EXTRAS))

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.ShowDetails


# ============================================================================
# Summary
# ============================================================================

SUMMARY_EXTRAS = [
    ("Account info", (("Account", "TRX #1"), ("Derivation path", "m/44'/195'/0'"))),
    ("Fee info", (("Fee rate", "12 sat/vB"),)),
]


def test_summary(session: Session, instance_id: int):
    """A summary shows the amount and the fee under their labels, offers the
    account and the fee's details in its menu, and confirms only by the hold."""
    account, fee_info = text_extras(SUMMARY_EXTRAS)
    request = m.Summary(
        step="summary",
        title="Send",
        amount=m.Amount(label="Amount", value="1.5", ticker="TRX"),
        fee=m.Amount(label="Fee limit", value="10", ticker="TRX"),
        account=account,
        fee_info=fee_info,
    )

    def input_flow():
        br = yield
        debug = session.debug
        assert "Send" in debug.read_layout().title()
        open_extra(debug, SUMMARY_EXTRAS, 0)
        open_extra(debug, SUMMARY_EXTRAS, 1)
        shown = flat("".join(read_all_pages(debug, br.pages)))
        for value in ("Amount", "1.5 TRX", "Fee limit", "10 TRX"):
            assert flat(value) in shown
        confirm_hold(debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_summary_needs_amount_or_fee(session: Session, instance_id: int):
    """A summary with neither an amount nor a fee is refused before anything is
    shown."""
    request = m.Summary(
        step="summary", title="Send", account=text_extras(SUMMARY_EXTRAS[:1])[0]
    )

    with testapp_ext.raises(SdkError.DataError, "a summary needs an amount or a fee"):
        modui_ext.show(session, instance_id, request)


# ============================================================================
# Verify address and public key
# ============================================================================

VERIFY_ACCOUNT = "TRX #1"
VERIFY_PATH = "m/44'/195'/0'/0/0"


def make_verify_address(account: str | None, path: str | None) -> m.VerifyAddress:
    return m.VerifyAddress(step="address", value=ADDRESS, account=account, path=path)


def make_verify_pubkey(account: str | None, path: str | None) -> m.VerifyPubkey:
    return m.VerifyPubkey(step="pubkey", value=XPUB, account=account, path=path)


@pytest.mark.parametrize(
    "make, value",
    [
        (make_verify_address, ADDRESS),
        (make_verify_pubkey, XPUB),
    ],
    ids=["address", "pubkey"],
)
def test_verify_confirm(session: Session, instance_id: int, make, value: str):
    """A verify flow shows the value, its account and path, and confirms."""
    request = make(VERIFY_ACCOUNT, VERIFY_PATH)

    def input_flow():
        br = yield
        assert br.pages is not None
        layout = session.debug.read_layout()
        assert flat(value) in flat(layout.text_content())
        open_account_info(session.debug, present=(VERIFY_ACCOUNT, VERIFY_PATH))
        confirm_verify(session.debug, br.pages)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@pytest.mark.parametrize(
    "make",
    [make_verify_address, make_verify_pubkey],
    ids=["address", "pubkey"],
)
def test_verify_absent_account(session: Session, instance_id: int, make):
    """A verify flow with no account or path shows neither."""
    request = make(None, None)

    def input_flow():
        br = yield
        assert br.pages is not None
        open_account_info(session.debug, absent=(VERIFY_ACCOUNT, VERIFY_PATH))
        confirm_verify(session.debug, br.pages)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@pytest.mark.parametrize(
    "make",
    [make_verify_address, make_verify_pubkey],
    ids=["address", "pubkey"],
)
def test_verify_cancel(session: Session, instance_id: int, make):
    """A verify flow backs out when the person refuses it."""
    request = make(VERIFY_ACCOUNT, VERIFY_PATH)

    def input_flow():
        yield
        session.debug.press_no()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


@pytest.mark.parametrize(
    "make",
    [make_verify_address, make_verify_pubkey],
    ids=["address", "pubkey"],
)
def test_verify_does_not_match(session: Session, instance_id: int, make):
    """The person's "does not match" path cancels the flow."""
    request = make(VERIFY_ACCOUNT, VERIFY_PATH)

    def input_flow():
        yield
        cancel_verify(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


# ============================================================================
# Done
# ============================================================================


def test_done(session: Session, instance_id: int):
    """A done screen asks nothing; the app answers Confirmed."""
    request = m.Done(step="signed", text="Transaction signed")

    def input_flow():
        yield
        layout = session.debug.read_layout()
        assert flat("Transaction signed") in screen_text(layout)
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


# ============================================================================
# Progress
# ============================================================================


@pytest.mark.parametrize(
    "total, steps",
    [
        (3, [1, 1, 1]),
        (3, [2, 5]),  # past the total
        (None, []),  # indeterminate
        (None, [1, 1]),  # steps of an indeterminate progress are ignored
    ],
)
def test_progress_steps(
    session: Session, instance_id: int, total: int | None, steps: list[int]
):
    """A progress is up while the app works: a counted one reports steps and
    pins full past its total, an indeterminate one ignores them, and either
    ends cleanly."""
    with modui_ext.progress(session, instance_id, "Working...", total) as report:
        assert session.debug.read_layout(wait=False).main_component() == "Progress"
        for units in steps:
            report(units)


def test_progress_label(session: Session, instance_id: int):
    """A progress label changes while the work goes on."""
    with modui_ext.progress(session, instance_id, "Working...", 3) as report:
        for step in [1, "Signing 1/3", 1, "Signing 2/3", 1]:
            report(step)


def test_progress_nested_refused(session: Session, instance_id: int):
    """A progress started inside another one is refused, and the app stops; the
    next request starts it anew."""
    modui_ext.tick(session, instance_id, m.ShowProgress(label="Working..."))

    with pytest.raises(TrezorFailure) as e:
        modui_ext.tick(session, instance_id, m.ProgressNested(label="Inner"))
    assert e.value.code == messages.FailureType.DataError
    assert "nested" in e.value.message.lower()

    with modui_ext.progress(session, instance_id, "Again", None):
        assert session.debug.read_layout(wait=False).main_component() == "Progress"


def test_progress_review_reshows(session: Session, instance_id: int):
    """A review inside the progress's work covers the bar, and confirming it
    brings the bar back, unchanged."""
    review = m.ProgressReview(step="review", title="Confirm step")

    def input_flow():
        yield
        assert review.title in session.debug.read_layout().title()
        confirm(session.debug)

    with modui_ext.progress(session, instance_id, "Working...", 3) as report:
        report(1)
        with session.test_ctx as client:
            client.set_input_flow(input_flow)
            client.set_expected_responses(expect_one_button_request(review.step))
            modui_ext.tick(session, instance_id, review)

        # The review covered the bar; it is back as it was before the review.
        assert session.debug.read_layout(wait=False).main_component() == "Progress"
        report(1)


# ============================================================================
# Data fields
# ============================================================================

# How many bytes of a data field core pulls at a time: three pages of hex.
CHUNK_BYTES = 384


def read_chunks(debug, pages: int | None, value: bytes) -> None:
    """Page through a data field chunk by chunk, check that each chunk shows its
    own bytes as lower-case hex, and confirm the last one.

    `pages` is the count the ButtonRequest reported for the first chunk; a later
    chunk sends none, and its own trace counts its pages. Confirming a chunk's
    last page, which reads "Continue", pulls the next one.
    """
    for offset in range(0, len(value), CHUNK_BYTES):
        if offset:
            confirm(debug)
            debug.read_layout(wait=True)
        texts = read_all_pages(debug, None if offset else pages)
        assert value[offset : offset + CHUNK_BYTES].hex() in flat("".join(texts))
    confirm(debug)


@pytest.mark.parametrize("length", [512, 1025], ids=["two-chunks", "three-chunks"])
def test_field_data_chunks(session: Session, instance_id: int, length: int):
    """Data of any length is accepted and pulled one chunk at a time, and each
    chunk pages as its own screen of lower-case hex."""
    value = bytes(i % 256 for i in range(length))
    request = m.Review(
        step="data",
        title="Data",
        fields=[data("Input data", value)],
    )

    def input_flow():
        br = yield
        layout = session.debug.read_layout(wait=True)
        assert br.pages is not None
        assert br.pages == layout.page_count()
        assert br.pages > 1
        read_chunks(session.debug, br.pages, value)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_field_data_cancel_between_chunks(session: Session, instance_id: int):
    """Refusing a review between two chunks pulls nothing more, and the app still
    gets its answer."""
    value = bytes(range(256)) * 2
    request = m.Review(
        step="data",
        title="Data",
        fields=[data("Input data", value)],
    )

    def input_flow():
        br = yield
        pages = read_all_pages(session.debug, br.pages)
        assert len(pages) > 1
        session.debug.press_no()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


def test_stream_data(session: Session, instance_id: int):
    """A data_source field is pulled from the app one chunk at a time, and the
    final review shows the hash of the bytes it handed out and how many reads it
    took."""
    length = 1025  # 384 + 384 + 257: three chunks
    value = bytes(i % 256 for i in range(length))
    request = m.StreamData(step="stream", title="Stream", length=length)

    def input_flow():
        br = yield
        read_chunks(session.debug, br.pages, value)

        br = yield
        shown = flat("".join(read_all_pages(session.debug, br.pages)))
        assert hashlib.sha256(value).hexdigest() in shown
        assert "Reads3" in shown
        confirm_hold(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(
            [
                messages.ButtonRequest(name=br_name(request.step)),
                messages.ButtonRequest(name=br_name("summary")),
                messages.ExtAppResponse,
            ]
        )
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_stream_data_failure(session: Session, instance_id: int):
    """A source whose read fails ends the review as refused, and the app gets the
    source's own error rather than a cancel."""
    request = m.StreamData(step="stream", title="Stream", length=1025, fail_at=2)

    def input_flow():
        br = yield
        read_all_pages(session.debug, br.pages)
        confirm(session.debug)  # the second read then fails

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        with testapp_ext.raises(SdkError.ValueError, "the stream failed"):
            modui_ext.show(session, instance_id, request)


def test_stream_data_cancel(session: Session, instance_id: int):
    """Refusing a streamed field between two chunks pulls nothing more, and the
    app still gets its answer."""
    request = m.StreamData(step="stream", title="Stream", length=1025)

    def input_flow():
        br = yield
        read_all_pages(session.debug, br.pages)
        session.debug.press_no()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


def test_data_in_an_extra(session: Session, instance_id: int):
    """A data field inside an extra is paged there, and the review stays one
    step."""
    value = bytes(range(192))
    request = m.Review(
        step="data",
        title="Data",
        fields=[text("Resource", "Energy")],
        extras=extras(("Input data", [data("Input data", value)])),
    )

    def input_flow():
        yield
        debug = session.debug
        open_extras_menu(debug)
        debug.button_actions.navigate_to_menu_item(0)
        assert "Input data" in debug.read_layout().title()
        assert value.hex() in read_extra_pages(debug, value)
        debug.click(debug.screen_buttons.menu())  # close the extra
        debug.click(debug.screen_buttons.menu())  # close the menu
        confirm(debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


# ============================================================================
# Limits
# ============================================================================


@pytest.mark.parametrize(
    "answer, offered",
    [
        (m.Answer.Confirm, 6),
        (m.Answer.Strong, 6),
        (m.Answer.Details, 5),
        (m.Answer.Danger, 1),
    ],
    ids=["review", "strong", "details", "danger"],
)
def test_limits_menu_budget(
    session: Session, instance_id: int, answer: m.Answer, offered: int
):
    """One extra more than the menu has room for is refused before anything is
    shown. Each offered extra takes an entry of the menu, the way out one, and
    "Show all" of details one; a danger's menu has none to spare."""
    request = m.Review(
        step="extras",
        title="Too many extras",
        fields=[text("Resource", "Energy")],
        extras=text_extras(
            [(f"Extra {i}", (("Key", "Value"),)) for i in range(offered)]
        ),
        answer=answer,
    )

    with testapp_ext.raises(
        SdkError.DataError, "more extras than the menu has room for"
    ):
        modui_ext.show(session, instance_id, request)


def test_limits_two_data_fields(session: Session, instance_id: int):
    """A second data field is refused before anything is shown."""
    request = m.Review(
        step="data",
        title="Two data fields",
        fields=[
            data("First", b"\x01"),
            data("Second", b"\x02"),
        ],
    )

    with testapp_ext.raises(SdkError.DataError, "more than one data field"):
        modui_ext.show(session, instance_id, request)
