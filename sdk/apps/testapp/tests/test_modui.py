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
from .modui_ext import extras, props
from .testapp_ext import SdkError

EXTRAS = extras(
    ("Account info", [("Account", "Tron #1"), ("Path", "m/44'/195'/0'")]),
    ("Fee info", [("Fee limit", "100 TRX")]),
)


@dataclass
class Layout:
    """One layout: how to ask for it, and a title and a text it shows."""

    make: Callable[..., object]
    title: str
    text: str

    def request(self, **kwargs) -> object:
        return self.make(**kwargs)


LAYOUTS = {
    "action": Layout(
        lambda **kw: m.ConfirmAction(
            title="Approve", action="Approve the contract?", br="modui/action", **kw
        ),
        title="Approve",
        text="Approve the contract?",
    ),
    "value": Layout(
        lambda **kw: m.ConfirmValue(
            title="Recipient", value="Hello value", br="modui/value", **kw
        ),
        title="Recipient",
        text="Hello value",
    ),
    "data": Layout(
        lambda **kw: m.ConfirmData(
            title="Data", data=bytes.fromhex("cafebabe"), br="modui/data", **kw
        ),
        title="Data",
        text="cafebabe",
    ),
    "properties": Layout(
        lambda **kw: m.ConfirmProperties(
            title="Stake",
            props=props([("Resource", "Energy")]),
            br="modui/properties",
            **kw,
        ),
        title="Stake",
        text="Energy",
    ),
    "summary": Layout(
        lambda **kw: m.ConfirmSummary(
            title="Summary",
            amount_label="Amount",
            amount="1 TRX",
            fee_label="Fee",
            fee="0.1 TRX",
            br="modui/summary",
            **kw,
        ),
        title="Summary",
        text="1 TRX",
    ),
    "notice": Layout(
        lambda **kw: m.ShowNotice(
            severity=m.Severity.Warning,
            title="Unknown token",
            content="Check the contract.",
            br="modui/notice",
            **kw,
        ),
        title="Unknown token",
        text="Check the contract.",
    ),
}

ALL = pytest.mark.parametrize("name", list(LAYOUTS))

# Where a model draws less than the layout asks for: (layout type, what) ->
# why. The test is not run there; it is reported as an expected failure.
GAPS = {
    (LayoutType.Delizia, "summary extras"): (
        "WIP: confirm_summary has no menu a caller can drive on this model; "
        "it shows its own, so the extras are unreachable"
    ),
    (LayoutType.Delizia, "value footer"): (
        "confirm_value draws no footer on this model, so a hint or warning is not shown"
    ),
    (LayoutType.Eckhart, "notice extras"): (
        "WIP: only the info notice has a menu a caller can drive on this model; "
        "a warning is drawn without it, so the extras are unreachable"
    ),
}


def skip_gap(session: Session, what: str) -> None:
    reason = GAPS.get((session.debug.layout_type, what))
    if reason is not None:
        pytest.xfail(reason)


def expect_one_button_request(br: str) -> list:
    """The responses of one layout: a single ButtonRequest, however long the
    person spends in its menu, then the app's answer."""
    return [messages.ButtonRequest(name=br), messages.ExtAppResponse]


@ALL
def test_confirm(session: Session, instance_id: int, name: str):
    layout = LAYOUTS[name]
    request = layout.request()

    def input_flow():
        yield
        screen = session.debug.read_layout()
        assert layout.title in screen.title()
        assert layout.text in screen.text_content()
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.br))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_cancel(session: Session, instance_id: int, name: str):
    request = LAYOUTS[name].request()

    def input_flow():
        yield
        session.debug.press_no()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


@ALL
def test_extras_look_and_confirm(session: Session, instance_id: int, name: str):
    """Open the menu, look at an extra, come back and confirm: the layout
    still answers once, as if the menu had never been opened."""
    skip_gap(session, f"{name} extras")
    request = LAYOUTS[name].request(extras=EXTRAS)
    debug = session.debug

    def input_flow():
        yield
        debug.click(debug.screen_buttons.menu())
        menu = debug.read_layout().text_content()
        for item in EXTRAS:
            assert item.label in menu
        debug.click(debug.screen_buttons.vertical_menu_items()[0])
        extra = debug.read_layout()
        assert "Account info" in extra.title()
        assert "Tron #1" in extra.text_content()
        debug.click(debug.screen_buttons.menu())  # close the extra
        debug.click(debug.screen_buttons.menu())  # close the menu
        debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        client.set_expected_responses(expect_one_button_request(request.br))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@ALL
