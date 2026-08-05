import pytest

from trezorlib import messages, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session

from ...device_handler import BackgroundDeviceHandler
from ...ward_mgr_emu import device_ward_keys, sign_ward_update, sign_wm_attestation

_APP = "bitcoin"  # capability principal == queried domain for these tests

pytestmark = [pytest.mark.models("core")]

# Host tree keyed by the device's WARD keys (reproduced from the known test seed)
# so its entry_keys/leaf commits match the device's and its proofs verify.
_K_INDEX, _K_DATA = device_ward_keys()


def _tree() -> WARDTree:
    return WARDTree(_K_INDEX, _K_DATA)


def _apply_device_leaf(tree: WARDTree, perform_result: tuple) -> None:
    """Store the device-returned leaf blob (random nonce) so the host tree tracks the
    device's authenticated root. perform_result[5:10] = (entry_key, entry_type,
    nonce, tag, ct); empty ct = DELETE."""
    ek, entry_type, nonce, tag, ct = perform_result[5:10]
    if ct:
        tree.set_leaf(ek, nonce, tag, ct, entry_type or "address")
    elif ek is not None:
        tree.del_leaf(ek)


def _with_proof(
    tree: WARDTree, address: str, proof: list
) -> "messages.DisplayAddressWithProof":
    """Build a PUSH DisplayAddressWithProof carrying the membership leaf blob
    (nonce/tag/ct/entry_type) for `address` and the given `proof` (which may be a
    deliberately wrong proof in negative tests)."""
    b = tree.leaf_blob(_APP, address.encode())
    assert b is not None, f"{address} not in tree"
    return messages.DisplayAddressWithProof(
        app_id=_APP,
        address=address,
        entry_type=b[3],
        nonce=b[0],
        tag=b[1],
        ct=b[2],
        proof=proof,
    )


def _lookup_membership(session: Session, tree: WARDTree, address: str):
    """Membership WARDLookup with the new signature (leaf blob + proof)."""
    b = tree.leaf_blob(_APP, address.encode())
    assert b is not None, f"{address} not in tree"
    return ward.lookup(
        session,
        _APP,
        address.encode(),
        tree.get_proof(_APP, address.encode()),
        nonce=b[0],
        tag=b[1],
        ct=b[2],
    )


def _sync_device(
    session: Session,
    counter: int,
    root: bytes | None,
    root_mac: bytes | None,
) -> tuple[int, bytes | None, bytes | None]:
    nonce, ward_id = ward.sync(session)
    assert ward_id is not None
    mac_for_sig = root_mac if root_mac is not None else ward.ZERO_MAC
    sig = sign_wm_attestation(nonce, counter, mac_for_sig, ward_id)
    ward.ingest_attestation(session, counter, root_mac, sig)
    return ward.reconcile(session, root)


def _add_value_via_device(
    session: Session,
    tree: WARDTree,
    address: str,
    value: bytes,
    counter: int,
    root_mac: bytes | None,
) -> tuple[int, bytes | None]:
    """Drive one edit through the PULL update round:
    queue_update (trusted confirm) -> perform_update (device pulls the proof from
    the host WARDTree via ward_proof_callback) -> confirmed_by_wm.
    """
    root = None if tree.is_empty() else tree.get_root_hash()
    counter, _root, root_mac = _sync_device(session, counter, root, root_mac)

    address_bytes = address.encode()
    old_counter = tree.get_counter(_APP, address_bytes)
    old_value = tree.get_value(_APP, address_bytes) if old_counter else b""

    with session.test_ctx as client:
        # perform_update pulls the proof for the *current* tree (before this insert).
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)

        # queue_update shows a trusted old->new confirm screen; approve it.
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: ward.queue_update(s, _APP, address_bytes, old_value, value),
            )
            dev.debuglink().press_yes()
            pending_id, _wallet_id = dev.result()

        # perform_update: the device derives counter_T and emits WARDProofRequest,
        # answered by the registered callback; no user interaction.
        res = ward.perform_update(session, pending_id)
        c_counter, _root_t, mac_t, _wallet_id, ward_id = res[:5]
        assert ward_id is not None
        mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
        sig = sign_ward_update(c_counter, mac_for_sig, ward_id)
        counter, new_root, _wallet_id, root_mac = ward.confirmed_by_wm(
            session, c_counter, mac_t, sig, pending_id
        )

    # Store the device's own encrypted leaf blob so the host root matches.
    _apply_device_leaf(tree, res)
    assert new_root == tree.get_root_hash()
    return counter, root_mac


def test_display_wrong_address_more_labels(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    tree.insert(_APP, address.encode(), value, counter=1)
    tree.insert(_APP, other_address.encode(), other_value, counter=1)
    proof = tree.get_proof(_APP, other_address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    _with_proof(tree, address, proof),
                    expect=messages.Success,
                ),
            )
            # A mismatched proof is rejected: the device first WARNS that the label
            # could not be verified, then shows the address titled "unknown" with no
            # verified label. Acknowledge the warning, then check the address screen.
            warning = dev.debuglink().read_layout()
            assert "could not be verified" in warning.screen_content().lower()
            dev.debuglink().press_yes()

            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "unknown"
            content = layout.screen_content()
            assert address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"

