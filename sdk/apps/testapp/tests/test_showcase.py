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

"""The API reference's examples, run end to end on the device.

Each showcase is the reference's own flow with its sample values, so confirming
or cancelling it proves the firmware can draw and answer every screen it contains.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pytest

from trezorlib import messages
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType

from . import modui_ext
from .generated import messages as m

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

APP_NAME = "testapp.trezor.io"

RECIPIENT = "TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq"
OWNER = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm"
CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ACCOUNT = "TRX #1"
LOCK_PERIOD = "3 days"
PATH = "m/44'/195'/0'/0/0"
XPUB = (
    "tpubDDKn3FtHc74CaRrRbi1WFdJNaaenZkDWqq9NsEhcafnDZ4VuKeuLG2aKHm5SuwuLgAhRkk"
    "fHqcCxpnVNSrs5kJYZXwa6Ud431VnevzzzK3U"
)

# `transfer(address,uint256)` and its two arguments, as the reference passes it.
CALLDATA = (
    bytes.fromhex("a9059cbb")
    + bytes(12)
    + bytes.fromhex("413f5d7a1b2c4d5e6f708192a3b4c5d6")
    + bytes(16)
    + bytes(16)
    + bytes.fromhex("00000064")
)


@dataclass
class Screen:
    """One screen of a showcase: what it is called and what it shows."""

    step: str
    title: str | None = None
    values: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    extras: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()
    final: bool = False
    kind: str = "review"
    account: str | None = None
    path: str | None = None
    show_details: bool = False


ACCOUNT_INFO = (
    "Account info",
    (("Account", ACCOUNT), ("Derivation path", PATH)),
)

SEND = [
    Screen(
        step="send",
        title="Send",
        values=(RECIPIENT,),
        extras=(ACCOUNT_INFO,),
    ),
    Screen(
        step="summary",
        title="Send",
        values=("1.5 TRX", "10 TRX"),
        labels=("Amount", "Fee limit"),
        extras=(ACCOUNT_INFO,),
        final=True,
    ),
]

DELEGATE = [
    Screen(
        step="delegate",
        title="Delegate",
        values=(RECIPIENT, "1,000 TRX", "Energy"),
        labels=("Recipient", "Amount", "Resource"),
    ),
    Screen(
        step="delegate/final",
        title="Delegate",
        values=("1,000 TRX", "Energy", LOCK_PERIOD),
        labels=("Amount", "Resource", "Lock period"),
        final=True,
    ),
]

CLAIM_OWNER = Screen(
    step="claim/owner",
    title="Claim",
    values=(OWNER, "This address is not yours."),
    labels=("Owner address",),
)

UNKNOWN_CONTRACT = Screen(
    step="unknown_contract",
    title="Important",
    values=("This contract is unknown. Continue only if you trust it.", CONTRACT),
    kind="danger",
)

PATH_WARNING = Screen(
    step="path_warning",
    title="Unknown path",
    values=("This path is not usual for this coin.", PATH),
    kind="danger",
)

TYPED_DATA_DETAILS = Screen(
    step="typed_data/message",
    title="Confirm message",
    values=("Permit", "owner, spender, value, deadline"),
    kind="details",
)

TYPED_DATA_OWNER = Screen(
    step="typed_data/owner",
    title="Confirm message",
    values=(OWNER, "1,000 USDT"),
    labels=("Owner", "Value"),
)

GET_ADDRESS = Screen(
    step="address",
    values=(RECIPIENT,),
    kind="verify",
    account=ACCOUNT,
    path=PATH,
)

GET_PUBKEY = Screen(
    step="pubkey",
    values=(XPUB,),
    kind="verify",
    account=ACCOUNT,
    path=PATH,
)

CONTRACT_DATA = Screen(
    step="contract/data",
    title="Contract data",
    values=(CONTRACT, CALLDATA.hex()),
    labels=("Contract", "Input data"),
)

SIGNED = Screen(
    step="signed",
    values=("Transaction signed",),
    kind="done",
)


# Where a model draws less than the layout asks for: (layout type, what) ->
# why. The test is not run there; it is reported as an expected failure.
GAPS = {
    (LayoutType.Delizia, "delegate"): (
        "WIP: confirm_properties draws a review's facts on one screen with no "
        "vertical paging, so a third fact is cut off"
    ),
    (LayoutType.Delizia, "contract/data"): (
        "WIP: confirm_properties draws a review's facts on one screen with no "
        "vertical paging, so long input data is cut off"
    ),
}


def skip_gap(debug: "DebugLink", what: str) -> None:
    reason = GAPS.get((debug.layout_type, what))
    if reason is not None:
        pytest.xfail(reason)


def br_name(step: str) -> str:
    """The name a host sees for one step of the app."""
    return f"{APP_NAME}/{step}"


def flat(text: str) -> str:
    """Text with every whitespace removed, for values the model wraps or pages."""
    return "".join(text.split())


def screen_text(layout) -> str:
    """Everything a screen says, the footer included.

    Eckhart keeps a closing screen's description in the content, Delizia in the
    footer, so a description is looked for wherever the model put it.
    """
    return flat(" ".join([layout.title(), layout.text_content(), layout.footer()]))


def page(debug: "DebugLink") -> None:
    """Turn one page of a paged layout: Eckhart's action bar, Delizia's swipe."""
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
    else:
        debug.click(debug.screen_buttons.ok())


def confirm(debug: "DebugLink") -> None:
    """Confirm the last page of a non-final layout."""
    page(debug)


def hold(debug: "DebugLink") -> None:
    """Confirm the last page of a final layout, which is drawn with a hold."""
    if debug.layout_type is LayoutType.Delizia:
        debug.swipe_up()
        debug.synchronize_at("PromptScreen")
        debug.click(debug.screen_buttons.tap_to_confirm(), hold_ms=2200)
    else:
        debug.click(debug.screen_buttons.ok(), hold_ms=1500)


def open_menu(debug: "DebugLink") -> None:
    """Open the layout's own menu and wait for it to be drawn."""
    debug.click(debug.screen_buttons.menu())
    debug.synchronize_at("VerticalMenu")


