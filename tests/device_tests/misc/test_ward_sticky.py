"""Sticky offline-cache entries.

STICKY is a device-only decision the user confirms on screen; it never enters the
leaf. A sticky entry may be used while NO proof can be had (the host answers
`unavailable`, i.e. no wardd), shown marked "cached". Every verified answer still updates
the cached copy, or removes it when WARD proves the entry absent -- sticky or not -- and
the device's own committed writes update its cache directly.

Across two devices of one wallet: A caches entries (one sticky) and backs them up.
Device B (the same emulator, wiped and loaded with the same seed) syncs, imports the
backup -- every entry checked against WARD by a proof B pulls -- follows A's later
deletes and changes through a chain sync, and validates its cache. Needs the offline
store (xtask --ward); skipped otherwise.
"""

import copy

import pytest

from trezorlib import debuglink, messages, ward
from trezorlib.debuglink import DebugSession as Session
from trezorlib.debuglink import LayoutType
from trezorlib.exceptions import Cancelled, TrezorFailure
from trezorlib.testing.device_handler import BackgroundDeviceHandler

from ...ward_mgr_emu import (
    DEFAULT_MNEMONIC,
    WMEmulator,
    wm_chain_sync,
    wm_initial_sync,
)
from .test_ward import _APP, _perform_and_finalize, _queue_update, _tree

pytestmark = pytest.mark.models("core")

STICKY = b"bc1qsticky"  # sticky; deleted from WARD on A
GONE = b"bc1qgone"  # non-sticky; deleted from WARD on A
CHANGED = b"bc1qchanged"  # non-sticky; its value changes in WARD on A
KEPT = b"bc1qkept"  # non-sticky; unchanged
ENTRIES = {STICKY: b"sticky", GONE: b"gone", CHANGED: b"old", KEPT: b"kept"}


def _ek(tree, address: bytes) -> bytes:
    return tree._ek(_APP, address, "address", 0)


def _confirmed(session: Session, fn, approve: bool = True):
    """Run `fn` and answer its one confirmation screen."""
    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(session, fn)
            if approve:
                dev.debuglink().press_yes()
            else:
                dev.debuglink().press_no()
            return dev.result()


def _cache_sticky(session: Session, entry_key: bytes, approve: bool = True):
    try:
        return _confirmed(
            session, lambda s: ward.cache_entry(s, entry_key, sticky=True), approve
        )
    except TrezorFailure as e:
        if "this firmware has no offline store" in str(e):
            pytest.skip("firmware built without the WARD offline store (xtask --ward)")
        raise


def _device_b(session: Session) -> Session:
    """Another device of the same wallet: this emulator wiped and loaded with the
    same seed, so its storage (cache, anchors) starts empty."""
    test_ctx = session.test_ctx
    test_ctx.wipe_device()
    seedless = test_ctx.get_seedless_session()
    seedless.refresh_features()
    debuglink.load_device(
        seedless,
        mnemonic=DEFAULT_MNEMONIC,
        pin=None,
        passphrase_protection=False,
        label="device B",
    )
    return test_ctx.get_session()


def _serving(session: Session, tree, pulled: list):
    """Serve proofs from `tree`, recording which entry each pull was for and whether
    it was answered with a leaf (membership)."""
    honest = ward.tree_proof_callback(tree)

    def callback(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        ack = honest(msg)
        pulled.append((msg.entry_key, ack.content is not None))
        return ack

    session.client.app.ward_proof_callback = callback


_STATUSES = ("membership", "non-membership", "cached", "unverified", "unknown")


def _label_screens(session: Session, address: bytes, callback) -> list[str]:
    """DisplayAddress for `address`, answered by `callback` (None: no WARD host, so
    trezorlib answers the proof request `unavailable`). Approves every screen up to
    and including the address; returns each screen's title + content, lowercased."""
    seen = []
    with session.test_ctx as client:
        client.app.ward_proof_callback = callback
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(address=address.decode(), app_id=_APP),
                    expect=messages.Success,
                ),
            )
            for _screen in range(4):
                layout = dev.debuglink().read_layout()
                title = layout.title().lower()
                text = title + " " + layout.screen_content()
                # Smaller screens split a long one into pages (e.g. the four
                # properties of a changed offline entry on Delizia): read them all.
                for _page in range(layout.page_count() - 1):
                    if dev.debuglink().layout_type is LayoutType.Caesar:
                        dev.debuglink().press_right()
                    else:
                        dev.debuglink().swipe_up()
                    text += " " + dev.debuglink().read_layout().screen_content()
                seen.append(" ".join(text.lower().split()))
                dev.debuglink().press_yes()
                # the address screen is titled with the lookup's status; a warning
                # before it may name the address too
                if title.split()[0] in _STATUSES:
                    break
            dev.result()
    return seen


