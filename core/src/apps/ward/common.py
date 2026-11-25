from typing import TYPE_CHECKING

from trezor import utils

if TYPE_CHECKING:
    from trezor.messages import WardLeafAck, WardMutationApplied
    from trezor.ui.layouts import StrPropertyType

# Sealing and the trie stop a host forging a value or moving a leaf between paths, but against a
# root this session has not had attested it can still serve an OLDER tree: the value is authentic,
# its freshness is not proven. Shown unless the WM attested the head in this session -- see
# `add_freshness`, which names the WM's timestamp for the head instead when it knows one.
WARNING_UNVERIFIED: "StrPropertyType" = (
    "Warning",
    "Not proven current; may be out of date.",
    False,
)

# FIXME(ward): all WARD screen strings are hardcoded English; move them to TR.* before shipping.

# GAP(ward): a host cannot know whether its replica is COMPLETE -- a missing leaf yields a
# well-formed proof against a different root. The device is the completeness oracle: an
# accepted adoption proves the replica held the tree that step produced. One refusal therefore
# covers a replica that is behind, one that is partial, and data that is lost; only
# `WardRollback` recovers the last.


def display_bytes(value: bytes) -> str:
    """UTF-8 when it decodes cleanly, otherwise hex."""
    try:
        return value.decode()
    except UnicodeError:
        # NOT `ubinascii`: this firmware has no such module.
        return value.hex()


def change_no(counter: int) -> str:
    return "change #%d" % counter


def count_changes(n: int) -> str:
    return "%d change%s" % (n, "" if n == 1 else "s")


def entry_props(app_id: str, identifier: bytes) -> list:
    """The Domain and Key rows every entry screen opens with."""
    return [
        ("Domain", app_id, False),
        ("Key", display_bytes(identifier), True),
    ]


def require_initialized() -> None:
    """Every WARD request needs a seed."""
    from apps.common.seed import raise_if_not_initialized

    raise_if_not_initialized()


def require_key(app_id: str | None, identifier: bytes | None) -> "tuple[str, bytes]":
    """Validate the (app_id, identifier) pair, before anything is derived, pulled or shown.

    GAP(ward): app_id comes from the wire, so it is a namespace, not a permission.
    """
    from trezor.wire import DataError

    require_initialized()

    if not app_id or not identifier:
        raise DataError("app_id and identifier are required")
    return app_id, identifier


def is_fresh() -> bool:
    """Whether the root reads prove against is the WM's head as of this session.

    True only after this session adopted a head the WM attested against a nonce the device minted
    for it, and the device's root moves only by such an adoption: a proof against it is a proof
    against the WM's current head, not merely against a head that once was.
    """
    from . import round as sync_round

    return sync_round.is_online()


async def add_freshness(props: list) -> None:
    """Append the warning unless the WM attested this session's head (`is_fresh`).

    DATED when the WM's timestamp for the head reads prove against is known (`read_timestamp`):
    the WM held that head then, and nothing since is reflected -- neither a later change, nor a
    revert that discarded it. A head stored before timestamps were kept gets the undated warning.
    """
    if is_fresh():
        return

    from trezor.strings import format_timestamp

    from .root import read_timestamp

    timestamp = await read_timestamp()
    if timestamp is None:
        props.append(WARNING_UNVERIFIED)
    else:
        props.append(
            (
                "Warning",
                "Not reflecting changes since %s UTC, nor user reverts."
                % format_timestamp(timestamp),
                False,
            )
        )


def has_wm() -> bool:
    """Whether this firmware is deployed with a WARD Manager. Not in the MVP build
    (`--ward-without-wm`): a head is then never attested, the stored head is moved by
    `WardCatchUp` along this wallet's own chain, and writes derive from it."""
    return utils.USE_WARD_WM


