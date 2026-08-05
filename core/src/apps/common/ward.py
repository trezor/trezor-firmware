"""Core WARD-facing API: the internal platform boundary (TC) between callers and
the WARD trust anchor (TW, apps.ward.service).

Two kinds of caller route through here:
  - On-device apps (Bitcoin/Ethereum getAddress, DisplayAddress, ...) call
    `lookup_label`, which is CAPABILITY-GATED: the caller passes its first-party
    `app_id`, checked against a static allowlist. This scopes which on-device app
    may authenticate a WARD label.
  - The host-facing WARD wire handlers (apps.ward.*) call the UNGATED ops below
    (lookup / add_pending / commit / confirm_commit / sync / pending /
    debug_set_root). The host is the WARD owner/driver, not an on-device app
    principal, so it is not capability-gated; these are thin pass-throughs kept
    here only so the trust anchor has a single gateway.

`app_id` is a trusted constant a firmware module passes; the gate is capability
scoping for on-device apps, not authenticating an untrusted principal.
"""

from typing import TYPE_CHECKING

# Capability allowlist for the GATED on-device entry point (lookup_label).
# Each app id maps to the WARD capabilities it may invoke.
_CAPABILITIES = {
    "bitcoin": ("lookup",),
    "ethereum": ("lookup",),
    "display_address": ("lookup",),
}

if TYPE_CHECKING:
    pass


def _authorize(app_id: str, capability: str) -> None:
    from trezor.wire import DataError

    if capability not in _CAPABILITIES.get(app_id, ()):
        raise DataError("app not authorized for WARD " + capability)


async def lookup_label(
    app_id: str,
    address: bytes,
    nonce: bytes,
    tag: bytes,
    ct: bytes,
    proof: list[bytes],
    key_type: str = "address",
    device_id: int = 0,
) -> bytes | None:
    """GATED on-device membership label lookup. Authorize `app_id` for `lookup`,
    then authenticate the leaf blob (nonce, tag, ct) against the device's WARD root
    and return the decrypted label, or None if it does not verify (or the tree is
    empty). Raises DataError if `app_id` lacks the capability."""
    _authorize(app_id, "lookup")
    from apps.ward import service

    return await service.lookup_label(
        app_id, address, nonce, tag, ct, proof, key_type, device_id
    )


