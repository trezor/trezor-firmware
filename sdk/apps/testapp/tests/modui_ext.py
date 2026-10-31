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

"""The modui layouts the testapp exposes, one request per layout."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Union

from . import testapp_ext
from .generated import messages as m

if TYPE_CHECKING:
    from trezorlib import protobuf
    from trezorlib.client import Session


def show(
    session: "Session", instance_id: int, request: "protobuf.MessageType"
) -> m.Reply:
    """Show one layout and return how it ended."""
    result = testapp_ext.call_ext(
        session, instance_id, msg_data=request, expect=[m.UiResult]
    )
    return m.Reply(result.reply)


def showcase(session: "Session", instance_id: int, name: str) -> m.Reply:
    """Run one flow from the API reference's examples, by name."""
    return show(session, instance_id, m.Showcase(name=name))


def progress(
    session: "Session",
    instance_id: int,
    label: str,
    total: int | None,
    steps: Iterable[Union[int, str]] = (),
) -> m.Reply:
    """Run a progress, report `steps` one by one, then end it.

    An int reports that many units of work done; a str changes the label under
    the bar.
    """
    testapp_ext.call_ext(
        session,
        instance_id,
        msg_data=m.ShowProgress(label=label, total=total),
        expect=[m.ProgressTick],
    )
    for step in steps:
        if isinstance(step, str):
            request = m.ProgressLabel(label=step)
        else:
            request = m.ProgressStep(units=step)
        testapp_ext.call_ext(
            session, instance_id, msg_data=request, expect=[m.ProgressTick]
        )
    result = testapp_ext.call_ext(
        session, instance_id, msg_data=m.ProgressEnd(), expect=[m.UiResult]
    )
    return m.Reply(result.reply)


def field(
    kind: m.FieldKind, value: Union[str, bytes], label: str | None = None
) -> m.Field:
    """One fact: what it is, its value, and a label unless it is a note or
    warning. A string value is UTF-8 on the wire."""
    if isinstance(value, str):
        value = value.encode()
    return m.Field(kind=kind, label=label, value=value)


def text(label: str, value: str) -> m.Field:
    """Words or a number, shown as written."""
    return field(m.FieldKind.Text, value, label)


def amount(label: str, value: str, ticker: str) -> m.Field:
    """A sum, formatted by the app, and the ticker of what it counts."""
    fact = field(m.FieldKind.Amount, value, label)
    fact.ticker = ticker
    return fact


def address(label: str, value: str) -> m.Field:
    """Something compared character by character."""
    return field(m.FieldKind.Address, value, label)


def data(label: str, value: bytes) -> m.Field:
    """Raw bytes, shown as hex and paged."""
    return field(m.FieldKind.Data, value, label)


def note(value: str) -> m.Field:
    """A sentence with no label."""
    return field(m.FieldKind.Note, value)


def warning(value: str) -> m.Field:
    """A sentence to weigh before confirming."""
    return field(m.FieldKind.Warning, value)


def extras(*items: tuple[str, Iterable[m.Field]]) -> list[m.Extra]:
    """Extras from (label, fields) pairs."""
    return [m.Extra(label=label, fields=list(fields)) for label, fields in items]
