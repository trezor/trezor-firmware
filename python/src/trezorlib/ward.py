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

Writes work the same way and pull too: the device asks for the CURRENT value so it can
show what is being replaced or removed. The device does not write -- on `Success` the
CALLER applies the change to its own store. Nothing is authenticated in this phase; see
messages-ward.proto.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from . import messages

if TYPE_CHECKING:
    import protobuf

    from .client import Session

# Answers a device pull: (app_id, identifier) -> value, or None for "no such entry".
EntryProvider = Callable[[str, bytes], Optional[bytes]]


def _call_answering_pulls(
    session: "Session",
    msg: "protobuf.MessageType",
    provider: EntryProvider,
) -> messages.Success:
    """Drive a WARD workflow, answering every `WARDEntryRequest` from `provider`.

    Note `Session.call` is used WITHOUT `expect=`: it defaults to the `MessageType`
    base, so either a `WARDEntryRequest` or the final `Success` is accepted and we
    dispatch on the type. Using `call_raw` instead would lose Failure-to-exception
    conversion and the button-request handling, both of which we want.

    The loop is not bounded to a single pull on purpose: what a later phase adds is more
    round trips (proof material, lineage), not a different mechanism.
    """
    res = session.call(msg)

    while isinstance(res, messages.WARDEntryRequest):
        req_app_id = res.app_id or ""
        req_identifier = res.identifier or b""
        res = session.call(
            messages.WARDEntryAck(value=provider(req_app_id, req_identifier))
        )

    if not isinstance(res, messages.Success):
        raise RuntimeError(
            f"unexpected response to {type(msg).__name__}: {type(res).__name__}"
        )

    return res


def get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> messages.Success:
    """Ask the device to display the host-held entry for (app_id, identifier).

    `provider` returning None means "no such entry" -- the device says so on screen
    rather than showing an empty value.
    """
    return _call_answering_pulls(
        session,
        messages.WARDGetEntry(app_id=app_id, identifier=identifier),
        provider,
    )


def set_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    value: Optional[bytes],
    provider: EntryProvider,
) -> messages.Success:
    """Ask the device to confirm creating or replacing the entry for (app_id, identifier).

    The device pulls the current value from `provider` first, so it shows an "Add entry"
    screen when the entry is new and an "Update entry" screen naming what it replaces
    when it is not.

    **The device does not write.** On `Success` the caller must apply the change to its
    own store; a `Success` that the caller ignores means the user confirmed a write that
    never happened.

    `value` is typed Optional only so callers can exercise the device-side validation --
    an absent value is rejected, because writing "nothing specified" as if it were an
    empty value would silently blank an entry. Pass b"" for a genuinely empty value.
    """
    return _call_answering_pulls(
        session,
        messages.WARDSetEntry(app_id=app_id, identifier=identifier, value=value),
        provider,
    )


def delete_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> messages.Success:
    """Ask the device to confirm deleting the entry for (app_id, identifier).

    The device pulls the entry first so the screen can name the value being removed, and
    fails with "no such entry" if `provider` reports none -- delete is deliberately not
    idempotent here, since a no-op delete means the caller and its own store disagree.

    **The device does not delete.** On `Success` the caller must remove the entry from
    its own store.
    """
    return _call_answering_pulls(
        session,
        messages.WARDDeleteEntry(app_id=app_id, identifier=identifier),
        provider,
    )


def dict_provider(entries: dict[tuple[str, bytes], bytes]) -> EntryProvider:
    """An `EntryProvider` backed by a plain dict, keyed by (app_id, identifier).

    This is what stands in for the host database in this phase; later phases replace it
    with a real store that also holds the proof material.

    Reads only. Applying a confirmed write or delete to `entries` is the caller's job --
    see `set_entry` and `delete_entry`.
    """

    def provider(app_id: str, identifier: bytes) -> Optional[bytes]:
        return entries.get((app_id, identifier))

    return provider
