# The WARD trie: canonical form

WARD stores each entry as a leaf in a path-compressed binary trie, keyed by an opaque
32-byte `entry_key`. The device holds only the **root**; the host holds the tree and serves
proofs. This document specifies the tree's canonical form, which every implementation must
agree on to the byte.

## Why this document exists

The device **derives** each new root from the previous one plus a proof
(`apps.ward.trie.compute_new_root`) and **verifies** by reconstructing a single path. It
never rebuilds the tree. A host, a second device, or a batch path rebuilds from the key set.

Those two ways of arriving at a root must produce the same number, and nothing inside the
device can check that they do: reconstruction along one path stays perfectly self-consistent
inside a locally-wrong tree. A device whose root has drifted verifies its own proofs happily,
and the disagreement only surfaces when some other party recomputes — at which point every
proof is refused and the entry set is unreachable.

Every trie bug found in this subsystem so far has been a disagreement of exactly this kind:

- the reference implementation promoted a re-parented **branch** sibling's hash unchanged on
  delete, which is non-canonical whenever the sibling is a branch;
- the reference implementation rejected an insert whose split point fell **above** an
  existing branch, inside a compressed run;
- this implementation let a delete signal "the sibling is a leaf" by **omitting** the
  decomposition — unverifiable, and a host that withheld it for a branch steered the device
  to a non-canonical root.

None of the three was a cryptographic weakness: no entry can be forged or altered, because
the AEAD seal and the keyed path are untouched. All three wedge the wallet. That is the
failure mode this specification exists to prevent.

## Hashing

All hashes are SHA-256. `len8`/`len32` are unsigned big-endian length prefixes of that width;
`u16be` is an unsigned 16-bit big-endian integer.

```
part      = encoding(1B) ‖ len8(nonce) ‖ nonce ‖ len8(tag) ‖ tag ‖ len32(body) ‖ body
            encoding: 0 = encrypted, 1 = plaintext

commit    = sha256( 0x02 ‖ len8(key_type) ‖ key_type
                         ‖ len32(id_part)  ‖ id_part
                         ‖ len32(val_part) ‖ val_part )

leaf      = sha256( 0x00 ‖ entry_key ‖ commit )

internal  = sha256( 0x01 ‖ u16be(split_bit) ‖ u16be(skiplen) ‖ left ‖ right )

EMPTY_ROOT = sha256( 0x03 )
           = 084fed08b978af4d7d196a7446a86b58009e636b611db16211b65a9aadff29c5
```

The four tags `0x00`–`0x03` are disjoint, so no node can be reinterpreted as a node of
another kind. That is load-bearing rather than tidy: a delete proves its sibling is a leaf by
recomputing the leaf hash from `(entry_key, commit)` and matching the hash the proof
committed to, which is only sound because a branch preimage can never produce it.

`commit` is over the **encoded parts**, not the plaintext value. That is what lets a host
serve proofs for entries it cannot read.

## Bit order

Bits are numbered MSB-first over the `entry_key`: bit 0 is the top bit of byte 0.

```
addr_bit(entry_key, b) = (entry_key[b // 8] >> (7 - (b % 8))) & 1
```

`entry_key` is 32 bytes, so bit indices run 0..255.

## Structure

For a key set `S`:

| `|S|` | root |
|---|---|
| 0 | `EMPTY_ROOT` — **never** an absent value; see below |
| 1 | that key's `leaf` hash. A leaf has no `skiplen` |
| ≥ 2 | a branch, per the rules below |

A subtree built over keys `K` whose parent branched at bit `p` (with `p = -1` for the root):

1. `split_bit` is the **lowest** bit `b > p` on which `K` splits — i.e. not all keys in `K`
   agree at `b`.
2. `left` is the subtree over `{k ∈ K : addr_bit(k, split_bit) = 0}`, `right` over the keys
   whose bit is 1. Both are non-empty by construction, since `split_bit` is a splitting bit.
3. `skiplen = split_bit - (p + 1)` — the number of bits jumped over since the parent
   branched.

Rule 3 is where the bugs live. **A node's `skiplen` is relative to its parent, so it is stale
the instant the node is re-parented.** A delete collapses the branch above the removed leaf
and moves the sibling up a level; a branch sibling's hash therefore cannot be reused, and
must be recomputed at the shallower depth. A leaf sibling has no `skiplen` and does move
unchanged — but that is a fact the verifier must *establish*, not assume (see "Deletes"
below).

### The empty tree is a state, not the absence of one

`EMPTY_ROOT` and "this device holds no root" are different things and must not share an
encoding. A device with no root verifies nothing — it has nothing to verify against — so
conflating the two means emptying a tree silently switches verification off. That is
reachable by ordinary use: a wallet holding one entry, deleting it.

An empty tree has exactly one honest answer to any query: nothing is present, and no witness
is needed to say so, because there is no leaf to exhibit.

## Proofs

A proof is a list of 36-byte elements, ordered **leaf-to-root**:

```
element = u16be(split_bit) ‖ u16be(skiplen) ‖ sibling(32B)
```

Walking the list in reverse (root-to-leaf), a well-formed proof satisfies:

