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

The verifier is `no_std`, allocates nothing, and keeps no state of its own: which root to
trust, and whether one is held at all, is the caller's concern.

### Walk

`Walk` enumerates the entries of the tree with one root in key order, one proof per entry, so
that the host can neither hide, repeat nor reorder an entry. Keys are ordered as byte strings,
which is the order the tree's leaves have from left to right, so the first entry is the leaf
whose path turns left at every branch, the entry after a given one parts from it at the lowest
branch where it turned left and then turns left all the way down, and the last entry turns left
nowhere, which is how the walk knows it is done without any word from the host.

The walk holds the current entry's full proof. For the next entry the host sends either its
full proof or only the part of its path below the branch where the two entries part
(`Proof::below`), which is a prefix of the full proof's bytes; the walk splices that onto the
steps it already holds, folds the one sibling that changes itself, and holds the result against
the root with `Proof::verify` like any other proof, so every entry comes out as an
`OccupiedEntry`. Over a whole walk the truncated form sends each branch's step once. The walk
allocates nothing: the caller provides the storage for each proof, sized by `Walk::next_len`,
and `Tree::walk` produces exactly what a `Walk` accepts.

```rust
use trezor_ward::trie::{Sha256, Tree, Walk};

let tree: Tree<[u8; 32], Vec<u8>, Sha256> =
    Tree::from_entries([([1; 32], b"one".to_vec()), ([2; 32], b"two".to_vec())]);

// The device holds the root and walks; the host serves one proof per entry.
let mut walk = Walk::new(tree.root());
for (key, value, proof) in tree.walk() {
    let entry = walk.next(&proof).unwrap();
    assert_eq!(entry.key(), key);
    assert_eq!(entry.value(value).unwrap(), value);
}
assert!(walk.is_done());
```

### Prover

`Tree` holds the whole map and keeps every node's digest current. `Tree::from_entries` builds
the canonical tree from scratch; `set` and `remove` maintain it one change at a time along a
deliberately separate code path; and `prove(key)` records the lookup for any key, present or
absent, as a `Proof` whose bytes go to the verifier. The prover needs `std` (feature `use_std`).

```rust
use trezor_ward::trie::{Entry, Sha256, Tree};

// The host holds the map.
let mut tree: Tree<[u8; 32], Vec<u8>, Sha256> = Tree::new();
tree.set([1; 32], b"one".to_vec());
tree.set([2; 32], b"two".to_vec());
let root = tree.root();            // what the device holds
let proof = tree.prove(&[2; 32]);  // what the host sends, together with the value

// The device verifies, reads, and derives the root of the change.
let new_root = match proof.verify(&root, &[2; 32]).unwrap() {
    Entry::Occupied(entry) => {
        assert_eq!(entry.value(b"two").unwrap(), b"two");
        entry.replace(b"deux")
    }
    Entry::Vacant(_) => unreachable!(),
};

// The host applies the same change and arrives at the same root.
tree.set([2; 32], b"deux".to_vec());
assert_eq!(tree.root(), new_root);
```