def open_extras_menu(debug: "DebugLink") -> None:
    """Open a review's external menu and wait for it to be drawn."""
    debug.press_info()
    debug.synchronize_at("VerticalMenu")


def open_extra(
    debug: "DebugLink",
    items: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
) -> None:
    """Open every extra of a review, read it, and come back to the review."""
    for index, (label, fields) in enumerate(items):
        open_extras_menu(debug)
        debug.button_actions.navigate_to_menu_item(index)
        extra = debug.read_layout()
        assert label in extra.title()
        text = flat(extra.text_content())
        for _, value in fields:
            assert flat(value) in text
        debug.click(debug.screen_buttons.menu())  # close the extra
        debug.click(debug.screen_buttons.menu())  # close the menu


def open_account_info(debug: "DebugLink", account: str, path: str) -> None:
    """Open a verify flow's account info, check it, and come back."""
    open_menu(debug)
    debug.button_actions.navigate_to_menu_item(1)
    text = flat(debug.read_layout().text_content())
    assert flat(account) in text
    assert flat(path) in text
    debug.click(debug.screen_buttons.menu())  # close the account info
    debug.click(debug.screen_buttons.menu())  # close the menu


def confirm_verify(debug: "DebugLink", pages: int) -> None:
    """Page to the end of a verify flow, confirm, and dismiss its success."""
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


def answer_review(debug: "DebugLink", screen: Screen, visit_extras: bool) -> None:
    """Read a review's title, extras and every page, then confirm or hold it."""
    layout = debug.read_layout()
    assert screen.title is not None
    assert screen.title in layout.title()

    if screen.extras and visit_extras:
        open_extra(debug, screen.extras)

    layout = debug.read_layout()
    pages = [layout.text_content()]
    for _ in range(layout.page_count() - 1):
        page(debug)
        pages.append(debug.read_layout().text_content())

    text = flat("".join(pages))
    for value in screen.values:
        assert flat(value) in text
    for label in screen.labels:
        assert flat(label) in text

    if screen.final:
        hold(debug)
    else:
        confirm(debug)


