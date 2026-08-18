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

"""Show an address on the device, labelled from WARD.

THE HOST NAMES THE ADDRESS AND NOTHING ELSE. There is no way to attach a label here,
because a label the host supplied would be a claim about the recipient made on the screen
the user checks the recipient against. The device resolves it, from the host's WARD replica
or from its own store, and says on screen which one it used.

That is why this takes a `provider`. If the session has synced (`ward.sync` ->
`ward.ingest_attestation` -> `ward.reconcile`), the device PULLS the entry mid-workflow and
checks it against the root it trusts, exactly as `ward.get_entry` does -- so the caller must
be ready to answer a `WardEntryRequest` while its own call is in flight. If the session has
NOT synced, the device reads its own store and no pull is emitted at all, so the provider is
simply never called; passing one costs nothing and omitting one is only safe for a caller
that knows it never synced.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import messages
from .ward import Answer, EntryProvider, _call_answering_pulls

if TYPE_CHECKING:
    from .client import Session


def _no_entry(_entry_key: bytes) -> Answer:
    """The provider for a caller with nothing to serve: a well-formed "I hold none".

    NOT the same as declining to answer -- the device is owed a reply to a pull it emitted,
    and this one is refused if the device holds a root, since an unwitnessed absence is
    exactly what a host hiding an entry would send.
    """
    return Answer()


def show_address(
    session: "Session",
    address: str,
    *,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    case_sensitive: bool = True,
    chunkify: bool = False,
    app_id: Optional[str] = None,
    provider: Optional[EntryProvider] = None,
) -> str:
    """Display `address` on the device with its WARD label, if one resolves.

    `app_id` is the WARD domain the label is looked up in -- the same domain a
    `ward.set_entry` wrote it under. `subtitle` is shown ONLY when no label resolves; a
    resolved label takes the slot.

    Returns the address that was shown, so a caller can use this where it would otherwise
    have used a `get_address` result.
    """
    _call_answering_pulls(
        session,
        messages.DisplayAddress(
            address=address,
            title=title,
            subtitle=subtitle,
            case_sensitive=case_sensitive,
            chunkify=chunkify,
            app_id=app_id,
        ),
        provider or _no_entry,
    )
    return address
