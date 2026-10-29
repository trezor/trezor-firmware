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
the person confirms or backs out, and the extras menu every layout carries."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType

from . import modui_ext, testapp_ext
from .generated import messages as m
from .modui_ext import extras
from .testapp_ext import SdkError

APP_NAME = "testapp.trezor.io"

ADDRESS = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm"
XPUB = (
    "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkk"
    "fHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U"
)

EXTRAS = [
    (
        "Account info",
        [
            modui_ext.text("Account", "Tron #1"),
            modui_ext.text("Path", "m/44'/195'/0'"),
        ],
    ),
    ("Fee info", [modui_ext.text("Fee limit", "100 TRX")]),
]


@dataclass
class Layout:
    """One review: how to ask for it, and what it shows."""

    make: Callable[..., object]
    title: str
    values: tuple[str, ...]
    labels: tuple[str, ...] = ()

    def request(self, **kwargs) -> object:
        return self.make(**kwargs)


REVIEWS = {
    "action": Layout(
        lambda **kw: m.Review(
            step="action",
            title="Approve",
            fields=[modui_ext.note("Approve the contract?")],
            **kw,
        ),
        title="Approve",
        values=("Approve the contract?",),
    ),
    "value": Layout(
        lambda **kw: m.Review(
            step="value",
            title="Recipient",
            fields=[modui_ext.text("Recipient", "Hello value")],
            **kw,
        ),
        title="Recipient",
        values=("Hello value",),
    ),
    "properties": Layout(
        lambda **kw: m.Review(
            step="properties",
            title="Stake",
            fields=[
                modui_ext.text("Resource", "Energy"),
                modui_ext.amount("Amount", "1.5 TRX"),
            ],
            **kw,
        ),
        title="Stake",
        values=("Energy", "1.5 TRX"),
        labels=("Resource", "Amount"),
    ),
    "warning": Layout(
        lambda **kw: m.Review(
            step="warning",
            title="Claim",
            fields=[
                modui_ext.address("Owner address", ADDRESS),
                modui_ext.warning("This address is not yours."),
            ],
            **kw,
        ),
        title="Claim",
        values=(ADDRESS, "This address is not yours."),
        labels=("Owner address",),
    ),
    "data": Layout(
        lambda **kw: m.Review(
            step="data",
            title="Data",
            fields=[modui_ext.data("Input data", bytes.fromhex("cafebabe"))],
            **kw,
        ),
        title="Data",
        values=("cafebabe",),
    ),
}

ALL = pytest.mark.parametrize("name", list(REVIEWS))
FINAL = pytest.mark.parametrize("name", ["action", "value", "properties", "data"])

# The testapp runs on Eckhart and Delizia only, so these model gaps are recorded
# but never exercised here:
# - `verify_address` / `verify_pubkey` call `flow_get_address` / `flow_get_pubkey`,
#   which are `NotImplementedError` on Bolt and Caesar; the pinned stage-A
#   exception, `show_address` / `show_pubkey`, works on all four models.
# - `done` calls `show_success`, which is `NotImplementedError` on Caesar; a
#   Caesar app would probably be stopped before it answers the host.


def br_name(step: str) -> str:
    """The name a host sees for one step of the app."""
    return f"{APP_NAME}/{step}"


def flat(text: str) -> str:
    """Text with every whitespace removed, for comparing values the model
    wraps across lines."""
    return "".join(text.split())


def screen_text(layout) -> str:
    """Everything a screen says, the footer included.

    Eckhart keeps a closing screen's description in the content, Delizia in the
    footer, so a description is looked for wherever the model put it.
    """
    return flat(" ".join([layout.title(), layout.text_content(), layout.footer()]))


def expect_one_button_request(step: str) -> list:
    """The responses of one layout: a single ButtonRequest, however long the
    person spends in its menu, then the app's answer."""
    return [messages.ButtonRequest(name=br_name(step)), messages.ExtAppResponse]


