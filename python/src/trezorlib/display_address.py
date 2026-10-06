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

The host names the address and nothing else; the device resolves the label, from the host's
replica or its own store, and says which. On a synced session the device PULLS the entry
mid-workflow (as `ward.get_entry` does), so pass a `provider`; unsynced, it is never called.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from . import messages
from .ward import Answer, EntryProvider, _call_answering_pulls

if TYPE_CHECKING:
    from .client import Session


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
    """Display `address` with its WARD label (looked up in domain `app_id`), if one resolves.
    `subtitle` is shown only when none does. Returns the address shown."""
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
        # no provider: a well-formed "I hold none", refused once the device holds a root
        provider or (lambda _entry_key: Answer()),
    )
    return address