async def online() -> bool:
    """Whether a WM attestation has been bound to a held tree in THIS session.

    A service build drives one sync attempt itself and raises whatever it failed with; a
    connect build can only report what the host has already done.

    WITHOUT A WM (the MVP) nothing is ever attested, so this means "there is a stored head to
    write on": the host catches the device up (`WardCatchUp`, persisted) first, genesis included.
    """
    from . import round as sync_round

    if not has_wm():
        from .root import get_root

        return await get_root() is not None

    if sync_round.is_online():
        return True

    if not utils.USE_WARD_SERVICE_CHANNEL:
        return False

    from .service import become_ready

    return await become_ready()


async def online_or_offline() -> bool:
    """`online`, but a failed sync answers False. Only for `label`, which may fall back to the
    device's own store and says so on screen."""
    try:
        return await online()
    except Exception:
        return False


def _refused(entry_key: bytes, what: str) -> None:
    """Say on the debug log that a host served a proof against another tree (an older one, say)."""
    from trezor import log

    log.info(
        __name__,
        "read REFUSED: entry=%s: %s does not prove against the trusted root",
        entry_key[:6].hex(),
        what,
    )


async def pull_leaf(
    entry_key: bytes,
    root: "bytes | None" = None,
    staged: "tuple | None" = None,
) -> tuple:
    """Ask the backend for its leaf at `entry_key`, verify it against the trusted root, open it.

    Returns `(content, old_leaf, (proof, witness_entry_key, witness_commit))`: `content` is the
    opened `(entry_type, value)` and `old_leaf` the sealed_content, both None when nothing is
    there. A pointer is returned as it is; `read_entry` follows it. `root`/`staged` are given only
    to prove against a root other than the stored one (a batched flush, a pointer's second hop).
    """
    from trezor.wire import DataError

    from .attest import EMPTY_ROOT
    from .keys import derive_k_data
    from .leaf import check_sealed, is_delete, open_content
    from .root import get_counter
    from .trie import verify_membership, verify_nonmembership

    if utils.USE_WARD_SERVICE_CHANNEL:
        from .service import fetch

        # A batched flush is connect-only; nothing on a service build stages a leaf.
        assert staged is None
        ack = await fetch(entry_key)
    else:
        from trezor.messages import WardEntryAck, WardEntryRequest, WardStagedLeaf
        from trezor.wire import context

        request = WardEntryRequest(entry_key=entry_key)
        if staged is not None:
            request.staged = WardStagedLeaf(entry_key=staged[0], commit=staged[1])
        ack = await context.call(request, expected_type=WardEntryAck)

    sealed = ack.sealed_content
    present = not is_delete(sealed)
    if present:
        check_sealed(sealed)

    # Verified BEFORE opening anything; an absence has to be proved too. No root at counter 0 is
    # a genuinely empty wallet; at a non-zero counter "cannot verify" must never read as
    # "verified". An EMPTY_ROOT tree admits only absence, with no witness needed.
    if root is None:
        from .root import read_root

        root = await read_root()
    if root is None:
        if await get_counter() > 0:
            raise DataError("no trusted root; sync before reading")
    elif root == EMPTY_ROOT:
        if present:
            raise DataError("WARD: the tree is empty; no entry can be in it")
    elif present:
        if not verify_membership(entry_key, sealed, ack.proof, root):
            _refused(entry_key, "the entry")
            raise DataError("WARD: entry does not match the trusted root")
    elif ack.witness_entry_key is None or ack.witness_commit is None:
        raise DataError("WARD: absence claimed without a witness")
    elif not verify_nonmembership(
        entry_key, ack.witness_entry_key, ack.witness_commit, ack.proof, root
    ):
        _refused(entry_key, "its absence")
        raise DataError("WARD: absence does not match the trusted root")

    material = (ack.proof, ack.witness_entry_key, ack.witness_commit)
    if not present:
        return None, None, material

    # The trie binds the sealed content to this path, so a successful open is authenticity.
    entry_type, _c_leaf, value = open_content(await derive_k_data(), sealed)
    return (entry_type, value), sealed, material


