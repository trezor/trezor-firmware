"""The trie root the device verifies proofs against, persisted per hidden wallet.

The device derives it from proven state (`trie.compute_new_root`); the host can never set it.
It lives in flash, not a module global, because `trezor.wire` unimports workflow modules
between requests and a lost root would read as "cannot verify". It proves leaves against a
root, not that the root is current -- only an attestation does that.
"""


async def get_root() -> bytes | None:
    """The trusted root for the active wallet. None means "cannot verify", never "verified"."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_root(await derive_wallet_id())


def root_for_write(root: bytes | None) -> bytes:
    """The root a write derives from, or refuse.

    None is never read as the empty tree, even at counter 0: an empty tree accepts an insert
    with no witness, so that reading would let the host replace the tree.
    """
    if root is None:
        from trezor.wire import DataError

        raise DataError("WARD: no trusted root; sync before writing")
    return root


async def get_counter() -> int:
    """The anti-rollback floor for the active wallet."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_counter(await derive_wallet_id())


async def set_root(root: bytes | None, counter: int | None = None) -> bool:
    """Record an adopted root (None = empty tree); `counter=None` keeps the stored one.

    False means the wallet has no slot, and the caller MUST fail the adoption: an online
    device with no stored root accepts leaves unproven.
    """
    import storage.ward as ward_store

    from .attest import EMPTY_ROOT
    from .keys import derive_wallet_id

    if root is None:
        root = EMPTY_ROOT
    wallet_id = await derive_wallet_id()
    if counter is None:
        counter = ward_store.get_counter(wallet_id)
    return ward_store.set_root(wallet_id, root, counter)
