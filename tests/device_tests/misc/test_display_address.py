import pytest

from trezorlib import messages, ward
from trezorlib.authdb_tree import WARDTree
from trezorlib.debuglink import DebugSession as Session

from ...device_handler import BackgroundDeviceHandler
from ...ward_mgr_emu import sign_ward_update, sign_wm_attestation

pytestmark = [pytest.mark.models("core")]


def _sync_device(
    session: Session,
    counter: int,
    root: bytes | None,
    root_mac: bytes | None,
) -> tuple[int, bytes | None, bytes | None]:
    nonce = ward.sync(session)
    _pending, wallet_id = ward.list_pending(session)
    assert wallet_id is not None
    mac_for_sig = root_mac if root_mac is not None else ward.ZERO_MAC
    sig = sign_wm_attestation(nonce, counter, mac_for_sig, wallet_id)
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
    root = None if tree.is_empty() else tree.get_root_hash()
    counter, _root, root_mac = _sync_device(session, counter, root, root_mac)

    address_bytes = address.encode()
    old_counter = tree.get_counter(address_bytes)
    if old_counter:
        old_value = tree.get_value(address_bytes)
        proof = tree.get_proof(address_bytes)
        witness_address = witness_value = None
        witness_counter = None
    else:
        old_value = b""
        proof, witness_address, witness_counter, witness_value = (
            tree.get_nonmembership_proof(address_bytes)
        )

    new_counter = counter + 1
    ward.add_pending(
        session,
        address=address_bytes,
        old_value=old_value,
        new_value=value,
        new_counter=new_counter,
        proof=proof,
        old_counter=old_counter or None,
        witness_address=witness_address,
        witness_value=witness_value,
        witness_counter=witness_counter,
    )
    c_counter, _root_t, mac_t, wallet_id = ward.commit(session)
    assert wallet_id is not None
    mac_for_sig = mac_t if mac_t is not None else ward.ZERO_MAC
    sig = sign_ward_update(c_counter, mac_for_sig, wallet_id)
    counter, new_root, _wallet_id, root_mac = ward.confirm_commit(
        session, c_counter, mac_t, sig
    )

    tree.insert(address_bytes, value, counter=new_counter)
    assert new_root == tree.get_root_hash()
    return counter, root_mac


def test_display_wrong_address_more_labels(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    tree.insert(other_address.encode(), other_value, counter=1)
    proof = tree.get_proof(other_address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(
                        address=address,
                        ward_value=value,
                        ward_proof=proof,
                        ward_counter=1,
                    ),
                    expect=messages.Success,
                ),
            )
            layout = dev.debuglink().read_layout()
            assert layout.title().splitlines()[0].lower() == "unknown"
            # assert "label1" in layout.title().lower() or layout.subtitle() == "label1"
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
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    tree.insert(other_address.encode(), other_value, counter=1)
    proof = tree.get_proof(address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(
                        address=address,
                        ward_value=value,
                        ward_proof=proof,
                        ward_counter=1,
                    ),
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
    tree = WARDTree()
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

    proof = tree.get_proof(address.encode())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(
                        address=address,
                        ward_value=value,
                        ward_proof=proof,
                        ward_counter=1,
                    ),
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
    tree = WARDTree()
    counter = 0
    root_mac = None

    # First write is an INSERT: the leaf is stamped with counter 1.
    counter, root_mac = _add_value_via_device(
        session, tree, address, value, counter, root_mac
    )
    assert tree.get_counter(address.encode()) == 1

    # Second write to the same address is an UPDATE: the leaf counter increments.
    counter, root_mac = _add_value_via_device(
        session, tree, address, updated_value, counter, root_mac
    )
    assert counter == 2
    assert tree.get_counter(address.encode()) == 2

    # The device's authenticated root binds the leaf at the INCREMENTED counter:
    # a membership lookup with counter=2 verifies, while the stale counter=1 does
    # not. (_add_value_via_device already asserts new_root == tree root, so the
    # device recomputed the root using the bumped leaf counter.)
    proof = tree.get_proof(address.encode())
    valid, membership, current, _wallet_id = ward.lookup(
        session, address.encode(), updated_value, proof, counter=2
    )
    assert valid and membership
    assert current == 2

    stale_valid, _membership, _current, _wallet_id = ward.lookup(
        session, address.encode(), updated_value, proof, counter=1
    )
    assert not stale_valid


def test_display_address_single_label(session: Session) -> None:
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    proof = tree.get_proof(address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(
                        address=address,
                        ward_value=value,
                        ward_proof=proof,
                        ward_counter=1,
                    ),
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
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    tree.insert(other_address.encode(), other_value, counter=1)
    wrong_proof = tree.get_proof(other_address.encode())
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(
                        address=address,
                        ward_value=value,
                        ward_proof=wrong_proof,
                        ward_counter=1,
                    ),
                    expect=messages.Success,
                ),
            )
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
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    tree.insert(other_address.encode(), other_value, counter=1)
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(address=address),
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
    carries witness_address/witness_value/witness_counter."""
    address = "bc1qdemoaddress000000000000000000000000000"
    other_address = "bc1qotheraddress000000000000000000000000000"
    missing_address = "bc1qlabel3000000000000000000000000000000000"
    value = b'TEST:1:{"label":"label1"}'
    other_value = b'TEST:1:{"label":"label2"}'
    tree = WARDTree()
    tree.insert(address.encode(), value, counter=1)
    tree.insert(other_address.encode(), other_value, counter=1)
    ward.debug_set_root(session, tree.get_root_hash())

    with session.test_ctx as client:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)
        with BackgroundDeviceHandler(client) as dev:
            dev.run_with_provided_session(
                session,
                lambda s: s.call(
                    messages.DisplayAddress(address=missing_address),
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

