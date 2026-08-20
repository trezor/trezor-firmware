"""The trie root the device verifies proofs against.

A proof only means something when checked against a root the host did not choose. This
holds that root, PERSISTED per hidden wallet.

The device DERIVES it: every confirmed write recomputes the root from a state the host had
to prove (see `trie.compute_new_root`), so this is a value the device computed, never one
it was handed. There is deliberately no way for the host to set it -- an earlier
`WardDebugSetRoot` existed only while writes could not derive one, and was removed rather
than left as a back door into the one number the whole scheme rests on.

It cannot live in a module global, and that is not a style preference: `trezor.wire` wraps
every request in `utils.unimport_begin()` / `unimport_end()`, which deletes from
`sys.modules` every module the workflow imported. A root stashed in a module attribute is
gone by the time the next request arrives and reads back as "no root" -- i.e. as "cannot
verify", so nothing gets checked. That is the failure direction that hides.

Storage is keyed by wallet_id rather than being one device-wide value, because K_path is
passphrase-dependent: each hidden wallet has its own trie and so its own root. See
`storage.ward` for the slot layout and for what happens when the slots run out.

WHAT A ROOT HERE DOES AND DOES NOT PROVE. Given one, the device can reject a leaf the
host forged, edited, moved between paths, or invented, and can reject a claim of absence
for an entry that exists. It CANNOT tell whether the root itself is current -- a host
that also rolled the device back to an older root would present a perfectly consistent
older world. Only an attested root closes that, so the screens still say so.
"""


async def get_root() -> bytes | None:
    """The trusted root for the active wallet, or None if it has none.

    Callers must treat None as "cannot verify", never as "verified".
    """
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_root(await derive_wallet_id())


async def get_counter() -> int:
    """The anti-rollback floor for the active wallet."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_counter(await derive_wallet_id())


async def set_root(root: bytes | None, counter: int | None = None) -> bool:
    """Record the root the device just adopted. False if there was no slot for this wallet.

    `counter=None` keeps the stored one. Only `reconcile` and `verify_chain` reach here now,
    so every stored head is one a WM attestation named -- which is what made the separately
    stored attested counter redundant.

    An ABSENT root means the empty tree, and is stored as EMPTY_ROOT. No caller ever means
    "forget the root I had", so normalising here rather than at each call site keeps the
    "verifies nothing" state unreachable by omission.

    A FALSE RETURN MUST FAIL THE ADOPTION. It means the wallet has no root slot -- eight are
    protected and this is the ninth -- so the head was verified but not kept. Continuing would
    leave the device online at counter 0 with no root, which `common.verify_leaf_against_root`
    treats as "nothing was ever written" and accepts unproven.
    """
    import storage.ward as ward_store

    from .attest import EMPTY_ROOT
    from .keys import derive_wallet_id

    if root is None:
        root = EMPTY_ROOT
    wallet_id = await derive_wallet_id()
    if counter is None:
        counter = ward_store.get_counter(wallet_id)
    # PROPAGATED, never swallowed: the store refuses a wallet it has no slot for, and a caller
    # that adopted a head without storing it would go on to verify proofs against nothing.
    return ward_store.set_root(wallet_id, root, counter)
