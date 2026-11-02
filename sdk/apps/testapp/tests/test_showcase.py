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

"""The testapp's example flows, composed on the host and run end to end on the
device.

Each showcase is a flow an app would show, with sample values in place of a real
transaction's, so confirming or cancelling it proves the firmware can draw and
answer every screen it contains. The app exposes the modui endpoints one to one; the
flows themselves live in `testapp_host.showcases`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pytest

from trezorlib.debuglink import DebugSession as Session

from .modui_ext import (
    SHOWCASES,
    XPUB,
    ShownExtra,
    TestApp,
    br_name,
    cancel_by_menu,
    cancel_danger,
    cancel_verify,
    confirm,
    confirm_hold,
    confirm_verify,
    flat,
    go_on_past_danger,
    m,
    open_account_info,
    open_extra,
    read_all_pages,
    screen_text,
    show_all,
    showcases,
)

if TYPE_CHECKING:
    from trezorlib.debuglink import DebugLink

RECIPIENT = "TQ9JfxgJ9JBz4GZ4MRDrjJeBdA6Mx5yYhq"
OWNER = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm"
CONTRACT = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
ACCOUNT = "TRX #1"
LOCK_PERIOD = "3 days"
PATH = "m/44'/195'/0'/0/0"

TXID = "8f2b6c1d9e4a7f30b5c2e81d6a9f4b7c3e0d5a2f8b6c1e9d4a7f3b0c5e2d81a6"
MESSAGE = "Log in to example.com at 18:05"

# `transfer(address,uint256)` and its two arguments, as the host flow passes it.
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
    """One screen of a showcase: what it is called, what it shows, and how the
    person answers it.

    `kind` is how it is answered: a `review` with a tap, a `final` review with a
    hold, `details` with "Show all" when `show_details` is set and a tap
    otherwise, a `danger` by its detour, a `verify` flow by checking its value,
    and a `done` screen by dismissing it.
    """

    step: str
    title: str | None = None
    values: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    extras: tuple[ShownExtra, ...] = ()
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
        kind="final",
    ),
    Screen(step="send/done", values=("Transaction sent",), kind="done"),
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
        kind="final",
    ),
    Screen(step="delegate/done", values=("Delegation confirmed",), kind="done"),
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
    labels=("Type", "Contains"),
    kind="details",
    show_details=True,
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

CONSENT = Screen(
    step="stake/consent",
    title="Stake",
    values=("Stake your TRX with Everstake? You can unstake at any time.",),
)

SWAP = [
    Screen(
        step="swap",
        title="Swap",
        values=(
            "-1,000 TRX",
            "+118.40 USDC",
            RECIPIENT,
            "1.2 TRX",
            "The price impact is 4.2%.",
        ),
        labels=("You pay", "You receive", "Recipient", "Network fee"),
        extras=(
            ("Provider", (("Provider", "Changelly"), ("Quote ID", "a3f9-77c1"))),
            ("Refund", (("Refund address", OWNER),)),
            ("Fee details", (("Provider fee", "0.50 USDC"), ("Fee limit", "10 TRX"))),
            (
                "Route",
                (
                    ("Hop 1", "TRX to USDT on SunSwap"),
                    ("Hop 2", "USDT to USDC on Curve"),
                ),
            ),
            ACCOUNT_INFO,
        ),
        kind="final",
    ),
    Screen(step="swap/done", values=("Swap confirmed",), kind="done"),
]

FEE_BUMP = [
    Screen(
        step="bump_fee",
        title="Bump fee",
        values=(TXID, "0.00000564 BTC", "0.00001692 BTC", "0.00001128 BTC"),
        labels=("Transaction ID", "Old fee", "New fee", "Increased by"),
        extras=(
            ("Fee rate", (("Old fee rate", "4 sat/vB"), ("New fee rate", "12 sat/vB"))),
        ),
        kind="final",
    ),
    Screen(step="bump_fee/done", values=("Transaction replaced",), kind="done"),
]

SIGN_MESSAGE = [
    Screen(
        step="sign_message",
        title="Sign message",
        values=(RECIPIENT, MESSAGE),
        labels=("Address", "Message"),
        kind="final",
    ),
    Screen(step="sign_message/done", values=("Message signed",), kind="done"),
]

VERIFY_MESSAGE = [
    Screen(
        step="verify_message",
        title="Verify message",
        values=(RECIPIENT, MESSAGE),
        labels=("Address", "Message"),
    ),
    Screen(
        step="verify_message/valid",
        values=("The signature is valid",),
        kind="done",
    ),
]

SIGNED = Screen(
    step="signed",
    values=("Transaction signed",),
    kind="done",
)

# Every showcase, by the name `SHOWCASES` takes: the screens it shows when the
# person says yes to each of them.
FLOWS: dict[str, list[Screen]] = {
    # An address with account info, the amounts as the last yes, then done.
    "send": SEND,
    # Several facts on one screen, the last yes with a hold, then done.
    "delegate": DELEGATE,
    # An address with a warning beside it.
    "claim-owner": [CLAIM_OWNER],
    # The danger screen goes on only when told to.
    "unknown-contract": [UNKNOWN_CONTRACT],
    # An unusual path is shown as a danger.
    "path-warning": [PATH_WARNING],
    # The short version, then the owner review once the details are asked for.
    "typed-data": [TYPED_DATA_DETAILS, TYPED_DATA_OWNER],
    # The address and its account info, then a confirm.
    "get-address": [GET_ADDRESS],
    # The key and its account info, then a confirm.
    "get-pubkey": [GET_PUBKEY],
    # An address and the call data's hex, paged.
    "contract-data": [CONTRACT_DATA],
    # A question with no value to check, answered yes.
    "consent": [CONSENT],
    # Both amounts, the recipient and a caution, with five extras, held, then done.
    "swap": SWAP,
    # The transaction and its old and new fee, with the rates as an extra, held,
    # then done.
    "fee-bump": FEE_BUMP,
    # The address and the message as text, held, then done.
    "sign-message": SIGN_MESSAGE,
    # The address and the message, then the result.
    "verify-message": VERIFY_MESSAGE,
    # Uncounted and counted work, then the done screen.
    "signing-progress": [SIGNED],
}

# Every screen that asks something, as its showcase and its index there: backing
# out of it cancels the showcase. A done screen asks nothing.
CANCELS = [
    pytest.param(name, index, id=name if index == 0 else f"{name}-{index}")
    for name, screens in FLOWS.items()
    for index, screen in enumerate(screens)
    if screen.kind != "done"
]


def check_shown(screen: Screen, shown: str) -> None:
    """Check that a screen's text holds its values and labels."""
    for value in screen.values:
        assert flat(value) in shown
    for label in screen.labels:
        assert flat(label) in shown


