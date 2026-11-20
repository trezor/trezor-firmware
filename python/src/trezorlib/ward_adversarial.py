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

"""
===========================================================================================
  ADVERSARIAL TESTS -- A HOSTILE HOST, ON PURPOSE. NOT FOR NORMAL USE.
===========================================================================================

Client helpers for wardd's adversarial-test calls (`packages/wardd/src/adversarial.ts`): each
makes wardd serve the device an OLDER state than it stored, which the device must refuse. They
work only against a wardd started with `--adversarial-tests`, and nothing in the normal
`ward_relay` paths uses them.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .ward_relay import WarddClient, WarddProvider, session_device

if TYPE_CHECKING:
    from .client import Session


def adversarial_catch_up_to_older_head(
    session: "Session", client: WarddClient, counter: int
) -> dict:
    """ADVERSARIAL TEST: have wardd offer the device the older head at `counter`. The device
    must refuse it, which arrives as `WarddError` with code `device_failure`."""
    return client.call(
        "adversarialCatchUpToOlderHead", {"counter": counter}, session_device(session)
    )


class AdversarialOlderTreeProvider(WarddProvider):
    """ADVERSARIAL TEST: answers every pull from the tree at the older head `counter`, as a host
    serving stale state would. The device must refuse the read."""

    def __init__(self, client: WarddClient, counter: int) -> None:
        super().__init__(client)
        self.counter = counter

    def _serve(self, entry_key: bytes) -> dict:
        return self.client.call(
            "adversarialServeEntry",
            {"request": {"entry_key": entry_key.hex()}, "counter": self.counter},
        )
