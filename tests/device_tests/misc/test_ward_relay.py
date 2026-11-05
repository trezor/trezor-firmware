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

"""WARD end to end through the HWI path: the device, the trezorlib WARD adapter, and a real wardd.

wardd runs every flow -- sync, the write round, lookup, the proofs, the debug WM -- and the
adapter only relays. Nothing here builds a proof or signs for the WM: if the device accepts a
write and later proves it, wardd did the work.

Needs a trezor-suite checkout with `packages/wardd` and its dependencies installed:
`WARDD_SUITE_DIR=/path/to/trezor-suite`. Skipped otherwise.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import time
import typing as t
from pathlib import Path

import pytest

from trezorlib.debuglink import DebugSession as Session
from trezorlib.ward_relay import WardAdapter, WarddClient

from trezorlib.testing.device_handler import BackgroundDeviceHandler

SUITE_DIR = os.environ.get("WARDD_SUITE_DIR")

pytestmark = [
    pytest.mark.models("core"),
    pytest.mark.skipif(not SUITE_DIR, reason="WARDD_SUITE_DIR is not set"),
]

APP = "bitcoin"
NETWORK = "btc"


@pytest.fixture
def wardd(tmp_path: Path) -> t.Iterator[WarddClient]:
    """A throwaway wardd: in-memory store, debug WM, its own port and token."""
    assert SUITE_DIR is not None
    token = secrets.token_hex(16)
    (tmp_path / "token").write_text(token)
    port = 30000 + secrets.randbelow(20000)
    proc = subprocess.Popen(
        [
            "node",
            "--import",
            "tsx",
            "src/cli.ts",
            "--memory",
            "--port",
            str(port),
            "--data-dir",
            str(tmp_path),
            "--token-file",
            str(tmp_path / "token"),
        ],
        cwd=Path(SUITE_DIR) / "packages" / "wardd",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline()
        assert "wardd listening" in line, line + proc.stdout.read()
        with WarddClient(token=token, url=f"ws://127.0.0.1:{port}") as client:
            yield client
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def _confirmed(session: Session, fn: t.Callable[[Session], t.Any]) -> t.Any:
    """Run `fn` while approving the one confirmation screen it raises.

    wardd syncs the session before the screen comes up, so the press waits for a screen other
    than the homescreen: one sent straight away would land before the confirmation exists.
    """
    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(session, fn)
            debug = dev.debuglink()
            deadline = time.monotonic() + 30
            while "Homescreen" in debug.read_layout(wait=False).json_str:
                assert time.monotonic() < deadline, "no confirmation screen came up"
                time.sleep(0.1)
            debug.press_yes()
            return dev.result()


def test_ward_relay_write_lookup_delete(session: Session, wardd: WarddClient) -> None:
    adapter = WardAdapter(session, wardd)

    synced = adapter.sync()
    assert synced["counter"] == 0 and synced["root"] == ""
    ward_id = synced["wardId"]

    # insert: the device confirms the intent, pulls the (empty-tree) proof, seals the leaf
    inserted = _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(APP, "bc1qrelay", NETWORK, {"label": "first"}),
    )
    assert inserted["wardId"] == ward_id
    assert inserted["counter"] == 1 and inserted["root"]

    found = adapter.lookup(APP, "bc1qrelay", NETWORK)
    assert found["valid"] and found["isMember"]
    assert found["metadata"] == {"label": "first"}

    # an absent address: a device-proven non-membership, served from wardd's witness
    absent = adapter.lookup(APP, "bc1qother", NETWORK)
    assert absent["valid"] and not absent["isMember"]
    assert "metadata" not in absent

    # update: the device pulls the membership proof of the old leaf
    updated = _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(APP, "bc1qrelay", NETWORK, {"label": "second"}),
    )
    assert updated["counter"] == 2
    assert adapter.lookup(APP, "bc1qrelay", NETWORK)["metadata"] == {"label": "second"}

    # delete empties the tree, and the absence is then proven on the device
    deleted = _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(APP, "bc1qrelay", NETWORK, delete=True),
    )
    assert deleted["counter"] == 3 and deleted["root"] == ""
    gone = adapter.lookup(APP, "bc1qrelay", NETWORK)
    assert gone["valid"] and not gone["isMember"]


def test_ward_relay_multi_entry_tree(session: Session, wardd: WarddClient) -> None:
    """Proofs with real branches: with one leaf every proof is empty, so wardd's trie hashing is
    only checked against the device's once the tree has several entries."""
    adapter = WardAdapter(session, wardd)
    addresses = ["bc1qalpha", "bc1qbravo", "bc1qcharlie", "bc1qdelta"]

    # each insert into a non-empty tree is proven absent first (a witness with a real path)
    for counter, address in enumerate(addresses, start=1):
        written = _confirmed(
            session,
            lambda s, a=address: WardAdapter(s, wardd).update(APP, a, NETWORK, {"label": a}),
        )
        assert written["counter"] == counter

    # every entry is a proven member, under the root the device installed
    for address in addresses:
        found = adapter.lookup(APP, address, NETWORK)
        assert found["valid"] and found["isMember"], address
        assert found["metadata"] == {"label": address}
    absent = adapter.lookup(APP, "bc1qecho", NETWORK)
    assert absent["valid"] and not absent["isMember"]

    # an update in the middle of the tree, then a delete that re-parents a sibling
    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(APP, "bc1qbravo", NETWORK, {"label": "B"}),
    )
    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(APP, "bc1qcharlie", NETWORK, delete=True),
    )
    assert adapter.lookup(APP, "bc1qbravo", NETWORK)["metadata"] == {"label": "B"}
    gone = adapter.lookup(APP, "bc1qcharlie", NETWORK)
    assert gone["valid"] and not gone["isMember"]
    for address in ("bc1qalpha", "bc1qdelta"):
        kept = adapter.lookup(APP, address, NETWORK)
        assert kept["valid"] and kept["isMember"], address


def test_ward_relay_display_address(session: Session, wardd: WarddClient) -> None:
    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(APP, "bc1qshown", NETWORK, {"label": "shown"}),
    )

    # the native DisplayAddress pulls the label proof; the adapter answers it through wardd
    shown = _confirmed(
        session, lambda s: WardAdapter(s, wardd).display_address(APP, "bc1qshown")
    )
    assert shown["shown"] is True
