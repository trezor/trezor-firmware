from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Optional

from . import messages

if TYPE_CHECKING:
    from .authdb_tree import WARDTree
    from .transport.session import Session

ZERO_MAC = b"\x00" * 32

# NOTE: the WM (WARD Manager) signing helpers and the debug WM key are NOT here.
# They are the WARD Manager's role (an external freshness authority), not a
# device-client operation, and they forge signatures with a debug-only key. They
# live in the test harness at tests/ward_mgr_emu.py so this production client
# library ships no debug-only signing.


# ---------------------------------------------------------------------------
# Wire wrappers — the WARD update round (add_pending -> commit -> finalize)
# ---------------------------------------------------------------------------


def queue_update(
    session: "Session",
    app_id: str,
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    key_type: str = "address",
    device_id: int = 0,
    delete: bool = False,
) -> Optional[int]:
    """Queue an edit INTENT (pull model). Carries NO proof.

    old_value=b"" means the address is currently absent (INSERT); new_value=b""
    means delete (DELETE); old_value is a display hint only. The device shows the
    old -> new change on a trusted screen and, only on user approval, returns a
    pending_id. Under the strict model NO candidate counter is derived here; the
    counter and candidate root are computed later, at perform_update, from a proof
    the device pulls itself. Returns pending_id.
    """
    # old_value is a display hint only and is not carried on the wire (the diagram's
    # WARDQueueUpdate is address + new_value); the device pulls the current state at
    # perform time.
    del old_value
    resp = session.call(
        messages.WARDQueueUpdate(
            app_id=app_id,
            address=address,
            new_value=new_value,
            key_type=key_type,
            device_id=device_id,
            delete=delete,
        ),
        expect=messages.WARDQueueUpdateAck,
    )
    return resp.pending_id


def perform_update(
    session: "Session",
    pending_id: Optional[int] = None,
) -> tuple:
    """Authorize a queued intent. The device PULLS the proof it needs mid-call:
    it emits a WARDProofRequest, which the client answers via the registered
    ``ward_proof_callback`` (e.g. ``tree_proof_callback(tree)``) -- so a callback
    MUST be registered before calling this. This is where the device first derives
    counter_T (strict model). pending_id selects the intent; if omitted, the device
    targets the single queued one.

    The device is the encoder, so it also returns the new leaf it produced — the host
    cannot compute a sealed leaf and must store it keyed by entry_key (an empty content
    part => DELETE; the identity part survives it). Returns
    (counter_T, root_T, mac_T, ward_id, entry_key, LeafBlob); root_T/mac_T
    are None if the candidate empties the tree.
    """
    from .ward_crypto import EMPTY_PART, LeafBlob

    resp = session.call(
        messages.WARDPerformUpdate(pending_id=pending_id),
        expect=messages.WARDPerformUpdateAck,
    )
    key_type, id_part = read_leaf_identity(resp.identity)
    val_part = read_leaf_content(resp.content)
    leaf = LeafBlob(
        key_type or "address", id_part or EMPTY_PART, val_part or EMPTY_PART
    )
    return (
        resp.counter,
        resp.new_root,
        resp.mac,
        resp.ward_id,
        resp.entry_key,
        leaf,
    )


def confirmed_by_wm(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    wm_signature: bytes,
    pending_id: Optional[int] = None,
) -> tuple[int, Optional[bytes], Optional[bytes]]:
    """Install a committed candidate with the WM's Ed25519 signature over the exact
    device-derived (counter_T, mac_T). pending_id selects it; if omitted, the
    device targets the single queued candidate.

    Advances the device counter and drops that candidate. Returns
    (counter, new_root, root_mac).
    """
    resp = session.call(
        messages.WARDConfirmedByWM(
            counter=counter, mac=mac, wm_signature=wm_signature, pending_id=pending_id
        ),
        expect=messages.WARDConfirmedByWMAck,
    )
    return resp.counter, resp.new_root, resp.root_mac


