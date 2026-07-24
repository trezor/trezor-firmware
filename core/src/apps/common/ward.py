"""Core WARD-facing API: the internal platform boundary (TC) between callers and
the WARD trust anchor (TW, apps.ward.service).

Two kinds of caller route through here:
  - On-device apps (Bitcoin/Ethereum getAddress, DisplayAddress, ...) call
    `lookup_label`, which is CAPABILITY-GATED: the caller passes its first-party
    `app_id`, checked against a static allowlist. This scopes which on-device app
    may authenticate a WARD label.
  - The host-facing WARD wire handlers (apps.ward.*) call the UNGATED ops below
    (lookup / add_pending / commit / confirm_commit / sync / list_pending /
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
    value: bytes,
    proof: list[bytes],
    counter: int,
) -> bytes | None:
    """GATED on-device label lookup. Authorize `app_id` for `lookup`, then
    authenticate (address, value) against the device's WARD root. Returns the
    verified label, or None if the proof does not verify (or the tree is empty).
    Raises DataError if `app_id` lacks the capability.
    """
    _authorize(app_id, "lookup")
    from apps.ward import service

    return await service.lookup_label_impl(address, value, proof, counter)


async def _classify_label(
    address: bytes,
    value: bytes | None,
    proof: list[bytes],
    counter: int | None,
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    witness_counter: int | None = None,
) -> tuple[str, bytes | None]:
    """Verify a (membership / non-membership) proof against the device's
    authenticated root and classify it. Returns (status, label), where status is
    "unknown" / "membership" / "non-membership" and label is the verified value
    bytes (only for a valid membership proof, else None). Shared by the PUSH and
    PULL label paths."""
    valid, _counter, membership, _wallet_id = await lookup(
        address,
        value,
        proof,
        witness_address=witness_address,
        witness_value=witness_value,
        counter=counter,
        witness_counter=witness_counter,
    )
    if not valid:
        return "unknown", None
    if membership:
        # `lookup` already verified (address, value, counter) against the root,
        # so the supplied value is now trusted.
        return "membership", value
    return "non-membership", None


async def verify_label(
    app_id: str,
    address: bytes,
    value: bytes | None,
    proof: list[bytes],
    counter: int | None,
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    witness_counter: int | None = None,
) -> tuple[str, bytes | None]:
    """GATED PUSH-path label resolution: classify a proof the host attached
    up-front (e.g. DisplayAddress.ward_*). Returns (status, label). Raises
    DataError if `app_id` lacks the `lookup` capability."""
    _authorize(app_id, "lookup")
    return await _classify_label(
        address,
        value,
        proof,
        counter,
        witness_address=witness_address,
        witness_value=witness_value,
        witness_counter=witness_counter,
    )


async def resolve_label(app_id: str, address: bytes) -> tuple[str, bytes | None]:
    """GATED PULL-path label resolution for on-device apps.

    Rather than trusting a proof the host pushed up-front, the device PULLS it:
    it sends a WARDProofRequest naming `address`, the host answers with the WARD
    entry + proof it holds (WARDProofAck), and this verifies that proof against
    the device's authenticated root. Returns (status, label) — see verify_label.

    Reusable by any on-device app that displays an address (DisplayAddress,
    Bitcoin/Ethereum getAddress, sign-tx outputs). Raises DataError if `app_id`
    lacks the `lookup` capability.
    """
    _authorize(app_id, "lookup")
    from trezor.messages import WARDProofAck, WARDProofRequest
    from trezor.wire import context

    ack = await context.call(WARDProofRequest(address=address), WARDProofAck)

    # A membership answer carries a value (and no witness); a non-membership
    # answer carries witness fields (or nothing at all, for an empty tree).
    return await _classify_label(
        address,
        ack.value,
        ack.proof,
        ack.counter,
        witness_address=ack.witness_address,
        witness_value=ack.witness_value,
        witness_counter=ack.witness_counter,
    )


# ---------------------------------------------------------------------------
# UNGATED host-facing ops. The WARD App (host wire handlers) drives these; the
# host is the WARD owner, not a gated on-device principal. Thin pass-throughs to
# the trust anchor, kept here so it has a single gateway. Public host-side naming
# prefers add_pending / sync / reconcile; the legacy wire message names remain.
# ---------------------------------------------------------------------------


async def lookup(
    address: bytes,
    value: bytes | None,
    proof: list[bytes],
    witness_address: bytes | None = None,
    witness_value: bytes | None = None,
    counter: int | None = None,
    witness_counter: int | None = None,
) -> tuple[bool, int, bool, bytes]:
    """Verify a membership / non-membership proof against the device's WARD root.
    Returns (valid, counter, membership, wallet_id). General proof-verification
    path used by the host WARDLookup handler.
    """
    from apps.ward import service

    return await service.lookup_impl(
        address,
        value,
        proof,
        witness_address=witness_address,
        witness_value=witness_value,
        counter=counter,
        witness_counter=witness_counter,
    )


async def add_pending(
    address: bytes,
    old_value: bytes,
    new_value: bytes,
    new_counter: int,
    proof: list[bytes],
    old_counter: int | None = None,
    witness_address: bytes | None = None,
    witness_counter: int | None = None,
    witness_value: bytes | None = None,
) -> tuple[int, bytes]:
    """Verify + queue the candidate edit via the WARD trust anchor. Returns
    (candidate_counter, wallet_id). The host update round's WARDAddPending step
    calls this; the counter only advances later at WARDConfirmCommit.
    """
    from apps.ward import service

    return await service.add_pending_impl(
        address,
        old_value,
        new_value,
        new_counter,
        proof,
        old_counter=old_counter,
        witness_address=witness_address,
        witness_counter=witness_counter,
        witness_value=witness_value,
    )


async def commit() -> tuple[int, bytes | None, bytes | None, bytes]:
    from apps.ward import service

    return await service.commit_impl()


async def confirm_commit(
    counter: int, mac: bytes | None, qm_signature: bytes
) -> tuple[int, bytes | None, bytes, bytes | None]:
    from apps.ward import service

    return await service.confirm_commit_impl(counter, mac, qm_signature)


async def sync() -> tuple[bytes, int, bytes]:
    from apps.ward import service

    return await service.sync_impl()


async def ingest_attestation(
    counter: int, mac: bytes | None, wm_signature: bytes
) -> tuple[int, bytes]:
    from apps.ward import service

    return await service.ingest_attestation_impl(counter, mac, wm_signature)


async def reconcile(
    root: bytes | None,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    from apps.ward import service

    return await service.reconcile_impl(root)


async def list_pending() -> tuple[list[bytes], bytes]:
    """Return queued pending-edit addresses.

    Note:
    - wallet_id is still returned for compatibility with current callers
    - list_pending() should not be the long-term source of wallet_id
    """
    from apps.ward import service

    return await service.list_pending_impl()


async def debug_set_root(
    root: bytes,
) -> tuple[int, bytes | None, bytes, bytes | None]:
    from apps.ward import service

    return await service.debug_set_root_impl(root)