async def _classify_label(
    app_id: str,
    address: bytes,
    nonce: bytes | None,
    tag: bytes | None,
    ct: bytes | None,
    proof: list[bytes],
    entry_type: str = "address",
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[str, bytes | None]:
    """Verify a (membership / non-membership) proof against the device's root and
    classify it. Returns (status, label): status ∈ unknown/membership/non-membership;
    label is the DECRYPTED value only for a valid membership proof. Shared by the
    PUSH and PULL label paths."""
    valid, _counter, membership, _wallet_id, _ward_id = await lookup(
        app_id,
        address,
        nonce,
        tag,
        ct,
        proof,
        key_type=entry_type,
        device_id=device_id,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )
    if not valid:
        return "unknown", None
    if membership:
        from apps.ward import service

        value = await service.lookup_label(
            app_id, address, nonce, tag, ct, proof, entry_type, device_id
        )
        return "membership", value
    return "non-membership", None


async def verify_label(
    app_id: str,
    address: bytes,
    nonce: bytes | None,
    tag: bytes | None,
    ct: bytes | None,
    proof: list[bytes],
    entry_type: str = "address",
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
    domain: str | None = None,
) -> tuple[str, bytes | None]:
    """GATED PUSH-path label resolution: classify a proof the host attached up-front
    (e.g. DisplayAddressWithProof). Returns (status, label). `app_id` is the
    capability principal (gated); `domain` is the WARD domain that forms entry_key,
    defaulting to `app_id`."""
    _authorize(app_id, "lookup")
    return await _classify_label(
        domain if domain is not None else app_id,
        address,
        nonce,
        tag,
        ct,
        proof,
        entry_type=entry_type,
        device_id=device_id,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


async def resolve_label(
    app_id: str,
    address: bytes,
    domain: str | None = None,
    entry_type: str = "address",
    device_id: int = 0,
) -> tuple[str, bytes | None]:
    """GATED PULL-path label resolution for on-device apps. The device computes the
    opaque entry_key path itself, sends a WARDProofRequest carrying only that path
    (never the identifier or domain), and verifies the host's WARDProofAck against
    its authenticated root. Returns (status, label)."""
    _authorize(app_id, "lookup")
    from trezor import log
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    from apps.ward import service

    domain = domain if domain is not None else app_id
    ek = await service.entry_key_for(domain, address, entry_type, device_id)
    log.debug(
        __name__,
        "resolve_label: pulling proof for domain=%s entry_type=%s (entry_key computed)",
        domain,
        entry_type,
    )
    ack = await context.call(WARDProofRequest(entry_key=ek), WARDProofAck)
    log.debug(
        __name__,
        "resolve_label: WARDProofAck membership=%s witness=%s",
        ack.ct is not None,
        ack.witness_entry_key is not None,
    )

    # Membership => (nonce, tag, ct); non-membership => witness_* ; empty => nothing.
    return await _classify_label(
        domain,
        address,
        ack.nonce,
        ack.tag,
        ack.ct,
        ack.proof,
        entry_type=entry_type,
        device_id=device_id,
        witness_entry_key=ack.witness_entry_key,
        witness_commit=ack.witness_commit,
    )


# ---------------------------------------------------------------------------
# UNGATED host-facing ops. The WARD App (host wire handlers) drives these; the
# host is the WARD owner, not a gated on-device principal. Thin pass-throughs to
# the trust anchor, kept here so it has a single gateway. Public host-side naming
# prefers add_pending / sync / reconcile; the legacy wire message names remain.
# ---------------------------------------------------------------------------


async def lookup(
    app_id,
    address: bytes,
    nonce: bytes | None,
    tag: bytes | None,
    ct: bytes | None,
    proof: list[bytes],
    key_type: str = "address",
    device_id: int = 0,
    witness_entry_key: bytes | None = None,
    witness_commit: bytes | None = None,
) -> tuple[bool, int, bool, bytes, bytes]:
    """Verify a membership / non-membership proof against the device's WARD root.
    Returns (valid, counter, membership, wallet_id, ward_id). The device forms
    entry_key from (app_id, key_type, device_id, address); membership carries the
    leaf blob (nonce, tag, ct); a non-membership witness is passed opaquely as
    (witness_entry_key, witness_commit)."""
    from apps.ward import service

    return await service.lookup(
        app_id,
        address,
        nonce,
        tag,
        ct,
        proof,
        key_type=key_type,
        device_id=device_id,
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )


async def lookup_pull(
    app_id,
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

    from apps.ward import service

    ek = await service.entry_key_for(app_id, address, key_type, device_id)
    ack = await context.call(WARDProofRequest(entry_key=ek), WARDProofAck)

    return await service.lookup(
        app_id,
        address,
        ack.nonce,
        ack.tag,
        ack.ct,
        ack.proof,
        key_type=key_type,
        device_id=device_id,
        witness_entry_key=ack.witness_entry_key,
        witness_commit=ack.witness_commit,
    )


async def queue(
    app_id,
    address: bytes,
    new_value: bytes,
    key_type: str = "address",
    device_id: int = 0,
) -> tuple[int, bytes]:
    """Queue an edit INTENT via the WARD trust anchor (pull model) for the domain
    named by app_id. The trust anchor checks its ACL, shows the domain + new value
    on a trusted screen, and returns (pending_id, wallet_id) only on user approval.
    No proof and no candidate counter here (strict model: counter_T is derived
    later, inside the WM-synchronized WARDPerformUpdate flow). key_type/device_id
    scope the entry_key the candidate will land on (§5.1).
    """
    from apps.ward import service

    return await service.queue(app_id, address, new_value, key_type, device_id)


async def perform(
    pending_id: int | None = None,
) -> tuple:
    """Authorize a queued intent. Resolves it to its opaque entry_key, PULLS the
    proof (WARDProofRequest(entry_key, pending_id) -> WARDProofAck), then hands the
    ack to the trust anchor to derive counter_T + compute the candidate and the new
    encrypted leaf blob. The wire I/O (context.call) lives here in the Core gateway.
    Returns (counter_T, root_T, mac_T, wallet_id, ward_id, entry_key, entry_type,
    nonce, tag, ct) -- the trailing blob lets the host store the leaf it can't
    compute itself."""
    from apps.ward import service
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    pid, ek = await service.intent(pending_id)

    ack = await context.call(
        WARDProofRequest(entry_key=ek, pending_id=pid),
        WARDProofAck,
    )

    return await service.perform(
        pid,
        ack.nonce,
        ack.tag,
        ack.ct,
        ack.proof,
        witness_entry_key=ack.witness_entry_key,
        witness_commit=ack.witness_commit,
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
    from apps.ward import service
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    resolved = []  # type: list[int]
    acks = []  # type: list[tuple]
    for pid in pending_ids:
        rpid, ek = await service.intent(pid)
        ack = await context.call(
            WARDProofRequest(entry_key=ek, pending_id=rpid),
            WARDProofAck,
        )
        acks.append(
            (
                ack.nonce,
                ack.tag,
                ack.ct,
                ack.proof,
                ack.witness_entry_key,
                ack.witness_commit,
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
    counter: int, mac: bytes | None, wm_signature: bytes
) -> tuple[int, bytes]:
    from apps.ward import service

    return await service.ingest(counter, mac, wm_signature)


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


async def export_keys(key_type: str = "address") -> tuple:
    """PUSH key export (user-confirmed inside the trust anchor). Returns
    (k_index, k_data) for the requested entry type; K_sig is never exported."""
    from apps.ward import service

    return await service.export_keys(key_type)