- `split_bit` strictly increases, and stays below 256;
- `skiplen` exactly accounts for the bits jumped since the previous element:
  `skiplen == split_bit - start_bit`, where `start_bit` is the previous `split_bit + 1` and 0
  at the root.

These two constraints make a proof's internal geometry self-consistent, so a reordered,
truncated or relabelled proof is rejected before a hash is computed. They also bound the
work: no valid proof exceeds 256 elements however many the sender supplies.

**Membership** is checked by folding the leaf hash up the proof, placing the running node
left or right according to `addr_bit(entry_key, split_bit)`, and comparing to the trusted
root.

**Non-membership** has no "absent" node to point at, so it exhibits the leaf that already
occupies the path the target would take. Three things must hold, and dropping any one makes
it forgeable:

1. the witness key differs from the target — otherwise it proves presence;
2. the witness folds up to the trusted root, i.e. it really is in the tree;
3. the witness agrees with the target at **every** bit the proof branches on. Since the shape
   rules above already force those branch points to be increasing with every skipped bit
   accounted for, agreeing at them is agreeing on the whole prefix down to where the paths
   part.

The witness travels as two hashes — its path and its commitment — so serving an absence proof
reveals nothing about the witness's own identifier or value.

## Deletes

Removing a leaf collapses the branch above it; the sibling takes that branch's place. The
proof carries only the sibling's **hash**, which does not say whether it is a leaf or a
branch, so the party requesting the delete must say **and prove** which it is. Exactly one of:

- **branch**: `(split_bit, left, right)`. The verifier checks
  `internal(split_bit, split_bit - (collapsing_split + 1), left, right)` equals the committed
  sibling hash, then re-hashes at the shallower depth, absorbing the collapsed branch's own
  `skiplen` plus the collapsed level:
  `skiplen' = split_bit - (collapsing_split + 1) + collapsing_skiplen + 1`.
- **leaf**: `(entry_key, commit)`. The verifier recomputes `leaf(entry_key, commit)` and
  requires it to equal the committed sibling hash. It then promotes unchanged — correct
  precisely *because* it has been established to be a leaf.

Supplying neither, or both, is refused. Signalling a leaf by omission is not a verifiable
statement, and it was a bug.

If the removed leaf was the only one, the proof is empty and the new root is `EMPTY_ROOT`.

## Inserts

An insert must exhibit a non-membership witness (above), except into an empty tree — where
there is nothing to witness and the verifier's own record that the tree is empty is the only
authority accepted.

The split point is computed by the **verifier**, never taken from the requester: it is the
first bit at which the new key and the witness differ. A requester-chosen value would let an
entry be grafted somewhere structurally inconsistent with the rest of the tree.

That split point is **not** necessarily below every branch on the witness's path. Path
compression means the two keys are only compared at the bits the tree actually branches on,
so they can agree at all of those and still part *inside* a compressed run — i.e. above an
existing branch. For a random key that is the ordinary case, not a corner one. Splicing there
re-parents the branch immediately below, whose `skiplen` must be restated:
`skiplen' = its_split_bit - (new_split_bit + 1)`.

## Conformance

Two artefacts back this document.

**`core/tests/test_apps.ward.canonicity.py`** — a differential test run by `make test`. It
drives randomised operation sequences through the firmware's incremental deriver and asserts
after **every** operation that the result equals a from-scratch rebuild
(`core/tests/ward_trie_model.py`, this specification transcribed into deliberately naive
code).

Geometry matters far more than operation count, which was measured rather than assumed: a
sweep of 2880 operations over random keys never reached a `split_bit` above 8 or a `skiplen`
above 2, with 86% of proof elements at `skiplen` 0 — and `skiplen` is the quantity behind
every known bug. So the test runs four key geometries, and **fails** if the sweep stops
reaching the hard shapes rather than merely reporting that it did not:

| geometry | what it forces |
|---|---|
| `random` | what real `entry_key`s are — HMAC outputs. Shallow, `skiplen` ≈ 0 |
| `shared_prefix` | keys agreeing on 160 bits: deep branches, `skiplen` up to ~164 |
| `ladder` | key *i* is *i* leading 1-bits: a compressed run at every level, and mostly branch siblings |
| `mixed` | both at once |

Each trial also **drains** the tree to empty one leaf at a time and then writes again, since
last-leaf deletes and the empty-tree-is-writable case are not reached by random operation
mixes at all.

**`common/tests/fixtures/ward/trie_canonicity.json`** — a fixed, diffable operation script
with the canonical root after each step, for implementations that are not this firmware.
Replay it in order and compare. Regenerate or verify with
`core/tools/ward_trie_fixture.py [--check]`; the generator writes nothing unless the deriver
and the rebuilder agree, and refuses to write a fixture that does not exercise all three
delete-sibling kinds. It is not wired into CI — run `--check` by hand until a second
implementation consumes it.

## What canonicity does and does not buy

A host cannot use non-canonicity to attack the device. Roots are either derived by the device
or adopted under a MAC only a seed-holding device can produce, and a leaf placed on the wrong
side of a branch becomes unprovable — a query for it descends by its own bits and reconstructs
to a different root. Suppressing it would still require a valid witness occupying that path,
which requires the tree to genuinely hold one.

What canonicity buys is that independent implementations agree, and therefore that the wallet
keeps working. It is an availability property, and it is the one that has actually broken.
