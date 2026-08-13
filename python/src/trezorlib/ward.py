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

**The store is keyed by the opaque `entry_key`, not by the identifier.** The device
derives that key from a seed this library does not have, so a host CANNOT compute it --
that is the whole point, and why every call returns the key it was asked for. Anything
here that could derive an entry_key would defeat the property being bought.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, NamedTuple, Optional

from . import messages

if TYPE_CHECKING:
    import protobuf

    from .client import Session

# Answers a device pull: entry_key -> value, or None for "no such entry".
EntryProvider = Callable[[bytes], Optional[bytes]]


class WardResult(NamedTuple):
    """What a WARD call returns.

    `entry_key` is the opaque 32-byte path the device asked about. Callers need it to
    apply a confirmed write or delete, since it is the key their store is organised by
    and they have no other way to learn it.
    """

    success: messages.Success
    entry_key: bytes


def _call_answering_pulls(
    session: "Session",
    msg: "protobuf.MessageType",
    provider: EntryProvider,
) -> WardResult:
    """Drive a WARD workflow, answering every `WARDEntryRequest` from `provider`.

    Note `Session.call` is used WITHOUT `expect=`: it defaults to the `MessageType`
    base, so either a `WARDEntryRequest` or the final `Success` is accepted and we
    dispatch on the type. Using `call_raw` instead would lose Failure-to-exception
    conversion and the button-request handling, both of which we want.

    The loop is not bounded to a single pull on purpose: what a later phase adds is more
    round trips (proof material, lineage), not a different mechanism. Every phase-1
    workflow pulls exactly once, and all pulls in one workflow name the same entry, so
    the last key seen is the workflow's key.
    """
    res = session.call(msg)
    entry_key = b""

    while isinstance(res, messages.WARDEntryRequest):
        entry_key = res.entry_key or b""
        res = session.call(messages.WARDEntryAck(value=provider(entry_key)))

    if not isinstance(res, messages.Success):
        raise RuntimeError(
            f"unexpected response to {type(msg).__name__}: {type(res).__name__}"
        )

    return WardResult(res, entry_key)


def get_entry(
    session: "Session",
    app_id: str,
    identifier: bytes,
    provider: EntryProvider,
) -> WardResult:
    """Ask the device to display the host-held entry for (app_id, identifier).

    The device derives the keyed path and asks `provider` for it; `provider` returning
    None means "no such entry" -- the device says so on screen rather than showing an
    empty value.
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
) -> WardResult:
    """Ask the device to confirm creating or replacing the entry for (app_id, identifier).

    The device pulls the current value from `provider` first, so it shows an "Add entry"
    screen when the entry is new and an "Update entry" screen naming what it replaces
    when it is not.

    **The device does not write.** On `Success` the caller must apply the change to its
    own store, under the returned `entry_key`; a `Success` that the caller ignores means
    the user confirmed a write that never happened.

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
) -> WardResult:
    """Ask the device to confirm deleting the entry for (app_id, identifier).

    The device pulls the entry first so the screen can name the value being removed, and
    fails with "no such entry" if `provider` reports none -- delete is deliberately not
    idempotent here, since a no-op delete means the caller and its own store disagree.

    **The device does not delete.** On `Success` the caller must remove the entry from
    its own store, under the returned `entry_key`.
    """
    return _call_answering_pulls(
        session,
        messages.WARDDeleteEntry(app_id=app_id, identifier=identifier),
        provider,
    )


def dict_provider(entries: dict[bytes, bytes]) -> EntryProvider:
    """An `EntryProvider` backed by a plain dict keyed by `entry_key`.

    This is what stands in for the host database in this phase; later phases replace it
    with a real store that also holds the proof material. Note what it is NOT keyed by:
    there is no identifier anywhere in it, which is the property the keyed path buys, and
    it is why a host cannot enumerate or correlate what it holds.

    Reads only. Applying a confirmed write or delete to `entries` is the caller's job --
    see `set_entry` and `delete_entry`, which return the key to apply it under.
    """

    def provider(entry_key: bytes) -> Optional[bytes]:
        return entries.get(entry_key)

    return provider