def confirm(debug) -> None:
    """Confirm a non-final layout by the model's own gesture."""
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
    else:
        debug.click(debug.screen_buttons.ok())


def confirm_hold(debug) -> None:
    """Confirm a final layout, which every model draws with a hold."""
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.synchronize_at("PromptScreen")
        debug.click(debug.screen_buttons.tap_to_confirm(), hold_ms=2200)
    else:
        debug.click(debug.screen_buttons.ok(), hold_ms=1500)


def open_menu(debug) -> None:
    """Open the layout's own menu and wait for it to be drawn."""
    debug.click(debug.screen_buttons.menu())
    debug.synchronize_at("VerticalMenu")


def open_extras_menu(debug) -> None:
    """Open a review's external menu and wait for it to be drawn."""
    debug.press_info()
    debug.synchronize_at("VerticalMenu")


def open_extra(debug, items, index: int = 0) -> None:
    """Open one extra from a review's external menu, read it, and come back."""
    open_extras_menu(debug)
    debug.button_actions.navigate_to_menu_item(index)
    label, fields = items[index]
    extra = debug.read_layout()
    assert label in extra.title()
    text = flat(extra.text_content())
    for field in fields:
        assert flat(field.value.decode()) in text
    debug.click(debug.screen_buttons.menu())  # close the extra
    debug.click(debug.screen_buttons.menu())  # close the menu


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


def read_all_pages(debug, pages: int | None = None) -> list[str]:
    """Read every page of a paged layout, leaving the last one up.

    Eckhart pages with its action bar, Delizia with a swipe. `pages` is the count
    the ButtonRequest reported, for a layout whose own trace has none.
    """
    layout = debug.read_layout()
    if pages is None:
        pages = layout.page_count()
    texts = [layout.text_content()]
    for _ in range(pages - 1):
        if debug.layout_type is LayoutType.Delizia:
            debug.swipe_up()
        else:
            debug.click(debug.screen_buttons.ok())
        texts.append(debug.read_layout().text_content())
    return texts


def read_extra_pages(debug, value: bytes) -> str:
    """Page an extra's screen until the whole value has been read.

    An extra's screen is one layout that pages itself: Eckhart with its action
    bar, Delizia with a swipe. Delizia's own trace has no page count, so the value
    itself says when the last page has been read.
    """
    text = flat("".join(debug.read_layout().text_content()))
    for _ in range(8):
        if value.hex() in text:
            break
        if debug.layout_type is LayoutType.Delizia:
            debug.swipe_up()
        else:
            debug.click(debug.screen_buttons.ok())
        text += flat("".join(debug.read_layout().text_content()))
    return text


def open_account_info(
    debug,
    present: tuple[str, ...] = (),
    absent: tuple[str, ...] = (),
) -> None:
    """Open the account info of a verify flow, check it, and come back."""
    open_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)
    text = flat(debug.read_layout().text_content())
    for value in present:
        assert flat(value) in text
    for value in absent:
        assert flat(value) not in text
    debug.click(debug.screen_buttons.menu())  # close the account info
    debug.click(debug.screen_buttons.menu())  # close the menu


def confirm_verify(debug, pages: int) -> None:
    """Confirm a verify flow, dismiss its success screen, and check it said so."""
    if debug.layout_type is LayoutType.Delizia:
        # Delizia pages the value, then asks for the tap on a prompt screen.
        for _ in range(pages - 1):
            debug.swipe_up()
        debug.synchronize_at("PromptScreen")
        debug.click(debug.screen_buttons.tap_to_confirm())
    else:
        for _ in range(pages - 1):
            debug.click(debug.screen_buttons.ok())
        debug.click(debug.screen_buttons.ok())
    success = debug.read_layout(wait=True)
    assert "confirmed" in screen_text(success).lower()
    debug.press_yes()


