"""Core WARD-facing API: the internal platform boundary (TC) between callers and
the WARD trust anchor (TW, apps.ward.service).

Two kinds of caller route through here:
  - On-device apps (DisplayAddress; later Bitcoin/Ethereum and third-party apps)
    call `resolve_label` / `verify_label` with their WardCaller. They are
    CAPABILITY-GATED by the firmware's grant (`_label_domain`), and never name the
    domain they read.
  - The host-facing WARD wire handlers (apps.ward.*) call the ops below (lookup /
    queue / perform / sync / ...). The host is the WARD driver, not an on-device
    app; its requests are served under `caller.ADDRESS_LABELS`, the domain the
    service fixes for host-driven labels (`caller.host_caller`).

Every entry point takes a `WardCaller` (apps.ward.caller), which the firmware creates:
the domain an operation touches comes from the caller's identity, never from a name the
app or the host passes. Host wire handlers use `caller.host_caller`, which refuses a host
that tries to pick the domain, key type or device slot.
"""


def _label_domain(caller):
    """The domain `caller` may read labels from -- the firmware's grant, never the
    caller's choice. DisplayAddress reads the host-written address labels; no other app
    may read labels yet."""
    from trezor.wire import DataError

    from apps.ward.caller import ADDRESS_LABELS, DISPLAY_ADDRESS

    if caller is DISPLAY_ADDRESS:
        return ADDRESS_LABELS
    raise DataError("app not authorized for WARD lookup")


# --- LeafIdentity / LeafContent wire <-> internal part codec ---
# A leaf is two independently encoded parts. The wire carries a self-describing
# oneof per part (EncryptedIdentity|PlainIdentity, EncryptedLeaf|PlaintextLeaf); the
# firmware works internally on a `part` tuple (encoding, nonce, tag, body). These
# helpers are the only place that maps between the two, and they enforce that a
# received encoding matches this build's mode for that part (an encrypted-only
# release rejects a plaintext part). See leaf.WARD_PLAINTEXT_IDENTITY /
# WARD_PLAINTEXT_CONTENT.


def make_leaf_content(part):
    """Build a LeafContent from an internal content part."""
    from trezor.messages import EncryptedLeaf, LeafContent, PlaintextLeaf

    from apps.ward import leaf

    encoding, nonce, tag, body = part if part is not None else leaf.EMPTY_PART
    if encoding == leaf.ENC_PLAINTEXT:
        return LeafContent(encoding=1, plaintext=PlaintextLeaf(content=body))
    return LeafContent(
        encoding=0, encrypted=EncryptedLeaf(nonce=nonce, tag=tag, ct=body)
    )


