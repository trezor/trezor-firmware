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
from typing import TYPE_CHECKING

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


def progress(
    session: "Session",
    instance_id: int,
    label: str,
    total: int | None,
    steps: Iterable[int] = (),
) -> m.Reply:
    """Run a progress, report `steps` units of work one by one, then end it."""
    testapp_ext.call_ext(
        session,
        instance_id,
        msg_data=m.ShowProgress(label=label, total=total),
        expect=[m.ProgressTick],
    )
    for units in steps:
        testapp_ext.call_ext(
            session,
            instance_id,
            msg_data=m.ProgressStep(units=units),
            expect=[m.ProgressTick],
        )
    result = testapp_ext.call_ext(
        session, instance_id, msg_data=m.ProgressEnd(), expect=[m.UiResult]
    )
    return m.Reply(result.reply)


def props(pairs: Iterable[tuple[str, str]]) -> list[m.Property]:
    """Properties from (key, value) pairs."""
    return [m.Property(key=k, value=v) for k, v in pairs]


def extras(*items: tuple[str, Iterable[tuple[str, str]]]) -> list[m.ExtraItem]:
    """Extras from (label, [(key, value), ...]) pairs."""
    return [m.ExtraItem(label=label, props=props(pairs)) for label, pairs in items]
