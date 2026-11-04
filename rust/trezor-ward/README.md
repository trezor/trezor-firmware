# trezor-ward

Rust library for *Wallet Authenticated Rollback-resistant Dictionary* (WARD): the parts that
both a Trezor device and a host need.

## The trie

`trie` is an authenticated crit-bit tree, a binary radix trie carrying Merkle digests: a map from
fixed-width keys to values, committed to by one digest, the *root*. The host holds the whole map (the **prover**) and answers lookups with
proofs. The device holds only the root (the **verifier**), checks those proofs, and computes the
root a change produces without ever holding the map. Both derive the same roots, because the
tree's shape is a function of the key set alone.

A key is routed by its bits, MSB-first. Every branch tests one bit, its *crit bit*, the first bit
on which the keys below it differ; keys with a 0 there go left, with a 1 right. Branches with a
single child do not exist, so a lookup follows the key's bits from the root and always ends at a
leaf. The key is present exactly when that leaf's key equals it.

### Encodings

`H` is the hash function and `‖` is concatenation. `key` is the key's bytes, `crit_bit` is the
position of the bit the branch splits on, encoded by `BitPos` as a big-endian `u16`, and the
rest are digests. Every operand has a fixed width, so no length prefixes are needed.

```text
leaf   = H(0x00 ‖ key ‖ value_digest)
branch = H(0x01 ‖ crit_bit ‖ left ‖ right)
empty  = H(0x02)                                  the root of the empty map
value  = H(0x03 ‖ bytes)                          any `AsRef<[u8]>` value
```

A value enters the tree only as a digest, which the value type computes (`Hashable`). Every
`AsRef<[u8]>` type is a value under the tagged default, the fourth tag of the namespace; a type
with its own commitment scheme implements `Hashable` itself and may use any digest, since a value
digest never occupies a node position.

### Proofs

A proof is the record of one lookup: the leaf it ended at and the path it took, as one byte
string:

```text
proof = terminal_key ‖ terminal_digest ‖ ( crit_bit ‖ sibling )*     steps leaf-to-root
        zero bytes for the empty map
```

The same proof answers "is `k` present?" for every key `k` whose lookup takes this path: present
if the terminal key is `k`, absent otherwise. The verifier does not take the host's word for
either; it derives the answer from the proof after checking that the path is well formed, that
it is `k`'s own path, and that it folds to the trusted root.

### Verifier

`Proof::verify(root, key)` holds a proof against a trusted root and answers where `key` sits in
that tree as an `Entry`, modelled on the entry API of `HashMap`: `Occupied`, with the value's
digest and the handles `replace` and `remove`, or `Vacant`, with `insert`. Each handle returns
the root the change produces, computed from the old root and the proof alone. Nothing is ever
derived from an unverified proof, and an insert is only reachable from a vacant entry. A value
the host supplies is obtained through `OccupiedEntry::value`, which hands it back only if it
hashes to the digest the proof commits to.

The verifier is `no_std`, allocates nothing, and keeps no state: which root to trust, and
whether one is held at all, is the caller's concern.