def perform_batch(session: "Session", pending_ids: list) -> tuple:
    """Authorize N queued intents as ONE root transition (batch-update). The device
    PULLS one proof per intent (WARDProofRequest per entry_key), answered by the
    registered ``ward_proof_callback`` — so a callback MUST be registered first. The
    whole batch advances the counter by 1. Returns (counter, from_root, new_root, mac,
    ward_id, head_mac, auth_commit, sig_commit, leaves) where `leaves` is a list of
    (entry_key, LeafBlob) the host stores keyed by entry_key (an empty content part
    => DELETE)."""
    from .ward_crypto import EMPTY_PART, LeafBlob

    resp = session.call(
        messages.WARDPerformBatch(pending_ids=pending_ids),
        expect=messages.WARDPerformBatchAck,
    )
    leaves = []
    for lf in resp.leaves:
        kt, id_part = read_leaf_identity(lf.identity)
        val_part = read_leaf_content(lf.content)
        leaves.append(
            (
                lf.entry_key,
                LeafBlob(
                    kt or "address", id_part or EMPTY_PART, val_part or EMPTY_PART
                ),
            )
        )
    return (
        resp.counter,
        resp.from_root,
        resp.new_root,
        resp.mac,
        resp.ward_id,
        resp.head_mac,
        resp.auth_commit,
        resp.sig_commit,
        leaves,
    )