def read_leaf_content(content):
    """Read a LeafContent into an internal content part. `content is None` (no leaf on
    the wire: a pull request, an empty tree, or a non-membership ack) returns None.
    Rejects a part whose encoding does not match this build."""
    from trezor.wire import DataError

    from apps.ward import leaf

    if content is None:
        return None
    if (content.encoding or 0) == 1:
        p = content.plaintext
        body = p.content if (p is not None and p.content is not None) else b""
        # An EMPTY body is the DELETE sentinel and is mode-agnostic -- there is nothing
        # to decrypt, so an encrypted-only build must still accept it.
        if len(body) > 0 and not leaf.WARD_PLAINTEXT_CONTENT:
            raise DataError("WARD: plaintext leaf but firmware is encrypted-only")
        return (leaf.ENC_PLAINTEXT, b"", b"", body)
    if leaf.WARD_PLAINTEXT_CONTENT:
        raise DataError("WARD: encrypted leaf but firmware is plaintext-only")
    e = content.encrypted
    if e is None:
        return None
    return (leaf.ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")


def make_leaf_identity(key_type: str, part):
    """Build a LeafIdentity from an internal identity part. `key_type` is always
    clear -- it selects both K_ident and K_data. An EMPTY part yields None: a deleted
    leaf no longer exists, so there is no identity to describe."""
    from trezor.messages import EncryptedIdentity, LeafIdentity, PlainIdentity

    from apps.ward import leaf

    if leaf.part_is_empty(part):
        return None
    encoding, nonce, tag, body = part
    if encoding == leaf.ENC_PLAINTEXT:
        identifier, app_id, device_id = leaf.unpack_identity(body)
        return LeafIdentity(
            encoding=1,
            key_type=key_type,
            plain=PlainIdentity(
                identifier=identifier, app_id=app_id.decode(), device_id=device_id
            ),
        )
    return LeafIdentity(
        encoding=0,
        key_type=key_type,
        encrypted=EncryptedIdentity(nonce=nonce, tag=tag, ct=body),
    )


def read_leaf_identity(identity):
    """Read a LeafIdentity into (key_type, part). `identity is None` returns
    (None, None). Rejects a part whose encoding does not match this build."""
    from trezor.wire import DataError

    from apps.ward import keys, leaf

    if identity is None:
        return None, None
    key_type = identity.key_type or keys.ENTRY_TYPE_ADDRESS
    if (identity.encoding or 0) == 1:
        if not leaf.WARD_PLAINTEXT_IDENTITY:
            raise DataError("WARD: plaintext identity but firmware is encrypted-only")
        p = identity.plain
        if p is None:
            return key_type, None
        body = leaf.pack_identity(
            p.identifier or b"", p.app_id or b"", p.device_id or 0
        )
        return key_type, (leaf.ENC_PLAINTEXT, b"", b"", body)
    if leaf.WARD_PLAINTEXT_IDENTITY:
        raise DataError("WARD: encrypted identity but firmware is plaintext-only")
    e = identity.encrypted
    if e is None:
        return key_type, None
    return key_type, (leaf.ENC_ENCRYPTED, e.nonce or b"", e.tag or b"", e.ct or b"")


async def _classify_label(
    domain,
    address: bytes,
    id_part,
    val_part,
    proof: list[bytes],
    key_type: str = "address",
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[str, bytes | None]:
    """Verify a (membership / non-membership) proof against the device's root and
    classify it. Returns (status, label): status in unknown/membership/non-membership;
    label is the DECRYPTED value only for a valid membership proof. Shared by the PUSH
    (verify_label) and PULL (resolve_label) label paths."""
    valid, _counter, membership, _wallet_id, _ward_id = await lookup(
        domain,
        address,
        id_part,
        val_part,
        proof,
        key_type=key_type,
        device_id=device_id,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )
    if not valid:
        return "unknown", None
    if membership:
        from apps.ward import service

        value = await service.lookup_label(
            domain, address, id_part, val_part, proof, key_type, device_id
        )
        return "membership", value
    return "non-membership", None


# FIXME(ward, PUSH-ONLY): the PUSH read path. PULL is the default and only exercised
# model; this is retained for the future PUSH deployment, where the host holds the
# exported keys (WARDExportKeys) and attaches the proof up front instead of answering a
# device-initiated WARDProofRequest. It is complete and correct but INACTIVE: nothing
# calls WARDExportKeys, so no host can currently compute an entry_key to build a proof.
async def verify_label(
    caller,
    address: bytes,
    id_part,
    val_part,
    proof: list[bytes],
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[str, bytes | None]:
    """GATED PUSH-path label resolution: classify a proof the host attached up-front
    (e.g. DisplayAddressWithProof). Returns (status, label). The domain is the one the
    firmware grants `caller` for labels (`_label_domain`)."""
    return await _classify_label(
        _label_domain(caller),
        address,
        id_part,
        val_part,
        proof,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


async def resolve_label(caller, address: bytes) -> tuple[str, bytes | None, int]:
    """GATED PULL-path label resolution for on-device apps. The device computes the
    opaque entry_key path itself, sends a WARDProofRequest carrying only that path
    (never the identifier or domain), and verifies the host's WARDProofAck against
    its authenticated root. Returns (status, label, freshness).

    The request also carries a fresh nonce. A host MAY answer it with the WM's
    current-head attestation; `freshness` is then whether the root the label was
    checked against is still current (`service.FRESH_*`). Asking the WM is the
    host's choice -- FRESH_UNCHECKED when it did not.

    The domain is the one the firmware grants `caller` for labels (`_label_domain`);
    labels are always of key type "address" in device slot 0x00.

    The offline cache follows every verified answer: a cached copy of this entry is
    updated to the proven value, or removed when WARD proves it absent. A host that
    answers `unavailable` (no wardd) gets status "cached" with the value of a STICKY
    cached copy, unverified -- or "unverified" with no label if there is none; see
    `service.cached_label` for why that is an accepted DoS."""
    domain = _label_domain(caller)
    from trezor import log
    from trezor.crypto import random
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    from apps.ward import keys, service

    ek = await keys.entry_key_for(domain, address)
    log.debug(__name__, "resolve_label: pulling proof (entry_key computed)")
    nonce = random.bytes(32)
    ack = await context.call(
        WARDProofRequest(entry_key=ek, freshness_nonce=nonce), WARDProofAck
    )
    if ack.unavailable:
        cached = await service.cached_label(domain, address)
        log.debug(
            __name__, "resolve_label: host unavailable, sticky=%s", cached is not None
        )
        if cached is None:
            return "unverified", None, service.FRESH_UNCHECKED
        return "cached", cached, service.FRESH_UNCHECKED
    a_val = read_leaf_content(ack.content)
    _a_kt, a_id = read_leaf_identity(ack.identity)
    log.debug(
        __name__,
        "resolve_label: WARDProofAck membership=%s witness=%s attested=%s",
        ack.content is not None,
        ack.witness_entry_key is not None,
        ack.attestation is not None,
    )

    # Membership => the two parts; non-membership => witness_*; empty => nothing.
    status, label = await _classify_label(
        domain,
        address,
        a_id,
        a_val,
        [bytes(node) for node in ack.proof],
        witness_entry_key=(
            bytes(ack.witness_entry_key) if ack.witness_entry_key is not None else None
        ),
        witness_commit=(
            bytes(ack.witness_commit) if ack.witness_commit is not None else None
        ),
    )
    await service.refresh_cached_label(domain, address, status, a_val)
    att = ack.attestation
    freshness = await service.label_freshness(
        nonce,
        (
            None
            if att is None
            else (
                att.counter,
                bytes(att.mac) if att.mac is not None else None,
                bytes(att.wm_signature),
                att.timestamp,
                bytes(att.head_nonce),
            )
        ),
    )
    return status, label, freshness


# ---------------------------------------------------------------------------
# UNGATED host-facing ops. The WARD App (host wire handlers) drives these; the
# host is the WARD owner, not a gated on-device principal. Thin pass-throughs to
# the trust anchor, kept here so it has a single gateway. Public host-side naming
# prefers add_pending / sync / reconcile; the legacy wire message names remain.
# ---------------------------------------------------------------------------


# FIXME(ward, PUSH-ONLY): host-pushed proof verification. See verify_label above --
# reachable today only via the WARDLookup PUSH branch, which no connect method drives.
async def lookup(
    caller,
    address: bytes,
    id_part,
    val_part,
    proof: list[bytes],
    key_type: str = "address",
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[bool, int, bool, bytes, bytes]:
    """Verify a membership / non-membership proof against the device's WARD root.
    Returns (valid, counter, membership, wallet_id, ward_id). The device forms
    entry_key from (caller domain, key_type, device_id, address); membership carries the
    leaf's two parts; a non-membership witness is passed opaquely as
    (witness_entry_key, witness_commit)."""
    from apps.ward import service

    return await service.lookup(
        caller,
        address,
        id_part,
        val_part,
        proof,
        key_type=key_type,
        device_id=device_id,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


async def lookup_pull(
    caller,
    address: bytes,
    key_type: str = "address",
    device_id: int = 0,
) -> tuple[bool, int, bool, bytes, bytes]:
    """Host-driven PULL verify: the device computes the target entry_key itself,
    PULLS the proof from the host on demand (WARDProofRequest -> WARDProofAck), and
    returns the verdict (valid, counter, membership, wallet_id, ward_id). Ungated
    (the host is the driver, like `lookup`).

    Unlike the pushed `lookup`, the host never has to know the target entry_key: the
    device sends it in WARDProofRequest, so a NON-membership verdict for an absent
    address is device-proven (the host builds the witness from the entry_keys it
    already stores). The wire I/O lives here in the Core gateway, not the trust
    anchor. Mirrors `resolve_label`, but returns the verdict rather than a label."""
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    from apps.ward import keys, service

    ek = await keys.entry_key_for(caller, address, key_type, device_id)
    ack = await context.call(WARDProofRequest(entry_key=ek), WARDProofAck)
    a_val = read_leaf_content(ack.content)
    _a_kt, a_id = read_leaf_identity(ack.identity)

    return await service.lookup(
        caller,
        address,
        a_id,
        a_val,
        [bytes(node) for node in ack.proof],
        key_type=key_type,
        device_id=device_id,
        witness_entry_key=(
            bytes(ack.witness_entry_key) if ack.witness_entry_key is not None else None
        ),
        witness_commit=(
            bytes(ack.witness_commit) if ack.witness_commit is not None else None
        ),
    )


async def cache_entry(entry_key: bytes, sticky: bool = False) -> tuple[bool, int]:
    """Copy the trie entry at `entry_key` into its app's offline cache. The proof pull
    (WARDProofRequest -> WARDProofAck) lives here in the gateway; the trust anchor
    verifies it and stores. Returns (replaced, counter)."""
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    from apps.ward import service

    ack = await context.call(WARDProofRequest(entry_key=entry_key), WARDProofAck)
    kt, id_part = read_leaf_identity(ack.identity)
    return await service.cache_entry(
        entry_key,
        kt,
        id_part,
        read_leaf_content(ack.content),
        [bytes(node) for node in ack.proof],
        ack.witness_entry_key is not None,
        sticky,
    )


async def validate_cache() -> tuple[int, int, int, int]:
    """Check the offline cache against the trie; one proof pull (WARDProofRequest ->
    WARDProofAck) per cached entry lives here in the gateway, the verdicts in the
    trust anchor. Returns (checked, unchanged, updated, removed)."""
    from apps.ward import service

    return await service.validate_cache(_pull_entry)


async def import_cache(blobs: list[bytes]) -> tuple[int, int]:
    """Load a cache backup; the trust anchor checks every entry against the root with a
    proof pulled here (one WARDProofRequest per entry). Returns (imported, skipped)."""
    from apps.ward import service

    return await service.import_cache(blobs, _pull_entry)


async def _pull_entry(entry_key: bytes) -> tuple:
    """One proof pull for the offline-cache checks: (key_type, id_part, val_part, proof,
    witness_entry_key, witness_commit). A host that answers `unavailable` fails the
    check -- these flows act on proofs only, never on their absence."""
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import DataError, context

    ack = await context.call(WARDProofRequest(entry_key=entry_key), WARDProofAck)
    if ack.unavailable:
        raise DataError("WARD cache: the host cannot serve proofs")
    kt, id_part = read_leaf_identity(ack.identity)
    return (
        kt,
        id_part,
        read_leaf_content(ack.content),
        [bytes(node) for node in ack.proof],
        bytes(ack.witness_entry_key) if ack.witness_entry_key is not None else None,
        bytes(ack.witness_commit) if ack.witness_commit is not None else None,
    )


async def list_entries(
    app_id: str | None = None,
    key_type: str | None = None,
    device_id: int | None = None,
) -> tuple[int, int, int, bool]:
    """Show every matching entry on-device via a verified walk of the trusted root.
    The node pulls (WARDNodeRequest -> WARDNodeAck) live here in the gateway; the
    trust anchor verifies each node before it uses it. Returns
    (shown, entries, counter, complete)."""
    from trezor.messages import WARDNodeAck, WARDNodeRequest
    from trezor.wire import context

    from apps.ward import service

    async def fetch(node_hash: bytes) -> list:
        ack = await context.call(WARDNodeRequest(node_hash=node_hash), WARDNodeAck)
        return [
            (
                n.split_bit,
                bytes(n.left) if n.left is not None else None,
                bytes(n.right) if n.right is not None else None,
                bytes(n.entry_key) if n.entry_key is not None else None,
                read_leaf_identity(n.identity),
                read_leaf_content(n.content),
            )
            for n in ack.nodes
        ]

    return await service.list_entries(fetch, app_id, key_type, device_id)


async def queue(
    caller,
    address: bytes,
    new_value: bytes,
    key_type: str = "address",
    device_id: int = 0,
    delete: bool = False,
) -> tuple[int, bytes]:
    """Queue an edit INTENT via the WARD trust anchor (pull model) for the domain
    of `caller` (a firmware-made WardCaller). The trust anchor checks its ACL, shows the domain + new value
    on a trusted screen, and returns (pending_id, wallet_id) only on user approval.
    No proof and no candidate counter here (strict model: counter_T is derived
    later, inside the WM-synchronized WARDPerformUpdate flow). key_type/device_id
    scope the entry_key the candidate will land on (§5.1).
    """
    from apps.ward import service

    return await service.queue(caller, address, new_value, key_type, device_id, delete)


async def perform(
    pending_id: int | None = None,
) -> tuple:
    """Authorize a queued intent. Resolves it to its opaque entry_key, PULLS the
    proof (WARDProofRequest(entry_key, pending_id) -> WARDProofAck), then hands the
    ack to the trust anchor to derive counter_T + compute the candidate and the new
    leaf (both parts). The wire I/O (context.call) lives here in the Core gateway.
    Returns (counter_T, root_T, mac_T, wallet_id, ward_id, entry_key, key_type,
    id_part, val_part) -- the trailing leaf lets the host store what it cannot
    compute itself."""
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    from apps.ward import service

    pid, ek = await service.intent(pending_id)

    ack = await context.call(
        WARDProofRequest(entry_key=ek, pending_id=pid),
        WARDProofAck,
    )
    a_val = read_leaf_content(ack.content)
    _a_kt, a_id = read_leaf_identity(ack.identity)

    return await service.perform(
        pid,
        a_id,
        a_val,
        [bytes(node) for node in ack.proof],
        witness_entry_key=(
            bytes(ack.witness_entry_key) if ack.witness_entry_key is not None else None
        ),
        witness_commit=(
            bytes(ack.witness_commit) if ack.witness_commit is not None else None
        ),
    )


async def finalize(
    counter: int,
    mac: bytes | None,
    wm_signature: bytes,
    pending_id: int | None = None,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    from apps.ward import service

    return await service.finalize(counter, mac, wm_signature, pending_id)


async def perform_batch(pending_ids: list) -> tuple:
    """Authorize a BATCH of queued intents as ONE root transition. Pulls a pre-state
    proof for EACH intent (one WARDProofRequest per opaque entry_key), collects the
    acks, then hands them all to the trust anchor to fold into one successor root and
    authenticate with head_mac + AuthCommit. The wire I/O lives here in the gateway.
    Returns (to_counter, to_root, mac_t, head_mac, auth_commit, sig, wallet_id,
    ward_id, leaves)."""
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    from apps.ward import service

    resolved = []  # type: list[int]
    acks = []  # type: list[tuple]
    for pid in pending_ids:
        rpid, ek = await service.intent(pid)
        ack = await context.call(
            WARDProofRequest(entry_key=ek, pending_id=rpid),
            WARDProofAck,
        )
        a_val = read_leaf_content(ack.content)
        _a_kt, a_id = read_leaf_identity(ack.identity)
        acks.append(
            (
                a_id,
                a_val,
                [bytes(node) for node in ack.proof],
                bytes(ack.witness_entry_key)
                if ack.witness_entry_key is not None
                else None,
                bytes(ack.witness_commit) if ack.witness_commit is not None else None,
            )
        )
        resolved.append(rpid)

    return await service.perform_batch(resolved, acks)


async def finalize_batch(
    counter: int,
    mac: bytes | None,
    wm_signature: bytes,
) -> tuple:
    from apps.ward import service

    return await service.finalize_batch(counter, mac, wm_signature)


async def perform_revert(
    stuck_counter: int,
    stuck_root: bytes,
    prev_root: bytes,
    forward_auth_commit: bytes,
) -> tuple:
    """Prepare a one-step rollback. No proof pull — the predecessor is proven by the
    host-supplied forward AuthCommit the trust anchor verifies."""
    from apps.ward import service

    return await service.perform_revert(
        stuck_counter, stuck_root, prev_root, forward_auth_commit
    )


async def finalize_revert(
    counter: int,
    mac: bytes | None,
    wm_signature: bytes,
) -> tuple:
    from apps.ward import service

    return await service.finalize_revert(counter, mac, wm_signature)


async def discard(
    pending_id: int | None = None,
) -> tuple[bytes | None, bytes]:
    """Abandon queued pending edit(s) for the active wallet. With pending_id, drops
    just that candidate and returns its address; without, drops all of the
    wallet's candidates. Returns (discarded_address, wallet_id); discarded_address
    is None when nothing matched (or in drop-all mode)."""
    from apps.ward import service

    return await service.discard(pending_id)


async def sync() -> tuple[bytes, int, bytes, bytes]:
    from apps.ward import service

    return await service.sync()


async def ingest(
    counter: int,
    mac: bytes | None,
    wm_signature: bytes,
    timestamp: int,
    head_nonce: bytes,
) -> tuple[int, bytes]:
    from apps.ward import service

    return await service.ingest(counter, mac, wm_signature, timestamp, head_nonce)


async def reconcile(
    root: bytes | None,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    from apps.ward import service

    return await service.reconcile(root)


async def verify_chain(links: list) -> tuple:
    """Adopt the WM-attested head by verifying the AuthCommit chain (Phase 4a). No
    proof pull — the host supplies the ordered links from its lineage store."""
    from apps.ward import service

    return await service.verify_chain(links)


async def pending() -> tuple[list[int], list[bytes], bytes, bytes]:
    """Return queued (pending_ids, addresses, wallet_id, ward_id) for the active
    wallet.

    Note:
    - wallet_id is still returned for compatibility with current callers
    - pending() should not be the long-term source of wallet_id
    - ward_id is the SLIP21-derived WM anchor a host uses to key WARD storage
    """
    from apps.ward import service

    return await service.pending()


async def debug_set_root(
    root: bytes,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    from apps.ward import service

    return await service.debug_set_root(root)


# FIXME(ward, PUSH-ONLY): NO CALLER anywhere in firmware, trezorlib, or connect. This
# is the single missing wire that would activate the whole PUSH path -- without it a host
# cannot derive entry_key and therefore cannot push a proof.
async def export_keys(key_type: str = "address") -> tuple:
    """PUSH key export (user-confirmed inside the trust anchor). Returns
    (k_path, k_data, k_ident) for the requested entry type; K_sig is never exported.
    The three are independent capabilities -- resolve identifier -> path, read values,
    read identities -- so a caller can be granted indexing without value reads."""
    from apps.ward import service

    return await service.export_keys(key_type)