def answer_simple(debug: "DebugLink", screen: Screen, pages: int) -> None:
    """Read a screen, paging it if it runs over, and answer it."""
    layout = debug.read_layout()
    if screen.title is not None:
        assert screen.title in layout.title()
    texts = [screen_text(layout)]
    for _ in range(pages - 1):
        page(debug)
        texts.append(screen_text(debug.read_layout()))
    text = flat("".join(texts))
    for value in screen.values:
        assert flat(value) in text
    for label in screen.labels:
        assert flat(label) in text

    if screen.kind == "danger":
        open_menu(debug)
        debug.button_actions.navigate_to_menu_item(1)
    elif screen.kind == "details":
        if screen.show_details:
            open_menu(debug)
            debug.button_actions.navigate_to_menu_item(0)
        else:
            debug.press_yes()
    elif screen.kind == "done":
        debug.press_yes()
    else:
        raise AssertionError(f"Unknown screen kind {screen.kind}")


def answer_verify(debug: "DebugLink", screen: Screen, pages: int) -> None:
    """Read a verify flow's value, open its account info, and confirm."""
    text = flat(debug.read_layout().text_content())
    for value in screen.values:
        assert flat(value) in text
    if screen.account is not None and screen.path is not None:
        open_account_info(debug, screen.account, screen.path)
    confirm_verify(debug, pages)


def cancel_screen(debug: "DebugLink", screen: Screen) -> None:
    """Back out of one screen by the model's own cancel path."""
    if screen.kind == "danger":
        open_menu(debug)
        debug.button_actions.navigate_to_menu_item(0)
        debug.press_yes()
    elif screen.kind == "details":
        open_menu(debug)
        debug.button_actions.navigate_to_menu_item(1)
    elif screen.kind == "verify":
        open_menu(debug)
        debug.button_actions.navigate_to_menu_item(2)
        if debug.layout_type is LayoutType.Delizia:
            debug.swipe_up()
            debug.click(debug.screen_buttons.tap_to_confirm())
        else:
            debug.click(debug.screen_buttons.ok())
    else:
        debug.press_no()


def expected_responses(screens: list[Screen], cancel_at: int | None) -> list:
    """The ButtonRequests of the screens reached, then the app's answer."""
    shown = screens if cancel_at is None else screens[: cancel_at + 1]
    return [messages.ButtonRequest(name=br_name(screen.step)) for screen in shown] + [
        messages.ExtAppResponse
    ]


def run_showcase(
    session: Session,
    instance_id: int,
    name: str,
    screens: list[Screen],
    *,
    cancel_at: int | None = None,
    reply: m.Reply = m.Reply.Confirmed,
    visit_extras: bool = True,
) -> None:
    """Run one showcase, confirming every screen or cancelling at one of them."""
    answered = screens if cancel_at is None else screens[:cancel_at]
    for screen in answered:
        skip_gap(session.debug, screen.step)

    def input_flow():
        for index, screen in enumerate(screens):
            br = yield
            assert br.name == br_name(screen.step)
            if cancel_at == index:
                cancel_screen(session.debug, screen)
                return
            if screen.kind == "verify":
                assert br.pages is not None
                answer_verify(session.debug, screen, br.pages)
            elif screen.kind == "review":
                answer_review(session.debug, screen, visit_extras)
            else:
                answer_simple(session.debug, screen, br.pages or 1)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expected_responses(screens, cancel_at))
        assert modui_ext.showcase(session, instance_id, name) is reply


# ============================================================================
# Send and delegate: several screens, a final hold, and extras
# ============================================================================


def test_showcase_send(session: Session, instance_id: int):
    """Send: an address with account info, then the amounts as the last yes."""
    run_showcase(session, instance_id, "send", SEND)


@pytest.mark.parametrize("cancel_at", [0, 1], ids=["address", "summary"])
def test_showcase_send_cancel(session: Session, instance_id: int, cancel_at: int):
    """Send: backing out of either screen cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "send",
        SEND,
        cancel_at=cancel_at,
        reply=m.Reply.Cancelled,
    )


def test_showcase_delegate(session: Session, instance_id: int):
    """Delegate: several facts on one screen, then the last yes with a hold."""
    run_showcase(session, instance_id, "delegate", DELEGATE)


@pytest.mark.parametrize("cancel_at", [0, 1], ids=["facts", "final"])
def test_showcase_delegate_cancel(session: Session, instance_id: int, cancel_at: int):
    """Delegate: backing out of either screen cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "delegate",
        DELEGATE,
        cancel_at=cancel_at,
        reply=m.Reply.Cancelled,
    )


