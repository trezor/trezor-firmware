from typing import *
from buffer_types import *
WardError: type[Exception]


# rust/src/ward/micropython.rs
def get(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bytes | None:
    """
    Return the value stored under `key` for the given wallet and app,
    or None if there is no such record.
    """


# rust/src/ward/micropython.rs
def next_entry(wallet_id: AnyBytes, app: AnyBytes, cursor: int) -> tuple[int, bytes, bytes] | None:
    """
    Return `(next_cursor, key, value)` of the next record of the given
    wallet and app from `cursor` on, or None if there is none left.
    The cursor is opaque: iteration starts with 0 and continues with
    `next_cursor`. The order of the records is unspecified, and so are
    the results if any store is modified in between.
    """


# rust/src/ward/micropython.rs
def set(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes, value: AnyBytes) -> None:
    """
    Store `value` under `key` for the given wallet and app, replacing an
    existing value in place. Raise WardError if the record does not fit.
    """


# rust/src/ward/micropython.rs
def delete(wallet_id: AnyBytes, app: AnyBytes, key: AnyBytes) -> bool:
    """
    Delete the record stored under `key` for the given wallet and app.
    Return whether a record was deleted.
    """


# rust/src/ward/micropython.rs
def trie_lookup(root: AnyBytes, key: AnyBytes, proof: AnyBytes) -> bytes | None:
    """
    Hold `proof` against the trusted `root` as the lookup path of `key` and
    return the value digest stored under `key`, or None if `key` is absent.
    Raise ValueError if the proof is refused.
    """


# rust/src/ward/micropython.rs
def trie_set(root: AnyBytes, key: AnyBytes, proof: AnyBytes, commit: AnyBytes, present: bool) -> bytes:
    """
    Return the root after storing the value digest `commit` under `key`, held
    against `root` by `proof`: a replacement if `present`, which `key` then
    must be, else an insertion, which `key` must be absent for. Raise
    ValueError if the proof is refused or `key` is not as required.
    """


# rust/src/ward/micropython.rs
def trie_remove(root: AnyBytes, key: AnyBytes, proof: AnyBytes) -> bytes:
    """
    Return the root after removing `key`, which `proof` must show present
    under `root`; the empty root if it was the last entry. Raise ValueError
    otherwise.
    """


# rust/src/ward/micropython.rs
def trie_follow_replace(key: AnyBytes, proof: AnyBytes, commit: AnyBytes, other_key: AnyBytes, other: bytearray) -> None:
    """
    Bring `other`, the proof of `other_key` under the root before `key` was
    replaced with `commit` under `proof`, up to date with that replacement, in
    place. The result is held against the new root before it is used.
    """


# rust/src/ward/micropython.rs
def trie_walk_done(root: AnyBytes, current: AnyBytes | None) -> bool:
    """
    Whether the key-order walk of the tree with `root`, at the entry the full
    proof `current` proves (None: before the first), is over.
    """


# rust/src/ward/micropython.rs
def trie_walk_next_len(root: AnyBytes, current: AnyBytes | None, proof: AnyBytes) -> int:
    """
    The length of the full proof `trie_walk_next` writes for `proof`.
    """


# rust/src/ward/micropython.rs
def trie_walk_next(root: AnyBytes, current: bytearray | None, proof: AnyBytes, buf: bytearray) -> tuple[bytes, bytes]:
    """
    Accept `proof`, full or cut below where it parts from `current`, as the
    entry after `current` (the first entry if None), and write its full proof
    into `buf` of `trie_walk_next_len` bytes. Return the entry's key and value
    digest. Raise ValueError if the proof is refused or out of order.
    """