def test_extras_cancel(session: Session, instance_id: int, name: str):
    """The menu's last item backs out of the layout."""
    skip_gap(session, f"{name} extras")
    request = LAYOUTS[name].request(extras=EXTRAS)
    debug = session.debug

    def input_flow():
        yield
        debug.click(debug.screen_buttons.menu())
        debug.click(debug.screen_buttons.vertical_menu_items()[len(EXTRAS)])

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


@pytest.mark.parametrize("name", ["action", "value", "properties"])
def test_final_commitment(session: Session, instance_id: int, name: str):
    """A final commitment confirms like a step, by the model's own gesture."""
    request = LAYOUTS[name].request(commitment=m.Commitment.Final)

    with session.test_ctx as client:
        client.set_input_flow(confirm_flow(session))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@pytest.mark.parametrize("footer", ["footer_hint", "footer_warning"])
def test_value_footer(session: Session, instance_id: int, footer: str):
    skip_gap(session, "value footer")
    request = LAYOUTS["value"].request(**{footer: "Check it twice"})

    def input_flow():
        yield
        # The footer is a hint under the content, not part of it.
        hints = session.debug.read_layout().find_values_by_key("instruction")
        assert any("Check it twice" in str(hint) for hint in hints)
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_value_two_footers(session: Session, instance_id: int):
    """A value takes a hint or a warning, not both: the app refuses the
    request before anything is shown, and says so rather than cancelling."""
    request = LAYOUTS["value"].request(footer_hint="hint", footer_warning="warning")

    with testapp_ext.raises(SdkError.ValueError):
        modui_ext.show(session, instance_id, request)


def test_value_address(session: Session, instance_id: int):
    address = "TQrY8tryqsYVCYS3MFbtffiPp2ccyn4STm"
    request = m.ConfirmValue(
        title="Recipient", value=address, kind=m.ValueKind.Address, br="modui/address"
    )

    def input_flow():
        yield
        shown = session.debug.read_layout().text_content()
        assert address in shown.replace(" ", "").replace("\n", "")
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_data_long(session: Session, instance_id: int):
    """Data longer than a screen is paged, and every page the model moves to
    announces itself under the layout's name until the person confirms."""
    request = m.ConfirmData(title="Data", data=bytes(range(256)) * 2, br="modui/long")

    def input_flow():
        br = yield
        assert br.pages is not None and br.pages > 1
        while True:
            session.debug.press_yes()
            br = yield
            assert br.name == request.br

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_summary_without_fee(session: Session, instance_id: int):
    request = m.ConfirmSummary(
        title="Summary", amount_label="Amount", amount="1 TRX", br="modui/nofee"
    )

    def input_flow():
        yield
        shown = session.debug.read_layout().text_content()
        assert "1 TRX" in shown
        assert "Fee" not in shown
        session.debug.press_yes()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


@pytest.mark.parametrize("severity", list(m.Severity), ids=lambda s: s.name)
def test_notice_severity(session: Session, instance_id: int, severity: m.Severity):
    request = m.ShowNotice(
        severity=severity, title="Notice", content="Something happened.", br="modui/n"
    )

    with session.test_ctx as client:
        client.set_input_flow(confirm_flow(session))
        assert modui_ext.show(session, instance_id, request) is m.Reply.Confirmed


def test_notice_cancel(session: Session, instance_id: int):
    request = LAYOUTS["notice"].request(cancel=True)

    def input_flow():
        yield
        session.debug.press_no()

    with session.test_ctx as client:
        client.set_input_flow(input_flow)
        assert modui_ext.show(session, instance_id, request) is m.Reply.Cancelled


def test_progress_is_shown(session: Session, instance_id: int):
    """The progress is up while the app works, between the host's calls. (Its
    label is drawn but not traced, so debuglink cannot read it.)"""
    testapp_ext.call_ext(
        session,
        instance_id,
        msg_data=m.ShowProgress(label="Signing...", total=3),
        expect=[m.ProgressTick],
    )
    # Nothing is in flight on the wire, so don't wait for a layout to come.
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
def test_progress(
    session: Session, instance_id: int, total: int | None, steps: list[int]
):
    reply = modui_ext.progress(session, instance_id, "Working...", total, steps)
    assert reply is m.Reply.Confirmed


def confirm_flow(session: Session):
    """An input flow confirming one layout."""

    def input_flow():
        yield
        session.debug.press_yes()

    return input_flow
