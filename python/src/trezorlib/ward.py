# This file is part of the Trezor project.
#
# Copyright (C) 2012-2019 SatoshiLabs and contributors
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

"""WARD client -- phase 1: plaintext, PULL-only.

The device stores no entries. It asks the host for the one it needs mid-workflow, so
the host must be prepared to answer a device-initiated `WARDEntryRequest` while its own
call is still in flight. That is the same shape as `btc.sign_tx` answering `TxRequest`:
call, inspect what came back, answer it, repeat until the workflow returns.

Nothing is authenticated in this phase -- see messages-ward.proto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from . import messages

if TYPE_CHECKING:
    from .client import Session

# Answers a device pull: (app_id, identifier) -> value, or None for "no such entry".
EntryProvider = Callable[[str, bytes], Optional[bytes]]


def get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> messages.Success:
    """Ask the device to display the host-held entry for (app_id, identifier).

    The device PULLS the value: it replies to our request with `WARDEntryRequest`, we
    answer from `provider`, and it then shows the value and returns `Success`.

    `provider` returning None means "no such entry" -- the device says so on screen
    rather than showing an empty value.

    Note `Session.call` is used WITHOUT `expect=`: it defaults to the `MessageType`
    base, so either a `WARDEntryRequest` or the final `Success` is accepted and we
    dispatch on the type. Using `call_raw` instead would lose Failure-to-exception
    conversion and the button-request handling, both of which we want.
    """
    res = session.call(messages.WARDGetEntry(app_id=app_id, identifier=identifier))

    while isinstance(res, messages.WARDEntryRequest):
        req_app_id = res.app_id or ""
        req_identifier = res.identifier or b""
        res = session.call(
            messages.WARDEntryAck(value=provider(req_app_id, req_identifier))
        )

    if not isinstance(res, messages.Success):
        raise RuntimeError(f"unexpected response to WARDGetEntry: {type(res).__name__}")

    return res


def dict_provider(entries: dict[tuple[str, bytes], bytes]) -> EntryProvider:
    """An `EntryProvider` backed by a plain dict, keyed by (app_id, identifier).

    This is what stands in for the host database in this phase; later phases replace it
    with a real store that also holds the proof material.
    """

    def provider(app_id: str, identifier: bytes) -> Optional[bytes]:
        return entries.get((app_id, identifier))

    return provider