def confirmed_batch_by_wm(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    wm_signature: bytes,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Install a committed batch with the WM's Ed25519 signature over the exact
    device-derived (to_counter, mac_t). Advances the counter by 1 and drops the whole
    pending set. Returns (counter, new_root, ward_id, root_mac)."""
    resp = session.call(
        messages.WARDConfirmBatchByWM(
            counter=counter, mac=mac, wm_signature=wm_signature
        ),
        expect=messages.WARDConfirmBatchByWMAck,
    )
    return resp.counter, resp.new_root, resp.ward_id, resp.root_mac


def perform_revert(
    session: "Session",
    stuck_counter: int,
    stuck_root: Optional[bytes],
    prev_root: Optional[bytes],
    forward_auth_commit: bytes,
) -> tuple:
    """Prepare a constrained one-step rollback (ward-design §8.2). Presents the
    FORWARD AuthCommit that created the current stuck head plus the predecessor root
    it encodes; the device verifies that MAC to prove the predecessor and demotes with
    a FORWARD-incrementing counter (to_counter = stuck_counter + 1). Returns (counter,
    from_root, new_root, mac, ward_id, head_mac, auth_revert, sig_commit)."""
    resp = session.call(
        messages.WARDPerformRevert(
            stuck_counter=stuck_counter,
            stuck_root=stuck_root,
            prev_root=prev_root,
            forward_auth_commit=forward_auth_commit,
        ),
        expect=messages.WARDPerformRevertAck,
    )
    return (
        resp.counter,
        resp.from_root,
        resp.new_root,
        resp.mac,
        resp.ward_id,
        resp.head_mac,
        resp.auth_revert,
        resp.sig_commit,
    )


def confirmed_revert_by_wm(
    session: "Session",
    counter: int,
    mac: Optional[bytes],
    wm_signature: bytes,
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Install a one-step rollback with the WM's signature over (to_counter, mac_t).
    Returns (counter, new_root, ward_id, root_mac)."""
    resp = session.call(
        messages.WARDConfirmRevertByWM(
            counter=counter, mac=mac, wm_signature=wm_signature
        ),
        expect=messages.WARDConfirmRevertByWMAck,
    )
    return resp.counter, resp.new_root, resp.ward_id, resp.root_mac


def verify_chain(
    session: "Session", links: list
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """Another-Trezor read-only chain verification + adopt (Phase 4a). Run AFTER
    ingest_attestation (in place of reconcile). `links` is the ordered list of
    transitions from the device's trusted baseline to the WM head, each a tuple
    `(from_counter, from_root, to_counter, to_root, auth_commit, sig_commit|None)`
    (roots in 32-byte MAC-preimage form). The device verifies the AuthCommit chain and
    adopts the head. Returns `(counter, new_root, ward_id, root_mac)`."""
    msg_links = [
        messages.WARDChainLink(
            from_counter=lk[0],
            from_root=lk[1],
            to_counter=lk[2],
            to_root=lk[3],
            auth_commit=lk[4],
            sig_commit=lk[5] if len(lk) > 5 else None,
        )
        for lk in links
    ]
    resp = session.call(
        messages.WARDVerifyChain(links=msg_links),
        expect=messages.WARDVerifyChainAck,
    )
    return resp.counter, resp.new_root, resp.ward_id, resp.root_mac


def discard_pending(
    session: "Session",
    pending_id: Optional[int] = None,
) -> tuple[Optional[bytes], Optional[bytes]]:
    """Abandon queued pending edit(s) without finalizing. With pending_id, drops
    just that candidate; without it, drops EVERY candidate queued for the wallet.
    Returns (discarded_address, wallet_id); discarded_address is None when nothing
    matched (or in drop-all mode)."""
    resp = session.call(
        messages.WARDDiscardPending(pending_id=pending_id),
        expect=messages.WARDDiscardPendingAck,
    )
    return resp.discarded_address, resp.wallet_id


# ---------------------------------------------------------------------------
# Wire wrappers — the WARD sync round + lookup + debug seed
# ---------------------------------------------------------------------------


def sync(session: "Session") -> tuple[bytes, Optional[bytes]]:
    """Start a fresh sync round on the device.

    Returns (nonce, ward_id): the fresh nonce for WM attestation and the
    SLIP21-derived WM-facing ward_id the host forwards to the WM (the WM signs its
    attestation preimage over ward_id, not the local wallet_id).
    """
    resp = session.call(messages.WARDSync(), expect=messages.WARDSyncAck)
    return resp.nonce, resp.ward_id


def ingest_attestation(
    session: "Session",
    counter_ext: int,
    root_mac_ext: Optional[bytes],
    wm_signature: bytes,
    *,
    timestamp: int,
    head_nonce: bytes,
) -> int:
    """Verify and record the WM freshness attestation for the open sync round.

    Returns the accepted external counter.
    """
    resp = session.call(
        messages.WARDIngestAttestation(
            counter=counter_ext,
            mac=root_mac_ext,
            wm_signature=wm_signature,
            timestamp=timestamp,
            head_nonce=head_nonce,
        ),
        expect=messages.WARDIngestAttestationAck,
    )
    return resp.counter


def list_pending(session: "Session") -> tuple[list[bytes], Optional[bytes]]:
    """Return (pending_edit_addresses, wallet_id).

    Note:
    - wallet_id is returned only for current compatibility
    - callers should not rely on list_pending() as the source of wallet_id
    - the intended design is for wallet_id to come from a different host/device source
    """
    resp = session.call(
        messages.WARDListPendingEdits(), expect=messages.WARDListPendingEditsAck
    )
    return list(resp.addresses), resp.wallet_id


def reconcile(
    session: "Session", root: Optional[bytes]
) -> tuple[int, Optional[bytes], Optional[bytes]]:
    """Finalize an already-attested sync round by installing the supplied root.

    Returns (counter, adopted_root, installed_root_mac).
    """
    resp = session.call(
        messages.WARDReconcile(root=root), expect=messages.WARDReconcileAck
    )
    return resp.counter, resp.new_root, resp.root_mac


def lookup(
    session: "Session",
    app_id: str,
    address: bytes,
    proof: list[bytes],
    leaf=None,
    key_type: str = "address",
    device_id: int = 0,
    witness_entry_key: Optional[bytes] = None,
    witness_commit: Optional[bytes] = None,
) -> tuple[bool, bool, int]:
    """PUSH-verify a proof against the device's authenticated root. Returns
    (valid, membership, counter). The device forms
    entry_key = HMAC(K_path, app_id||0x00||key_type||0x00||device_id||address) and,
    for membership, rebuilds the leaf from the ward_crypto.LeafBlob in `leaf`; a
    non-membership witness is two hashes only (witness_entry_key, witness_commit)."""
    resp = session.call(
        messages.WARDLookup(
            app_id=app_id,
            address=address,
            proof=proof,
            content=make_leaf_content(leaf.content if leaf is not None else None),
            identity=(
                make_leaf_identity(leaf.key_type, leaf.identity)
                if leaf is not None
                else None
            ),
            key_type=key_type,
            device_id=device_id,
            witness_entry_key=witness_entry_key,
            witness_commit=witness_commit,
        ),
        expect=messages.WARDLookupAck,
    )
    membership = resp.membership if resp.membership is not None else True
    return resp.valid, membership, resp.counter


def export_keys(
    session: "Session", key_type: str = "address"
) -> tuple[Optional[bytes], Optional[bytes], Optional[str]]:
    """PUSH: retrieve the keys the host needs to drive the push flow itself — K_path
    (resolve identifier -> entry_key), K_ident(key_type) (read identities) and
    K_data(key_type) (read values). Three independent capabilities; K_sig is never
    exported. None of them is needed to *locate* a leaf or serve a proof — the MAC is
    stored with the leaf. The host should keep the returned keys in memory only.
    Returns (k_path, k_data, key_type, k_ident)."""
    resp = session.call(
        messages.WARDExportKeys(key_type=key_type),
        expect=messages.WARDExportKeysAck,
    )
    return resp.k_path, resp.k_data, resp.key_type, resp.k_ident


def debug_set_root(
    session: "Session", root: bytes
) -> tuple[int, Optional[bytes], Optional[bytes], Optional[bytes]]:
    """DEBUG-only unauthenticated root injection (seeds a root in one call).
    Returns (counter, new_root, wallet_id, root_mac). WARDDebugSetRootAck RETAINS
    wallet_id -- connect-cli and the device tests read it."""
    resp = session.call(
        messages.WARDDebugSetRoot(root=root), expect=messages.WARDDebugSetRootAck
    )
    return resp.counter, resp.new_root, resp.wallet_id, resp.root_mac


# ---------------------------------------------------------------------------
# Proof-on-demand: the device pulls a WARD proof mid-workflow via WARDProofRequest.
# ---------------------------------------------------------------------------


def make_leaf_content(part) -> Optional["messages.LeafContent"]:
    """Wrap a ward_crypto.Part in a self-describing LeafContent. Returns None when
    there is no content part at all (a non-membership / pull answer)."""
    from . import ward_crypto

    if part is None:
        return None
    if part.encoding == ward_crypto.ENC_PLAINTEXT:
        return messages.LeafContent(
            encoding=1, plaintext=messages.PlaintextLeaf(content=part.body)
        )
    return messages.LeafContent(
        encoding=0,
        encrypted=messages.EncryptedLeaf(nonce=part.nonce, tag=part.tag, ct=part.body),
    )


def read_leaf_content(content: Optional["messages.LeafContent"]):
    """Read a LeafContent into a ward_crypto.Part (None if absent). The host is
    keyless and carries whatever encoding the device produced."""
    from . import ward_crypto

    if content is None:
        return None
    if (content.encoding or 0) == 1:
        p = content.plaintext
        body = p.content if (p is not None and p.content is not None) else b""
        return ward_crypto.Part(ward_crypto.ENC_PLAINTEXT, b"", b"", body)
    e = content.encrypted
    if e is None:
        return None
    return ward_crypto.Part(
        ward_crypto.ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b""
    )


def make_leaf_identity(key_type: str, part) -> Optional["messages.LeafIdentity"]:
    """Wrap a ward_crypto.Part in a LeafIdentity. `key_type` is always clear -- it
    selects both K_ident and K_data. An empty part yields None: a deleted leaf no
    longer exists, so there is no identity to describe."""
    from . import ward_crypto

    if part is None or part.is_empty():
        return None
    if part.encoding == ward_crypto.ENC_PLAINTEXT:
        identifier, app_id, device_id = ward_crypto.unpack_identity(part.body)
        return messages.LeafIdentity(
            encoding=1,
            key_type=key_type,
            plain=messages.PlainIdentity(
                identifier=identifier, app_id=app_id.decode(), device_id=device_id
            ),
        )
    return messages.LeafIdentity(
        encoding=0,
        key_type=key_type,
        encrypted=messages.EncryptedIdentity(
            nonce=part.nonce, tag=part.tag, ct=part.body
        ),
    )


def read_leaf_identity(identity: Optional["messages.LeafIdentity"]):
    """Read a LeafIdentity into (key_type, Part). (None, None) if absent."""
    from . import ward_crypto

    if identity is None:
        return None, None
    key_type = identity.key_type or "address"
    if (identity.encoding or 0) == 1:
        p = identity.plain
        if p is None:
            return key_type, None
        body = ward_crypto.pack_identity(
            p.identifier or b"", p.app_id or b"", p.device_id or 0
        )
        return key_type, ward_crypto.Part(ward_crypto.ENC_PLAINTEXT, b"", b"", body)
    e = identity.encrypted
    if e is None:
        return key_type, None
    return key_type, ward_crypto.Part(
        ward_crypto.ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b""
    )


def build_proof_ack(tree: "WARDTree", entry_key: bytes) -> messages.WARDProofAck:
    """Answer a WARDProofRequest by the opaque `entry_key` path (pull model): a
    membership proof (both leaf parts + proof) if the leaf is present, otherwise a
    non-membership witness (witness_entry_key, witness_commit), or an empty ack for an
    empty tree. Serving needs NO key -- the MAC is the stored key and the commit is
    over ciphertext -- so the host never learns the identifier or the value (§3)."""
    if tree.is_empty():
        return messages.WARDProofAck()
    leaf = tree.get_leaf(entry_key)
    if leaf is not None:
        return messages.WARDProofAck(
            proof=tree.get_proof_by_key(entry_key),
            content=make_leaf_content(leaf.content),
            identity=make_leaf_identity(leaf.key_type, leaf.identity),
        )
    proof, witness_entry_key, witness_commit = tree.get_nonmembership_proof_by_key(
        entry_key
    )
    return messages.WARDProofAck(
        proof=proof,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


def cache_entry(
    session: "Session", entry_key: bytes, sticky: bool = False
) -> messages.WARDCacheEntryAck:
    """Copy the trie entry at `entry_key` into the device's offline cache, STICKY if
    asked (kept even after WARD deletes it). The device pulls its proof through the
    registered ``ward_proof_callback``, verifies it, and stores it in the store of the
    app the entry belongs to. Returns (replaced, counter) only."""
    return session.call(
        messages.WARDCacheEntry(entry_key=entry_key, sticky=sticky),
        expect=messages.WARDCacheEntryAck,
    )


def export_cache(session: "Session") -> list[bytes]:
    """Back up the device's cached WARD entries: one blob per entry, sealed so only a
    device unlocked with the same wallet can load it."""
    return session.call(
        messages.WARDCacheExport(), expect=messages.WARDCacheExportAck
    ).entries


def import_cache(session: "Session", blobs: list[bytes]) -> messages.WARDCacheImportAck:
    """Load backed-up entries into the device's offline cache (sticky bits kept)."""
    return session.call(
        messages.WARDCacheImport(entries=blobs), expect=messages.WARDCacheImportAck
    )


def validate_cache(session: "Session") -> messages.WARDValidateCacheAck:
    """Check every cached entry against the device's root (after a sync); the device
    pulls one proof per entry through the registered ``ward_proof_callback``."""
    return session.call(
        messages.WARDValidateCache(), expect=messages.WARDValidateCacheAck
    )


def list_entries(
    session: "Session",
    app_id: Optional[str] = None,
    key_type: Optional[str] = None,
    device_id: Optional[int] = None,
) -> messages.WARDListEntriesAck:
    """Show every WARD entry matching the filters on the device screen. The device
    walks its trusted root and pulls each node through the registered
    ``ward_node_callback`` (e.g. ``tree_node_callback(tree)``), verifying it before
    use. Returns only counts: (shown, entries, counter, complete)."""
    return session.call(
        messages.WARDListEntries(app_id=app_id, key_type=key_type, device_id=device_id),
        expect=messages.WARDListEntriesAck,
    )


def tree_node_callback(
    tree: "WARDTree", max_nodes: int = 16
) -> Callable[[messages.WARDNodeRequest], messages.WARDNodeAck]:
    """Build an AppManifest.ward_node_callback that serves a listing walk from `tree`:
    the requested node and up to `max_nodes - 1` descendants in pre-order per round
    trip.

        client.app.ward_node_callback = ward.tree_node_callback(tree)
    """

    def _callback(msg: messages.WARDNodeRequest) -> messages.WARDNodeAck:
        nodes = []
        for split_bit, left, right, entry_key in tree.get_nodes(
            msg.node_hash, max_nodes
        ):
            if entry_key is None:
                nodes.append(
                    messages.WARDTrieNode(split_bit=split_bit, left=left, right=right)
                )
                continue
            leaf = tree.get_leaf(entry_key)
            assert leaf is not None
            nodes.append(
                messages.WARDTrieNode(
                    entry_key=entry_key,
                    content=make_leaf_content(leaf.content),
                    identity=make_leaf_identity(leaf.key_type, leaf.identity),
                )
            )
        return messages.WARDNodeAck(nodes=nodes)

    return _callback


def tree_proof_callback(
    tree: "WARDTree",
    attest: Optional[
        Callable[[bytes], Optional[messages.WARDAttestation]]
    ] = None,
) -> Callable[[messages.WARDProofRequest], messages.WARDProofAck]:
    """Build an AppManifest.ward_proof_callback that serves proofs from `tree`.

    Register it on the client so the device can pull WARD proofs on demand:
        client.app.ward_proof_callback = ward.tree_proof_callback(tree)

    Freshness is optional. With `attest`, a request carrying a `freshness_nonce` is
    answered with `attest(nonce)` -- the WM's current-head attestation over that
    nonce, or None when the WM is not asked or unreachable.
    """

    def _callback(msg: messages.WARDProofRequest) -> messages.WARDProofAck:
        # The device sends the opaque entry_key path; serve the proof for it.
        ack = build_proof_ack(tree, msg.entry_key)
        if attest is not None and msg.freshness_nonce is not None:
            ack.attestation = attest(msg.freshness_nonce)
        return ack

    return _callback