async def read_entry(
    app_id: str, identifier: bytes
) -> "tuple[bytes | None, bytes | None]":
    """`(value, target)` for a read of (app_id, identifier), following a pointer ONE hop.

    `target` is the identifier a pointer named, else None; `value` is None when the entry, or the
    pointer's target, is proven absent. Both pulls prove against the same root. A pointer that
    leaves its app_id, or points at another pointer, fails the read.
    """
    from trezor.wire import DataError

    from .keys import ENTRY_TYPE_POINTER, entry_key_for
    from .leaf import unpack_identity

    content = (await pull_leaf(await entry_key_for(app_id, identifier)))[0]
    if content is None:
        return None, None
    entry_type, value = content
    if entry_type != ENTRY_TYPE_POINTER:
        return value, None

    target, target_app, target_device = unpack_identity(value)
    if target_app != app_id.encode():
        raise DataError("WARD: a pointer must stay in its own domain")
    target_key = await entry_key_for(app_id, target, target_device)
    # The pull above may have synced (service builds); the hop proves against the same root.
    from .root import read_root

    hop = (await pull_leaf(target_key, root=await read_root()))[0]
    if hop is None:
        return None, target
    if hop[0] == ENTRY_TYPE_POINTER:
        raise DataError("WARD: a pointer may not point at another pointer")
    return hop[1], target


def display_content(content: "tuple[str, bytes]") -> str:
    """An opened entry as a screen shows it: a pointer names its target."""
    from .keys import ENTRY_TYPE_POINTER
    from .leaf import unpack_identity

    entry_type, value = content
    if entry_type == ENTRY_TYPE_POINTER:
        return "-> " + display_bytes(unpack_identity(value)[0])
    return display_bytes(value)


async def commit_change(
    entry_key: bytes,
    app_id: str,
    identifier: bytes,
    value: "bytes | None",
    old_leaf: "bytes | None",
    material: tuple,
    entry_type: str = "address",
) -> "WardLeafAck | WardMutationApplied":
    """Seal `value` (None: delete), derive the new root from the proven pull, authorise
    `(counter - 1, from_root) -> (counter, new_root)` and hand it on. Called after the screen.

    The leaf is stamped with the counter it lands at (C_leaf). The device DERIVES its new root
    rather than being told one. NOT COMMITTED HERE: the head moves only when a WM attestation
    names this transition and the device re-verifies it. A connect build returns the leaf and
    authorisations; a service build publishes and adopts, returning no leaf -- a replica owner
    reads an empty sealed_content as a deletion.
    """
    from .transition import authorise
    from .keys import derive_k_data, derive_k_ident
    from .leaf import EMPTY, seal_content, seal_identity
    from .root import get_counter, get_root, root_for_write
    from .trie import compute_new_root

    from_root = await get_root()
    counter = await get_counter() + 1
    if value is None:
        sealed_identity = sealed_content = EMPTY
        new_leaf = None
    else:
        sealed_identity = seal_identity(await derive_k_ident(), identifier, app_id)
        sealed_content = seal_content(await derive_k_data(), entry_type, counter, value)
        new_leaf = sealed_content

    # A delete has an old leaf, so it is never an insert and the witness goes unused.
    proof, witness_entry_key, witness_commit = material
    new_root = compute_new_root(
        entry_key,
        old_leaf,
        new_leaf,
        proof,
        root_for_write(from_root),
        witness_entry_key=witness_entry_key,
        witness_commit=witness_commit,
    )
    step, advance = await authorise(counter - 1, from_root, counter, new_root)

    if utils.USE_WARD_SERVICE_CHANNEL:
        from trezor.messages import WardMutationApplied

        from .service import publish

        await publish(
            entry_key,
            sealed_identity,
            sealed_content,
            from_root,
            counter,
            new_root,
            step,
            advance,
        )
        return WardMutationApplied(entry_key=entry_key, counter=counter)

    from trezor.messages import WardLeafAck

    return WardLeafAck(
        entry_key=entry_key,
        sealed_identity=sealed_identity,
        sealed_content=sealed_content,
        counter=counter,
        auth_commit=step,
        wm_sig=advance,
    )
