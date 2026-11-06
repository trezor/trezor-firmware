"""Device tests for the verified on-device WARD listing (WARDListEntries).

The device walks its trusted root top-down, pulling every node from the host
(WARDNodeRequest, answered by ward.tree_node_callback) and accepting it only if it
hashes to what its parent committed to. Matching entries are decrypted and shown one
per screen; the host gets back counts only.
"""

import pytest

from trezorlib import messages, ward, ward_crypto
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure
from trezorlib.testing.device_handler import BackgroundDeviceHandler

from ...ward_mgr_emu import WMEmulator, device_ward_keys, wm_initial_sync

pytestmark = pytest.mark.models("core")

_K_PATH, _K_DATA, _K_IDENT = device_ward_keys()

ENTRIES = [
    ("bitcoin", b"bc1qalice", b"Alice"),
    ("bitcoin", b"bc1qbob", b"Bob"),
    ("bitcoin", b"bc1qcarol", b"Carol"),
    ("ethereum", b"0xdave", b"Dave"),
]


def _tree() -> WARDTree:
    tree = WARDTree(_K_PATH, _K_DATA, _K_IDENT)
    for app_id, identifier, value in ENTRIES:
        tree.insert(app_id, identifier, value, counter=1)
    return tree


def _list(
    session: Session, callback, screens: int, approve: int | None = None, **filters
) -> tuple[messages.WARDListEntriesAck, list[str]]:
    """Run WARDListEntries, reading `screens` entry screens. Each is approved, except
    that the one at index `approve` (if given) is declined to stop the listing.
    Returns the ack and each screen's text, whitespace folded."""
    seen = []
    with session.test_ctx as client:
        client.app.ward_node_callback = callback
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session, lambda s: ward.list_entries(s, **filters)
            )
            for index in range(screens):
                layout = dev.debuglink().read_layout()
                seen.append(
                    " ".join((layout.title() + " " + layout.screen_content()).split())
                )
                if index == approve:
                    dev.debuglink().press_no()
                else:
                    dev.debuglink().press_yes()
            ack = dev.result()
    return ack, seen


def test_ward_list_shows_every_entry(session: Session) -> None:
    tree = _tree()
    counter, _r, _w, _m = ward.debug_set_root(session, tree.get_root_hash())

    ack, seen = _list(session, ward.tree_node_callback(tree), len(ENTRIES))

    assert (ack.shown, ack.entries, ack.counter, ack.complete) == (
        len(ENTRIES),
        len(ENTRIES),
        counter,
        True,
    )
    text = " ".join(seen)
    for _app, identifier, value in ENTRIES:
        assert identifier.decode() in text and value.decode() in text


def test_ward_list_one_node_per_round_trip(session: Session) -> None:
    """The batch size is the host's choice; one node per request walks the same trie."""
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())

    ack, _seen = _list(session, ward.tree_node_callback(tree, max_nodes=1), 4)

    assert (ack.shown, ack.entries, ack.complete) == (4, 4, True)


def test_ward_list_filters_still_verify_every_leaf(session: Session) -> None:
    """A filter narrows what is SHOWN, never what is verified: every leaf is still
    walked, so a matching entry cannot hide behind a skipped one."""
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())

    ack, seen = _list(session, ward.tree_node_callback(tree), 1, app_id="ethereum")

    assert (ack.shown, ack.entries, ack.complete) == (1, 4, True)
    assert "0xdave" in seen[0] and "Dave" in seen[0]


def test_ward_list_user_can_stop(session: Session) -> None:
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())

    ack, _seen = _list(session, ward.tree_node_callback(tree), 2, approve=1)

    assert (ack.shown, ack.complete) == (2, False)


def test_ward_list_empty_tree(session: Session) -> None:
    wm_initial_sync(session, WMEmulator(), WARDTree(_K_PATH, _K_DATA, _K_IDENT), 0)

    def never(_msg):
        raise AssertionError("an empty trie has no node to pull")

    ack, _seen = _list(session, never, 0)

    assert (ack.shown, ack.entries, ack.complete) == (0, 0, True)


@pytest.mark.parametrize("attack", ["substituted_child", "omitted_subtree", "no_nodes"])
def test_ward_list_rejects_a_dishonest_host(session: Session, attack: str) -> None:
    """Whatever the host serves must hash to what the trusted root committed to; a
    substituted or skipped subtree, or a host that stops answering, ends the listing
    with a failure -- never with a quietly shorter list."""
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())
    honest = ward.tree_node_callback(tree)

    def dishonest(msg: messages.WARDNodeRequest) -> messages.WARDNodeAck:
        ack = honest(msg)
        if msg.node_hash != tree.get_root_hash():
            return ack
        if attack == "no_nodes":
            return messages.WARDNodeAck(nodes=[])
        root = ack.nodes[0]
        if attack == "substituted_child":
            root.left = b"\x42" * 32
        else:  # claim the root is its own left subtree's first leaf
            ack.nodes = [n for n in ack.nodes if n.entry_key is not None][:1]
        return ack

    with session.test_ctx as client:
        client.app.ward_node_callback = dishonest
        with pytest.raises(TrezorFailure, match="WARD listing"):
            ward.list_entries(session)


def test_ward_list_rejects_identity_that_does_not_match_its_path(
    session: Session,
) -> None:
    """The walk proves a leaf is in the trie; the screen names it by its identity.
    A leaf whose (validly sealed) identity is another entry's must not be shown as
    that entry."""
    tree = _tree()
    app_id, identifier, _value = ENTRIES[0]
    ek = tree._ek(app_id, identifier, "address", 0)
    tree.set_leaf(
        ek,
        ward_crypto.encode_leaf(
            _K_IDENT, _K_DATA, ek, "address", 1, b"bc1qmallory", app_id, b"Mallory", 0
        ),
    )
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        client.app.ward_node_callback = ward.tree_node_callback(tree)
        with pytest.raises(TrezorFailure, match="does not match its path"):
            ward.list_entries(session)