def test_display_address_more_labels(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    tree.insert(_APP, address.encode(), value, counter=1)
    tree.insert(_APP, other_address.encode(), other_value, counter=1)
    proof = tree.get_proof(_APP, address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    _with_proof(tree, address, proof),
                    expect=messages.Success,
                ),
            )
            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "membership"
            assert "label1" in layout.title().lower() or layout.subtitle() == "label1"
            content = layout.screen_content()
            assert address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"


def test_display_address_more_labels_via_device(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    counter = 0
    root_mac = None

    counter, root_mac = _add_value_via_device(
        session, tree, address, value, counter, root_mac
    )
    counter, root_mac = _add_value_via_device(
        session, tree, other_address, other_value, counter, root_mac
    )
    assert counter == 2
    assert root_mac is not None

    proof = tree.get_proof(_APP, address.encode())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    _with_proof(tree, address, proof),
                    expect=messages.Success,
                ),
            )
            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "membership"
            assert "label1" in layout.title().lower() or layout.subtitle() == "label1"
            content = layout.screen_content()
            assert address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"


def test_add_value_via_device_increments_leaf_counter(session: Session) -> None:
    """Updating an existing WARD entry via the device must bump that leaf's
    counter. The device stamps the changed leaf with new_counter (== global
    counter + 1) and recomputes the root, so a repeated update to the SAME
    address advances its leaf counter 1 -> 2."""
    address = "bc1qdemoaddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    updated_value = b'TEST:1:{"label":"label1-updated"}'
    tree = _tree()
    counter = 0
    root_mac = None

    # First write is an INSERT: the leaf is stamped with counter 1.
    counter, root_mac = _add_value_via_device(
        session, tree, address, value, counter, root_mac
    )
    assert tree.get_counter(_APP, address.encode()) == 1

    # Second write to the same address is an UPDATE: the leaf counter increments.
    counter, root_mac = _add_value_via_device(
        session, tree, address, updated_value, counter, root_mac
    )
    assert counter == 2
    assert tree.get_counter(_APP, address.encode()) == 2

    # The device's authenticated root binds the current leaf: a membership lookup
    # of the stored blob verifies at the global counter 2. (C_leaf now lives inside
    # the encrypted ct, so `tree.get_counter` above already decrypted it to 2; there
    # is no separate stale-counter wire field to probe.)
    valid, membership, current, _wallet_id = _lookup_membership(session, tree, address)
    assert valid and membership
    assert current == 2


def test_display_address_single_label(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    tree.insert(_APP, address.encode(), value, counter=1)
    proof = tree.get_proof(_APP, address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    _with_proof(tree, address, proof),
                    expect=messages.Success,
                ),
            )
            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "membership"
            assert "label1" in layout.title().lower() or layout.subtitle() == "label1"
            content = layout.screen_content()
            assert address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"




def test_display_address_unknown_with_wrong_proof(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    tree.insert(_APP, address.encode(), value, counter=1)
    tree.insert(_APP, other_address.encode(), other_value, counter=1)
    wrong_proof = tree.get_proof(_APP, other_address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    _with_proof(tree, address, wrong_proof),
                    expect=messages.Success,
                ),
            )
            # A mismatched proof is rejected: the device first WARNS that the label
            # could not be verified, then shows the address titled "unknown" with no
            # verified label. Acknowledge the warning, then check the address screen.
            warning = dev.debuglink().read_layout()
            assert "could not be verified" in warning.screen_content().lower()
            dev.debuglink().press_yes()

            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "unknown"
            content = layout.screen_content()
            assert address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"


# ---------------------------------------------------------------------------
# PULL model: the host omits the proof from DisplayAddress and instead answers a
# WARDProofRequest the device emits on demand. The device pulls the entry from
# the host's WARDTree via the registered ward_proof_callback.
# ---------------------------------------------------------------------------


def test_display_address_more_labels_pull(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    tree.insert(_APP, address.encode(), value, counter=1)
    tree.insert(_APP, other_address.encode(), other_value, counter=1)
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(address=address, app_id=_APP),
                    expect=messages.Success,
                ),
            )
            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "membership"
            assert "label1" in layout.title().lower() or layout.subtitle() == "label1"
            content = layout.screen_content()
            assert address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"


def test_display_address_non_membership_pull(session: Session) -> None:
    """Non-membership on a non-empty tree — impossible in the PUSH model (the
    message has no witness fields) but expressible via PULL, since WARDProofAck
    carries witness_entry_key/witness_commit."""
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    missing_address = "bc1qlabel3000000000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = _tree()
    tree.insert(_APP, address.encode(), value, counter=1)
    tree.insert(_APP, other_address.encode(), other_value, counter=1)
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(address=missing_address, app_id=_APP),
                    expect=messages.Success,
                ),
            )
            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "non-membership"
            content = layout.screen_content()
            assert missing_address in content.replace("\n", "").replace(" ", "")
            dev.debuglink().press_yes()
            response = dev.result()

    assert response.message == "Address shown"

