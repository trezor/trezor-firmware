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
import threading
import time
import typing as t
from pathlib import Path

import pytest

from tools.ward_manager import DEBUG_SEED, WardManager, WardManagerServer
from trezorlib.debuglink import DebugSession as Session
from trezorlib.testing.device_handler import BackgroundDeviceHandler
from trezorlib.ward_relay import WardAdapter, WarddClient

SUITE_DIR = os.environ.get("WARDD_SUITE_DIR")

pytestmark = [
    pytest.mark.models("core"),
    pytest.mark.skipif(not SUITE_DIR, reason="WARDD_SUITE_DIR is not set"),
]

APP = "bitcoin"
NETWORK = "btc"


@pytest.fixture(params=("mock", "http"))
def wm_url(request: pytest.FixtureRequest, tmp_path: Path) -> t.Iterator[str | None]:
    if request.param == "mock":
        yield None
        return

    manager = WardManager(tmp_path / "wm.sqlite3", DEBUG_SEED)
    try:
        with WardManagerServer(manager, port=0) as server:
            thread = threading.Thread(target=server.serve_forever)
            thread.start()
            try:
                yield f"http://127.0.0.1:{server.server_port}"
            finally:
                server.shutdown()
                thread.join()
    finally:
        manager.close()


@pytest.fixture
def wardd_port() -> int:
    return 30000 + secrets.randbelow(20000)


@pytest.fixture
def wardd(
    tmp_path: Path, wm_url: str | None, wardd_port: int
) -> t.Iterator[WarddClient]:
    """A throwaway wardd with either the mock or the real HTTP WARD Manager."""
    assert SUITE_DIR is not None
    token = secrets.token_hex(16)
    (tmp_path / "token").write_text(token)
    port = wardd_port
    # wardd falls back to WARD_MANAGER_URL / WARD_MANAGER_PORT when no --wm-url is given;
    # tools/ward_stack.py exports both, so the "mock" variant would otherwise talk to
    # the stack's persistent manager instead of its own in-process mock.
    env = {
        name: value
        for name, value in os.environ.items()
        if name not in ("WARD_MANAGER_URL", "WARD_MANAGER_PORT")
    }
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
            *(["--wm-url", wm_url] if wm_url else []),
        ],
        cwd=Path(SUITE_DIR) / "packages" / "wardd",
        env=env,
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


def _confirmed(
    session: Session, fn: t.Callable[[Session], t.Any], expected_text: str | None = None
) -> t.Any:
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
            if expected_text is not None:
                assert expected_text in debug.read_layout(wait=False).json_str
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
        lambda s: WardAdapter(s, wardd).update(
            APP, "bc1qrelay", NETWORK, {"label": "first"}
        ),
    )
    assert inserted["wardId"] == ward_id
    assert inserted["counter"] == 1 and inserted["root"]

    found = adapter.lookup(APP, "bc1qrelay", NETWORK)
    assert found["valid"] and found["isMember"]
    assert "metadata" not in found

    # an absent address: a device-proven non-membership, served from wardd's witness
    absent = adapter.lookup(APP, "bc1qother", NETWORK)
    assert absent["valid"] and not absent["isMember"]
    assert "metadata" not in absent

    # update: the device pulls the membership proof of the old leaf
    updated = _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(
            APP, "bc1qrelay", NETWORK, {"label": "second"}
        ),
    )
    assert updated["counter"] == 2
    assert "metadata" not in adapter.lookup(APP, "bc1qrelay", NETWORK)

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
            lambda s, a=address: WardAdapter(s, wardd).update(
                APP, a, NETWORK, {"label": a}
            ),
        )
        assert written["counter"] == counter

    # every entry is a proven member, under the root the device installed
    for address in addresses:
        found = adapter.lookup(APP, address, NETWORK)
        assert found["valid"] and found["isMember"], address
        assert "metadata" not in found
    absent = adapter.lookup(APP, "bc1qecho", NETWORK)
    assert absent["valid"] and not absent["isMember"]

    # an update in the middle of the tree, then a delete that re-parents a sibling
    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(
            APP, "bc1qbravo", NETWORK, {"label": "B"}
        ),
    )
    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(
            APP, "bc1qcharlie", NETWORK, delete=True
        ),
    )
    assert "metadata" not in adapter.lookup(APP, "bc1qbravo", NETWORK)
    gone = adapter.lookup(APP, "bc1qcharlie", NETWORK)
    assert gone["valid"] and not gone["isMember"]
    for address in ("bc1qalpha", "bc1qdelta"):
        kept = adapter.lookup(APP, address, NETWORK)
        assert kept["valid"] and kept["isMember"], address