def answer_review(debug: "DebugLink", screen: Screen, pages: int) -> None:
    """Read a review's title, extras and every page, then answer it as its kind
    says: a review, a final one, details, or a danger.

    `pages` is the count the ButtonRequest reported. Delizia's review traces no
    page count of its own, so the ButtonRequest is the only source of truth there.
    """
    assert screen.title is not None
    assert screen.title in debug.read_layout().title()

    for index in range(len(screen.extras)):
        open_extra(debug, screen.extras, index)

    check_shown(screen, flat("".join(read_all_pages(debug, pages))))

    if screen.kind == "danger":
        go_on_past_danger(debug)
    elif screen.kind == "final":
        confirm_hold(debug)
    elif screen.kind == "details" and screen.show_details:
        show_all(debug, len(screen.extras))
    else:
        confirm(debug)


def answer_verify(debug: "DebugLink", screen: Screen, pages: int) -> None:
    """Read a verify flow's value, open its account info, and confirm."""
    check_shown(screen, flat(debug.read_layout().text_content()))
    if screen.account is not None and screen.path is not None:
        open_account_info(debug, present=(screen.account, screen.path))
    confirm_verify(debug, pages)


def answer_done(debug: "DebugLink", screen: Screen) -> None:
    """Read a done screen and dismiss it."""
    check_shown(screen, screen_text(debug.read_layout()))
    debug.press_yes()


def cancel_screen(debug: "DebugLink", screen: Screen) -> None:
    """Back out of one screen by the model's own way out."""
    if screen.kind == "danger":
        cancel_danger(debug)
    elif screen.kind == "details":
        # Past the extras and "Show all".
        cancel_by_menu(debug, len(screen.extras) + 1)
    elif screen.kind == "verify":
        cancel_verify(debug)
    else:
        debug.press_no()


def run_showcase(
    session: Session,
    instance_id: int,
    name: str,
    screens: list[Screen],
    *,
    cancel_at: int | None = None,
) -> None:
    """Run one host-side showcase, answering every screen or backing out of the
    one at `cancel_at`, and check that it ended as the person did."""
    shown = screens if cancel_at is None else screens[: cancel_at + 1]
    expected = m.Reply.Confirmed if cancel_at is None else m.Reply.Cancelled
    app = TestApp(session, instance_id)
    seen = 0

    def input_flow():
        nonlocal seen
        for index, screen in enumerate(shown):
            br = yield
            seen += 1
            assert br.name == br_name(screen.step)
            debug = session.debug
            if index == cancel_at:
                cancel_screen(debug, screen)
            elif screen.kind == "verify":
                assert br.pages is not None
                answer_verify(debug, screen, br.pages)
            elif screen.kind == "done":
                answer_done(debug, screen)
            else:
                assert br.pages is not None
                answer_review(debug, screen, br.pages)

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert showcases.run(app, name) is expected
        assert seen == len(shown)


def test_flows_cover_showcases():
    """Every host-side showcase has its expected screens here."""
    assert set(FLOWS) == set(SHOWCASES)


@pytest.mark.parametrize("name", SHOWCASES)
def test_showcase(session: Session, instance_id: int, name: str):
    """Every screen of the showcase read and said yes to: the flow confirms."""
    run_showcase(session, instance_id, name, FLOWS[name])


def test_showcase_typed_data_skip(session: Session, instance_id: int):
    """Typed data: confirming the short version skips the owner review."""
    details = replace(TYPED_DATA_DETAILS, show_details=False)
    run_showcase(session, instance_id, "typed-data", [details])


@pytest.mark.parametrize("name, cancel_at", CANCELS)
def test_showcase_cancel(session: Session, instance_id: int, name: str, cancel_at: int):
    """Backing out of any screen that asks something cancels the flow, and
    nothing after it is shown."""
    run_showcase(session, instance_id, name, FLOWS[name], cancel_at=cancel_at)
