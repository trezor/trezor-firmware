"""The trie root the device verifies proofs against.

A proof only means something when checked against a root the host did not choose. This
holds that root, PERSISTED per hidden wallet.

The device DERIVES it: every confirmed write recomputes the root from a state the host had
to prove (see `trie.compute_new_root`), so this is a value the device computed, never one
it was handed. There is deliberately no way for the host to set it -- an earlier
`WARDDebugSetRoot` existed only while writes could not derive one, and was removed rather
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


async def get_timestamp() -> int:
    """The last attested time for the active wallet, or 0 if it has never synced."""
    import storage.ward as ward_store

    from .keys import derive_wallet_id

    return ward_store.get_timestamp(await derive_wallet_id())


async def set_root(
    root: bytes | None, counter: int | None = None, timestamp: int | None = None
) -> None:
    """Record the root the device just derived, and optionally a new counter.

    `counter=None` keeps the stored counter, which is what an ordinary write does: the
    device advances the tree without an attestation, so nothing has told it a new counter
    is current. Only the sync round moves the counter, and only ever forward.

    An ABSENT root means the empty tree, and is stored as EMPTY_ROOT. No caller ever means
    "forget the root I had": a delete that empties the tree, a rollback to an empty
    predecessor and a reconcile onto an empty head all describe a state, not the loss of
    one. Normalising here rather than at each of them is deliberate -- this is the only
    function that can write the "verifies nothing" state, so it is the only place that has
    to be got right, and a future caller cannot reintroduce it by omission.
    """
    import storage.ward as ward_store

    from .attest import EMPTY_ROOT
    from .keys import derive_wallet_id

    if root is None:
        root = EMPTY_ROOT
    wallet_id = await derive_wallet_id()
    if counter is None:
        counter = ward_store.get_counter(wallet_id)
    if timestamp is None:
        # An ordinary write does not learn the time -- only an attestation carries one --
        # so it must not clear what the last sync established.
        timestamp = ward_store.get_timestamp(wallet_id)
    ward_store.set_root(wallet_id, root, counter, timestamp)