# ============================================================================
# One review: a warning, and a warning of a danger
# ============================================================================


def test_showcase_claim_owner(session: Session, instance_id: int):
    """Claim owner: an address with a warning beside it."""
    run_showcase(session, instance_id, "claim-owner", [CLAIM_OWNER])


def test_showcase_claim_owner_cancel(session: Session, instance_id: int):
    """Claim owner: backing out of the review cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "claim-owner",
        [CLAIM_OWNER],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


def test_showcase_unknown_contract(session: Session, instance_id: int):
    """Unknown contract: the danger screen goes on only when told to."""
    run_showcase(session, instance_id, "unknown-contract", [UNKNOWN_CONTRACT])


def test_showcase_unknown_contract_cancel(session: Session, instance_id: int):
    """Unknown contract: the danger screen's cancel backs out."""
    run_showcase(
        session,
        instance_id,
        "unknown-contract",
        [UNKNOWN_CONTRACT],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


def test_showcase_path_warning(session: Session, instance_id: int):
    """Path warning: an unusual path is shown as a danger."""
    run_showcase(session, instance_id, "path-warning", [PATH_WARNING])


def test_showcase_path_warning_cancel(session: Session, instance_id: int):
    """Path warning: the danger screen's cancel backs out."""
    run_showcase(
        session,
        instance_id,
        "path-warning",
        [PATH_WARNING],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


# ============================================================================
# Typed data: details first, then the owner review only when asked
# ============================================================================


@pytest.mark.parametrize("show_details", [True, False], ids=["show", "skip"])
def test_showcase_typed_data(session: Session, instance_id: int, show_details: bool):
    """Typed data: the details, then the owner review only when asked for it."""
    screens = [replace(TYPED_DATA_DETAILS, show_details=show_details)]
    if show_details:
        screens.append(TYPED_DATA_OWNER)
    run_showcase(session, instance_id, "typed-data", screens)


def test_showcase_typed_data_cancel_details(session: Session, instance_id: int):
    """Typed data: backing out of the details screen cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "typed-data",
        [TYPED_DATA_DETAILS],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


def test_showcase_typed_data_cancel_review(session: Session, instance_id: int):
    """Typed data: backing out of the owner review cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "typed-data",
        [replace(TYPED_DATA_DETAILS, show_details=True), TYPED_DATA_OWNER],
        cancel_at=1,
        reply=m.Reply.Cancelled,
    )


# ============================================================================
# Verify address and public key: the value, account info, and a confirm
# ============================================================================


def test_showcase_get_address(session: Session, instance_id: int):
    """Get address: the address and its account info, then a confirm."""
    run_showcase(session, instance_id, "get-address", [GET_ADDRESS])


def test_showcase_get_address_cancel(session: Session, instance_id: int):
    """Get address: the "does not match" path cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "get-address",
        [GET_ADDRESS],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


def test_showcase_get_pubkey(session: Session, instance_id: int):
    """Get public key: the key and its account info, then a confirm."""
    run_showcase(session, instance_id, "get-pubkey", [GET_PUBKEY])


def test_showcase_get_pubkey_cancel(session: Session, instance_id: int):
    """Get public key: the "does not match" path cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "get-pubkey",
        [GET_PUBKEY],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


# ============================================================================
# Contract data and signing progress
# ============================================================================


def test_showcase_contract_data(session: Session, instance_id: int):
    """Contract data: an address and the call data's hex, paged."""
    run_showcase(session, instance_id, "contract-data", [CONTRACT_DATA])


def test_showcase_contract_data_cancel(session: Session, instance_id: int):
    """Contract data: backing out of the review cancels the flow."""
    run_showcase(
        session,
        instance_id,
        "contract-data",
        [CONTRACT_DATA],
        cancel_at=0,
        reply=m.Reply.Cancelled,
    )


def test_showcase_signing_progress(session: Session, instance_id: int):
    """Signing progress: uncounted and counted work, then the done screen."""
    run_showcase(session, instance_id, "signing-progress", [SIGNED])