def _label_screen(session: Session, address: bytes, callback) -> str:
    """The address screen alone, for lookups that raise no other screen."""
    seen = _label_screens(session, address, callback)
    assert len(seen) == 1, seen
    return seen[0]


def test_ward_cache_follows_ward_across_devices(session: Session):
    # --- device A: WARD holds four entries; cache them, one sticky (confirmed) ----
    tree = _tree()
    for address, value in ENTRIES.items():
        tree.insert(_APP, address, value, counter=1)
    counter0, _r, _w, _m = ward.debug_set_root(session, tree.get_root_hash())
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    _cache_sticky(session, _ek(tree, STICKY))
    for address in (GONE, CHANGED, KEPT):
        assert ward.cache_entry(session, _ek(tree, address)).replaced is False

    backup = ward.export_cache(session)
    assert len(backup) == 4
    for blob in backup:
        for value in ENTRIES.values():
            assert value not in blob

    # --- device B: sync, then load the backup, checked against WARD --------------
    b = _device_b(session)
    wm = WMEmulator()
    wm_initial_sync(b, wm, tree, counter0)

    tampered = bytes([backup[0][0] ^ 1]) + backup[0][1:]
    with pytest.raises(TrezorFailure, match="not sealed by this wallet"):
        ward.import_cache(b, [tampered])

    b.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    # one entry becomes sticky on B: the user confirms the import
    loaded = _confirmed(b, lambda s: ward.import_cache(s, backup))
    assert (loaded.imported, loaded.skipped) == (4, 0)

    # --- A deletes two entries and changes one; B follows through the chain ------
    before = copy.deepcopy(tree)
    tree.delete(_APP, STICKY)
    tree.delete(_APP, GONE)
    tree.insert(_APP, CHANGED, b"new", counter=counter0 + 1)
    counter1, root, _mac = wm_chain_sync(b, wm, before, counter0, tree, counter0 + 1)
    assert (counter1, root) == (counter0 + 1, tree.get_root_hash())

    pulled = []
    _serving(b, tree, pulled)
    # the sticky copy WARD deleted is removed -- and the user is told first
    report = _confirmed(b, lambda s: ward.validate_cache(s))
    assert (report.checked, report.unchanged, report.updated, report.removed) == (
        4,
        1,
        1,
        2,
    )
    assert report.counter == counter1
    # one verified proof per entry: absence (a witness) for the two WARD deleted,
    # sticky or not
    assert dict(pulled) == {
        _ek(tree, STICKY): False,
        _ek(tree, GONE): False,
        _ek(tree, CHANGED): True,
        _ek(tree, KEPT): True,
    }

    # --- replaying the old backup cannot bring the deleted entries back ----------
    replay = ward.import_cache(b, backup)
    assert (replay.imported, replay.skipped) == (2, 2)
    again = ward.validate_cache(b)
    assert (again.checked, again.unchanged, again.removed) == (2, 2, 0)


def test_ward_sticky_needs_the_users_approval(session: Session):
    tree = _tree()
    tree.insert(_APP, STICKY, b"sticky label", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)

    with pytest.raises(Cancelled):
        _cache_sticky(session, _ek(tree, STICKY), approve=False)
    # nothing was stored, so nothing is shown without a host
    assert _label_screen(session, STICKY, None).startswith("unverified")

    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    _cache_sticky(session, _ek(tree, STICKY))
    assert _label_screen(session, STICKY, None).startswith("cached")