def check_review(debug, case: Layout) -> None:
    """Read a review's title, values and labels."""
    layout = debug.read_layout()
    assert case.title in layout.title()
    text = flat(layout.text_content())
    for value in case.values:
        assert flat(value) in text
    for label in case.labels:
        assert flat(label) in text


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
        check_review(session.debug, case)
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


@FINAL
def test_review_final_hold(session: Session, instance_id: int, name: str):
    """A final review confirms only by the model's hold gesture."""
    case = REVIEWS[name]
    request = case.request(is_final=True)

    def input_flow():
        yield
        check_review(session.debug, case)
        confirm_hold(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_review_extras(session: Session, instance_id: int, name: str):
    """Open an extra, look at it, come back and confirm: the layout still
    answers once, as if the menu had never been opened."""
    request = REVIEWS[name].request(extras=extras(*EXTRAS))

    def input_flow():
        yield
        open_extra(session.debug, EXTRAS)
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@FINAL
def test_review_final_extras(session: Session, instance_id: int, name: str):
    """A final review keeps its extras menu reachable while holding."""
    request = REVIEWS[name].request(is_final=True, extras=extras(*EXTRAS))

    def input_flow():
        yield
        open_extra(session.debug, EXTRAS)
        confirm_hold(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_review_extras_cancel(session: Session, instance_id: int, name: str):
    """The menu's last item backs out of the review."""
    request = REVIEWS[name].request(extras=extras(*EXTRAS))

    def input_flow():
        yield
        debug = session.debug
        open_extras_menu(debug)
        debug.button_actions.navigate_to_menu_item(len(EXTRAS))

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


@FINAL
def test_review_final_extras_cancel(session: Session, instance_id: int, name: str):
    """A final review's extras menu can still back out of it."""
    request = REVIEWS[name].request(is_final=True, extras=extras(*EXTRAS))

    def input_flow():
        yield
        debug = session.debug
        open_extras_menu(debug)
        debug.button_actions.navigate_to_menu_item(len(EXTRAS))

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


def test_review_long_menu_one_button_request(session: Session, instance_id: int):
    """A full extras menu, walked through, is still one step: one ButtonRequest."""
    long_extras = [
        (f"Extra {i}", [modui_ext.text("Key", f"Value {i}")]) for i in range(5)
    ]
    request = m.Review(
        step="long",
        title="Long menu",
        fields=[modui_ext.text("Resource", "Energy")],
        extras=extras(*long_extras),
    )

    def input_flow():
        yield
        open_extra(session.debug, long_extras, index=4)
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
        fields=[modui_ext.text("Resource", "Energy")],
        extras=extras(EXTRAS[0], ("Empty info", []), EXTRAS[1]),
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


def test_step_name(session: Session, instance_id: int):
    """The host sees the app's identity prefixed to the step's own name."""
    request = m.Review(
        step="long/step",
        title="Step",
        fields=[modui_ext.text("Resource", "Energy")],
    )

    def input_flow():
        br = yield
        assert br.name == br_name("long/step")
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


# ============================================================================
# Danger
# ============================================================================

DANGER_FIELDS = [
    modui_ext.note("This contract is unknown. Continue only if you trust it."),
    modui_ext.address("Contract", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"),
]


def test_danger_confirm(session: Session, instance_id: int):
    """A danger shows what is risky and goes on only when told to."""
    request = m.Danger(step="danger", title="Important", fields=DANGER_FIELDS)

    def input_flow():
        br = yield
        assert br.pages is not None
        layout = session.debug.read_layout()
        assert "Important" in layout.title()
        text = flat("".join(read_all_pages(session.debug, br.pages)))
        assert flat("This contract is unknown. Continue only if you trust it.") in text
        assert "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t" in text
        open_menu(session.debug)
        session.debug.button_actions.navigate_to_menu_item(1)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_danger_cancel(session: Session, instance_id: int):
    """A danger's menu backs out, and the closing screen says so."""
    request = m.Danger(step="danger", title="Important", fields=DANGER_FIELDS)

    def input_flow():
        yield
        open_menu(session.debug)
        session.debug.button_actions.navigate_to_menu_item(0)
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


# ============================================================================
# Details
# ============================================================================

DETAIL_FIELDS = [
    modui_ext.text("Type", "Permit"),
    modui_ext.text("Contains", "owner, spender, value, deadline"),
]


def test_details_show(session: Session, instance_id: int):
    """A details screen offers the details; asking for them answers ShowDetails."""
    request = m.Details(step="details", title="Confirm message", fields=DETAIL_FIELDS)

    def input_flow():
        yield
        layout = session.debug.read_layout()
        assert "Confirm message" in layout.title()
        text = flat(layout.text_content())
        assert "Permit" in text
        assert flat("owner, spender, value, deadline") in text
        open_menu(session.debug)
        session.debug.button_actions.navigate_to_menu_item(0)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.ShowDetails


def test_details_skip(session: Session, instance_id: int):
    """A details screen can be accepted without opening the details."""
    request = m.Details(step="details", title="Confirm message", fields=DETAIL_FIELDS)

    def input_flow():
        yield
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_details_cancel(session: Session, instance_id: int):
    """A details screen's menu backs out of it."""
    request = m.Details(step="details", title="Confirm message", fields=DETAIL_FIELDS)

    def input_flow():
        yield
        open_menu(session.debug)
        session.debug.button_actions.navigate_to_menu_item(1)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


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
        debug = session.debug
        open_menu(debug)
        debug.button_actions.navigate_to_menu_item(2)
        if debug.layout_type is LayoutType.Delizia:
            debug.swipe_up()
            debug.click(debug.screen_buttons.tap_to_confirm())
        else:
            debug.click(debug.screen_buttons.ok())

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


def test_progress_indeterminate(session: Session, instance_id: int):
    """A progress with no total is up while the app works, and ends cleanly."""
    testapp_ext.call_ext(
        session,
        instance_id,
        msg_data=m.ShowProgress(label="Signing...", total=0),
        expect=[m.ProgressTick],
    )
    assert session.debug.read_layout(wait=False).main_component() == "Progress"
    result = testapp_ext.call_ext(
        session, instance_id, msg_data=m.ProgressEnd(), expect=[m.UiResult]
    )
    assert result.reply == m.Reply.Confirmed


@pytest.mark.parametrize(
    "total, steps",
    [
        (3, [1, 1, 1]),
        (3, [2, 5]),  # past the total
        (None, []),  # indeterminate
        (None, [1, 1]),  # steps of an indeterminate progress are ignored
    ],
)
def test_progress_counted(
    session: Session, instance_id: int, total: int | None, steps: list[int]
):
    """A counted progress reports steps, pins full past its total, and ends."""
    reply = modui_ext.progress(session, instance_id, "Working...", total, steps)
    assert reply is m.Reply.Confirmed


def test_progress_label(session: Session, instance_id: int):
    """A progress label changes while the work goes on."""
    reply = modui_ext.progress(
        session,
        instance_id,
        "Working...",
        3,
        [1, "Signing 1/3", 1, "Signing 2/3", 1],
    )
    assert reply is m.Reply.Confirmed


# ============================================================================
# Field kinds
# ============================================================================


@pytest.mark.parametrize(
    "kind, label, value",
    [
        (m.FieldKind.Text, "Resource", "Energy"),
        (m.FieldKind.Amount, "Amount", "1.5 TRX"),
        (m.FieldKind.Address, "Recipient", ADDRESS),
    ],
    ids=["text", "amount", "address"],
)
def test_field_value_kind(
    session: Session, instance_id: int, kind: m.FieldKind, label: str, value: str
):
    """A text, amount or address field is shown as written."""
    request = m.Review(
        step="field",
        title="Field",
        fields=[modui_ext.field(kind, value, label)],
    )

    def input_flow():
        yield
        layout = session.debug.read_layout()
        assert flat(value) in flat(layout.text_content())
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_field_data_paging(session: Session, instance_id: int):
    """A data field is pulled one chunk at a time, and each chunk pages as its
    own screen of lower-case hex."""
    value = bytes(range(256)) * 2
    request = m.Review(
        step="data",
        title="Data",
        fields=[modui_ext.data("Input data", value)],
    )

    def input_flow():
        br = yield
        assert br.name == br_name(request.step)
        layout = session.debug.read_layout(wait=True)
        assert br.pages is not None
        assert br.pages == layout.page_count()
        assert br.pages > 1
        first = read_all_pages(session.debug, br.pages)
        assert value[:384].hex() in flat("".join(first))
        confirm(session.debug)  # the last page of the chunk reads "Continue"
        second = read_all_pages(session.debug)
        assert value[384:].hex() in flat("".join(second))
        confirm(session.debug)

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
        fields=[modui_ext.data("Input data", value)],
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


def test_field_data_long_value(session: Session, instance_id: int):
    """Data of any length is accepted, pulled in chunks, and shown whole."""
    value = bytes(range(256)) * 4 + b"\xff"  # 1025 bytes: 384 + 384 + 257
    request = m.Review(
        step="data",
        title="Long data",
        fields=[modui_ext.data("Input data", value)],
    )

    def input_flow():
        br = yield
        pages = read_all_pages(session.debug, br.pages)
        assert len(pages) > 1
        text = "".join(pages)
        for _ in range(2):  # the second and third chunks
            confirm(session.debug)
            session.debug.read_layout(wait=True)
            text += "".join(read_all_pages(session.debug))
        confirm(session.debug)
        assert value.hex() in flat(text)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_data_in_an_extra(session: Session, instance_id: int):
    """A data field inside an extra is paged there, and the review stays one
    step."""
    value = bytes(range(192))
    request = m.Review(
        step="data",
        title="Data",
        fields=[modui_ext.text("Resource", "Energy")],
        extras=extras(("Input data", [modui_ext.data("Input data", value)])),
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


def test_field_note(session: Session, instance_id: int):
    """A note is a sentence of its own, with no label."""
    request = m.Review(
        step="note",
        title="Question",
        fields=[modui_ext.note("Allow access to your balance?")],
    )

    def input_flow():
        yield
        layout = session.debug.read_layout()
        assert flat("Allow access to your balance?") in flat(layout.text_content())
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_field_warning_beside_address(session: Session, instance_id: int):
    """A warning is drawn beside the address it warns about."""
    request = m.Review(
        step="warning",
        title="Claim",
        fields=[
            modui_ext.address("Owner address", ADDRESS),
            modui_ext.warning("This address is not yours."),
        ],
    )

    def input_flow():
        yield
        layout = session.debug.read_layout()
        text = flat(layout.text_content())
        assert ADDRESS in text
        assert flat("This address is not yours.") in text
        confirm(session.debug)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.step))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


# ============================================================================
# Limits
# ============================================================================


def test_limits_too_many_extras(session: Session, instance_id: int):
    """A sixth extra is refused before anything is shown."""
    request = m.Review(
        step="extras",
        title="Too many extras",
        fields=[modui_ext.text("Resource", "Energy")],
        extras=extras(
            *[(f"Extra {i}", [modui_ext.text("Key", "Value")]) for i in range(6)]
        ),
    )

    with testapp_ext.raises(SdkError.DataError, "more than 5 extras"):
        modui_ext.show(session, instance_id, request)


def test_limits_two_data_fields(session: Session, instance_id: int):
    """A second data field is refused before anything is shown."""
    request = m.Review(
        step="data",
        title="Two data fields",
        fields=[
            modui_ext.data("First", b"\x01"),
            modui_ext.data("Second", b"\x02"),
        ],
    )

    with testapp_ext.raises(SdkError.DataError, "more than one data field"):
        modui_ext.show(session, instance_id, request)
