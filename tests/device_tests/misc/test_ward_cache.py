"""Device tests for copying a trie entry into the offline cache (WARDCacheEntry).

The host names the entry by its entry_key; the device pulls the proof
(WARDProofRequest, answered by ward.tree_proof_callback), requires membership under
its trusted root, checks the identity is entry_key's preimage, and stores the entry in
the WARD store of the app the entry's domain belongs to. Only `replaced` comes back.
Needs a firmware built with the offline store (xtask --ward); skipped otherwise.
"""

import pytest

from trezorlib import messages, ward, ward_crypto
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session
from trezorlib.exceptions import TrezorFailure

from ...ward_mgr_emu import device_ward_keys

pytestmark = pytest.mark.models("core")

_K_PATH, _K_DATA, _K_IDENT = device_ward_keys()
_APP = "bitcoin"


def _tree() -> WARDTree:
    tree = WARDTree(_K_PATH, _K_DATA, _K_IDENT)
    tree.insert(_APP, b"bc1qcache1", b"label one", counter=1)
    tree.insert(_APP, b"bc1qcache2", b"label two", counter=1)
    tree.insert("ethereum", b"0xcache", b"eth label", counter=1)
    return tree


def _cache(session: Session, tree: WARDTree, entry_key: bytes, callback=None):
    session.client.app.ward_proof_callback = callback or ward.tree_proof_callback(tree)
    try:
        return ward.cache_entry(session, entry_key)
    except TrezorFailure as e:
        if "no offline store" in str(e) and "domain" not in str(e):
            pytest.skip("firmware built without the WARD offline store (xtask --ward)")
        raise


def test_ward_cache_entry_stores_and_replaces(session: Session) -> None:
    tree = _tree()
    counter, _r, _w, _m = ward.debug_set_root(session, tree.get_root_hash())
    ek = tree._ek(_APP, b"bc1qcache1", "address", 0)

    first = _cache(session, tree, ek)
    again = _cache(session, tree, ek)

    assert (first.replaced, first.counter) == (False, counter)
    assert again.replaced is True
    # another entry is its own record
    other = tree._ek(_APP, b"bc1qcache2", "address", 0)
    assert _cache(session, tree, other).replaced is False


def test_ward_cache_entry_refuses_an_absent_entry(session: Session) -> None:
    """A non-membership answer stores nothing: only entries in the trie are cached."""
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())
    absent = tree._ek(_APP, b"bc1qnotthere", "address", 0)

    with pytest.raises(TrezorFailure, match="not in the trie"):
        _cache(session, tree, absent)


def test_ward_cache_entry_refuses_a_forged_proof(session: Session) -> None:
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())
    ek = tree._ek(_APP, b"bc1qcache1", "address", 0)
    honest = ward.tree_proof_callback(tree)

    def forged(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        ack = honest(msg)
        ack.proof[0] = ack.proof[0][:2] + bytes(32)
        return ack

    with pytest.raises(TrezorFailure, match="does not verify"):
        _cache(session, tree, ek, forged)


def test_ward_cache_entry_refuses_a_domain_without_a_store(session: Session) -> None:
    tree = _tree()
    ward.debug_set_root(session, tree.get_root_hash())

    with pytest.raises(TrezorFailure, match="no offline store for this domain"):
        _cache(session, tree, tree._ek("ethereum", b"0xcache", "address", 0))


def test_ward_cache_entry_refuses_identity_that_does_not_match_its_path(
    session: Session,
) -> None:
    """A leaf proven in the trie, whose sealed identity names another entry, is not
    filed under that other entry's identifier."""
    tree = _tree()
    ek = tree._ek(_APP, b"bc1qcache1", "address", 0)
    tree.set_leaf(
        ek,
        ward_crypto.encode_leaf(
            _K_IDENT, _K_DATA, ek, "address", 1, b"bc1qmallory", _APP, b"Mallory", 0
        ),
    )
    ward.debug_set_root(session, tree.get_root_hash())

    with pytest.raises(TrezorFailure, match="does not match its path"):
        _cache(session, tree, ek)
