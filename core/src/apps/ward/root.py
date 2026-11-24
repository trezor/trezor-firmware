"""The trie root the device verifies proofs against, persisted per hidden wallet in flash (workflow
modules are unimported between requests). Derived from proven state, never set by the host; it
proves leaves against a root, not that the root is current -- only an attestation does that.
"""


async def get_root() -> bytes | None:
    """The trusted root for the active wallet. None means "cannot verify", never "verified"."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_root(await derive_wallet_id())


async def read_root() -> bytes | None:
    """The root a READ proves against: the stored one, or -- in a session with no attested head --
    the head `WardCatchUp` followed this wallet's chain to. Never for a write."""
    from . import round as sync_round

    if not sync_round.is_online():
        caught_up = sync_round.provisional()
        if caught_up is not None:
            return caught_up[1]
    return await get_root()


async def get_timestamp() -> int | None:
    """The WM's timestamp for the stored head; None if it was adopted before one was kept."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_timestamp(await derive_wallet_id())


async def read_timestamp() -> int | None:
    """The WM's timestamp for the head `read_root` names: when the WM reached it."""
    from . import round as sync_round

    if not sync_round.is_online():
        caught_up = sync_round.provisional()
        if caught_up is not None:
            return caught_up[2]
    return await get_timestamp()


def root_for_write(root: bytes | None) -> bytes:
    """The root a write derives from, or refuse. None is never the empty tree, even at counter 0:
    an empty tree accepts an insert with no witness, which would let the host replace the tree."""
    if root is None:
        from trezor.wire import DataError

        raise DataError("WARD: no trusted root; sync before writing")
    return root


async def get_counter() -> int:
    """The anti-rollback floor for the active wallet."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_counter(await derive_wallet_id())


async def set_root(
    root: bytes | None, counter: int | None = None, timestamp: int | None = None
) -> bool:
    """Record an adopted root (None = empty tree); `counter=None` keeps the stored one. False means
    no slot, and the caller MUST fail the adoption: with no stored root leaves go unproven."""
    import storage.ward as ward_store

    from .attest import root_or_empty
    from .keys import derive_wallet_id

    wallet_id = await derive_wallet_id()
    if counter is None:
        counter = ward_store.get_counter(wallet_id)
    return ward_store.set_root(wallet_id, root_or_empty(root), counter, timestamp)