def test_ward_sticky_entry_is_used_only_while_no_proof_can_be_had(session: Session):
    tree = _tree()
    tree.insert(_APP, STICKY, b"sticky label", counter=1)
    tree.insert(_APP, KEPT, b"plain label", counter=1)
    counter, _r, _w, _m = ward.debug_set_root(session, tree.get_root_hash())
    honest = ward.tree_proof_callback(tree)
    session.client.app.ward_proof_callback = honest
    _cache_sticky(session, _ek(tree, STICKY))
    ward.cache_entry(session, _ek(tree, KEPT))

    # no wardd: the sticky entry is shown from the cache, marked cached; a non-sticky
    # cached entry is not used without a proof
    offline = _label_screen(session, STICKY, None)
    assert offline.startswith("cached") and "sticky label" in offline
    offline_plain = _label_screen(session, KEPT, None)
    assert offline_plain.startswith("unverified") and "plain label" not in offline_plain

    # wardd available: the proven label, and the sticky copy stays
    assert _label_screen(session, STICKY, honest).startswith("membership")
    assert _label_screen(session, STICKY, None).startswith("cached")

    # ANOTHER device changes it in WARD: the next proven lookup tells the user the
    # offline copy differs, shows WARD's label, and the copy follows WARD
    wm = WMEmulator()
    before = copy.deepcopy(tree)
    tree.insert(_APP, STICKY, b"new label", counter=counter + 1)
    wm_chain_sync(session, wm, before, counter, tree, counter + 1)
    honest = ward.tree_proof_callback(tree)
    changed = _label_screens(session, STICKY, honest)
    assert len(changed) == 2
    assert "offline entry changed" in changed[0]
    assert "sticky label" in changed[0] and "new label" in changed[0]
    assert changed[1].startswith("membership") and "new label" in changed[1]
    assert "new label" in _label_screen(session, STICKY, None)

    # ... and deletes it: the user is told, and the sticky copy is removed too
    before = copy.deepcopy(tree)
    tree.delete(_APP, STICKY)
    wm_chain_sync(session, wm, before, counter + 1, tree, counter + 2)
    honest = ward.tree_proof_callback(tree)
    removed = _label_screens(session, STICKY, honest)
    assert len(removed) == 2
    assert "offline entry removed" in removed[0] and "new label" in removed[0]
    assert removed[1].startswith("non-membership")
    gone = _label_screen(session, STICKY, None)
    assert gone.startswith("unverified") and "label" not in gone


def test_ward_own_writes_update_the_cache_at_once(session: Session):
    """This device's own approved update and delete reach its cached copy when they
    are committed -- not only after a host serves a proof."""
    tree = _tree()
    tree.insert(_APP, STICKY, b"before", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    _cache_sticky(session, _ek(tree, STICKY))

    pid = _queue_update(session, STICKY, b"before", b"after")
    _perform_and_finalize(session, tree, pid)
    updated = _label_screen(session, STICKY, None)
    assert updated.startswith("cached") and "after" in updated

    pid = _queue_update(session, STICKY, b"after", b"", delete=True)
    _perform_and_finalize(session, tree, pid)
    deleted = _label_screen(session, STICKY, None)
    assert deleted.startswith("unverified") and "after" not in deleted


def test_ward_validate_cache_refuses_a_lying_host(session: Session):
    """A host that hides a cached entry (a non-membership answer for an entry WARD
    still has) cannot make the device drop it: the proof of absence does not verify."""
    tree = _tree()
    tree.insert(_APP, KEPT, b"kept", counter=1)
    tree.insert(_APP, GONE, b"gone", counter=1)
    ward.debug_set_root(session, tree.get_root_hash())
    session.client.app.ward_proof_callback = ward.tree_proof_callback(tree)
    try:
        ward.cache_entry(session, _ek(tree, KEPT))
    except TrezorFailure as e:
        if "this firmware has no offline store" in str(e):
            pytest.skip("firmware built without the WARD offline store (xtask --ward)")
        raise

    honest = ward.tree_proof_callback(tree)
    without_kept = _tree()
    without_kept.insert(_APP, GONE, b"gone", counter=1)
    liar = ward.tree_proof_callback(without_kept)

    def hiding(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        return liar(msg) if msg.entry_key == _ek(tree, KEPT) else honest(msg)

    session.client.app.ward_proof_callback = hiding
    with pytest.raises(TrezorFailure, match="does not verify"):
        ward.validate_cache(session)

    session.client.app.ward_proof_callback = honest
    report = ward.validate_cache(session)
    assert (report.checked, report.unchanged, report.removed) == (1, 1, 0)