def test_ward_relay_display_address(session: Session, wardd: WarddClient) -> None:
    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(
            APP, "bc1qshown", NETWORK, {"label": "shown"}
        ),
    )

    # the native DisplayAddress pulls the label proof; the adapter answers it through wardd
    shown = _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).display_address(APP, "bc1qshown"),
        expected_text="shown",
    )
    assert shown["shown"] is True


def test_ward_relay_list_entries(session: Session, wardd: WarddClient) -> None:
    """The verified listing through wardd: the device walks its root and pulls every node via
    the adapter's `answerNodeRequest`; each entry appears on its own screen, and only counts
    come back."""
    labels = {"bc1qlist1": "one", "bc1qlist2": "two", "bc1qlist3": "three"}
    for address, label in labels.items():
        _confirmed(
            session,
            lambda s, a=address, text=label: WardAdapter(s, wardd).update(
                APP, a, NETWORK, {"label": text}
            ),
        )

    screens = []
    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session, lambda s: WardAdapter(s, wardd).list_entries(app_id=APP)
            )
            debug = dev.debuglink()
            deadline = time.monotonic() + 30
            while "Homescreen" in debug.read_layout(wait=False).json_str:
                assert time.monotonic() < deadline, "no entry screen came up"
                time.sleep(0.1)
            for _entry in labels:
                layout = debug.read_layout()
                screens.append(" ".join(layout.screen_content().split()))
                debug.press_yes()
            listed = dev.result()

    assert (listed["shown"], listed["entries"], listed["complete"]) == (3, 3, True)
    text = " ".join(screens)
    for address, label in labels.items():
        assert address in text and label in text


def test_ward_relay_cache_entry(session: Session, wardd: WarddClient) -> None:
    """Copy an entry into the offline cache through wardd: the host names it by entry_key
    only, the device pulls its proof via the adapter and stores it."""
    from trezorlib import ward_crypto

    from ...ward_mgr_emu import device_ward_keys

    _confirmed(
        session,
        lambda s: WardAdapter(s, wardd).update(
            APP, "bc1qcached", NETWORK, {"label": "cached"}
        ),
    )
    k_path, _k_data, _k_ident = device_ward_keys()
    entry_key = ward_crypto.leaf_identity_mac(k_path, APP, b"bc1qcached", "address", 0)

    adapter = WardAdapter(session, wardd)
    try:
        first = adapter.cache_entry(entry_key)
    except Exception as e:
        if "no offline store" in str(e) and "domain" not in str(e):
            pytest.skip("firmware built without the WARD offline store (xtask --ward)")
        raise
    assert first["replaced"] is False and first["counter"] == 1
    assert adapter.cache_entry(entry_key)["replaced"] is True


def test_ward_relay_cache_follows_ward_on_another_device(
    session: Session, wardd: WarddClient
) -> None:
    """Cache backup through wardd: A caches two entries (one sticky, confirmed), backs
    the cache up, then deletes both from WARD -- its own commits drop the cached copies
    at once. Device B (same wallet, fresh storage) loads the backup: wardd syncs it
    (through the AuthCommit chain) and B checks every entry against WARD by a proof
    pulled through the adapter, so neither deleted entry comes back."""
    from trezorlib import ward_crypto

    from ...ward_mgr_emu import device_ward_keys
    from .test_ward_sticky import _device_b

    k_path, _k_data, _k_ident = device_ward_keys()

    def ek(address: str) -> bytes:
        return ward_crypto.leaf_identity_mac(k_path, APP, address.encode(), "address", 0)

    for address in ("bc1qsticky", "bc1qplain"):
        _confirmed(
            session,
            lambda s, a=address: WardAdapter(s, wardd).update(
                APP, a, NETWORK, {"label": a}
            ),
        )
    adapter = WardAdapter(session, wardd)
    try:
        # making it sticky is the user's decision: one confirmation screen
        _confirmed(
            session,
            lambda s: WardAdapter(s, wardd).cache_entry(ek("bc1qsticky"), sticky=True),
        )
    except Exception as e:
        if "this firmware has no offline store" in str(e):
            pytest.skip("firmware built without the WARD offline store (xtask --ward)")
        raise
    adapter.cache_entry(ek("bc1qplain"))
    backup = adapter.export_cache()
    assert len(backup) == 2

    for address in ("bc1qsticky", "bc1qplain"):
        _confirmed(
            session,
            lambda s, a=address: WardAdapter(s, wardd).update(
                APP, a, NETWORK, delete=True
            ),
        )

    # B: wardd syncs it to A's head, then the import checks every entry against WARD
    # by a proof -- both were deleted, so an old backup brings neither back
    b = WardAdapter(_device_b(session), wardd)
    assert b.import_cache(backup) == {"imported": 0, "skipped": 2}
    synced = b.sync()
    assert synced["counter"] == 4 and synced["root"] == ""
    assert synced["cache"] == {"checked": 0, "unchanged": 0, "updated": 0, "removed": 0}
