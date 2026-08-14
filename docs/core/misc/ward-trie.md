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

internal  = sha256( 0x01 ‖ u16be(split_bit) ‖ left ‖ right )

EMPTY_ROOT = sha256( 0x03 )
           = 084fed08b978af4d7d196a7446a86b58009e636b611db16211b65a9aadff29c5
```

**Every opaque operand is exactly 32 bytes, and that is load-bearing.** `entry_key`,
`commit`, `ward_id`, `mac` and every root are fixed-width. The preimages above concatenate
them with nothing marking the boundary, so a variable width makes the split ambiguous: with
`leaf`, the pair `(K, C)` and the pair `(K ‖ C[0], C[1:])` hash identically, no attack on
SHA-256 required. A non-membership witness is supplied by the host, and the other checks do
not save it — a shifted witness key *differs* from the target and *routes* identically, since
routing reads bits 0..255. A host could therefore pass the target's own **membership** proof
off as proof of **absence**, hiding any present entry on every read. Implementations must
reject wrong-width operands in the hashing primitives themselves rather than at call sites.

The four tags `0x00`–`0x03` are disjoint, so no node can be reinterpreted as a node of
another kind, so a leaf hash can never be passed off as an internal one or the reverse.

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
| 1 | that key's `leaf` hash |
| ≥ 2 | a branch, per the rules below |

A subtree built over keys `K` whose parent branched at bit `p` (with `p = -1` for the root):

1. `split_bit` is the **lowest** bit `b > p` on which `K` splits — i.e. not all keys in `K`
   agree at `b`.
2. `left` is the subtree over `{k ∈ K : addr_bit(k, split_bit) = 0}`, `right` over the keys
   whose bit is 1. Both are non-empty by construction, since `split_bit` is a splitting bit.
**A node's hash does not depend on its depth.** Only `split_bit`, and the two child hashes,
go into the preimage — so a subtree that is re-parented keeps its hash, and a delete may
promote the collapsing sibling unchanged whether it is a leaf or a branch.

An earlier version also committed to `skiplen`, the number of bits jumped over since the
parent branched. That value is a *function of the split bits* a proof already carries
(`skiplen = split_bit − (previous split_bit + 1)`), so the verifier derived it rather than
checking it against anything independent, and committing to it bound nothing. It was
introduced in the same change as `split_bit`, which is why the fix below was originally
credited to both; only `split_bit` was load-bearing.

Removing it deleted a whole class of problem. All three trie bugs this subsystem has had were
artifacts of the depth binding: a delete promoting a re-parented branch unchanged (wrong
then, correct now), an insert refusing to splice above an existing branch, and a sibling
whose *kind* had to be proved because the two kinds re-parented differently.

### The empty tree is a state, not the absence of one

`EMPTY_ROOT` and "this device holds no root" are different things and must not share an
encoding. A device with no root verifies nothing — it has nothing to verify against — so
conflating the two means emptying a tree silently switches verification off. That is
reachable by ordinary use: a wallet holding one entry, deleting it.

An empty tree has exactly one honest answer to any query: nothing is present, and no witness
is needed to say so, because there is no leaf to exhibit.

## Proofs

A proof is a list of 34-byte elements, ordered **leaf-to-root**:

```
element = u16be(split_bit) ‖ sibling(32B)
```

Walking the list in reverse (root-to-leaf), a well-formed proof has `split_bit` strictly
increasing and below 256. That rejects a reordered or relabelled proof before a hash is
computed, and bounds the work: no valid proof exceeds 256 elements however many the sender
supplies.

**Membership** is checked by folding the leaf hash up the proof, placing the running node
left or right according to `addr_bit(entry_key, split_bit)`, and comparing to the trusted
root.

**Non-membership** has no "absent" node to point at, so it exhibits the leaf that already
occupies the path the target would take. Four things must hold, and dropping any one makes
it forgeable:

1. every operand is exactly 32 bytes — see the note under **Hashing**; without this the
   remaining checks are all satisfiable by a witness that is the target with bytes glued on;
2. the witness key differs from the target — otherwise it proves presence;
3. the witness folds up to the trusted root, i.e. it really is in the tree;
4. the witness agrees with the target at **every** bit the proof branches on. Since the shape
   rules above already force those branch points to be increasing with every skipped bit
   accounted for, agreeing at them is agreeing on the whole prefix down to where the paths
   part.

The witness travels as two hashes — its path and its commitment — so serving an absence proof
reveals nothing about the witness's own identifier or value.

## Deletes

Removing a leaf collapses the branch above it; the sibling takes that branch's place, with
the hash the proof already committed to. Nothing else is needed.

That is worth dwelling on, because it used to be the hardest corner here. While a node's hash
committed to its depth, a *branch* sibling's hash went stale the instant it moved up a level
while a *leaf* sibling's did not — so the requester had to declare which kind it was and
prove it, via a decomposition or an `(entry_key, commit)` pair, and refusing to guess from an
omission was itself a fix. All of it was an artifact of the depth binding.

The lesson generalises even though the mechanism is gone: signalling something by *omission*
is not a verifiable statement, and treating it as one was the bug.

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
re-parents the branch immediately below, which needs no fixing up — its hash does not depend
on the depth it now hangs at.

## Host storage: the store's own history

The host keeps **one** table: `entry_key → leaf`, holding the entries that currently exist.
The trie is built over the rows where `isDeleted = false`.

There is no WARD-specific history table, because the store already has one. In Evolu:

- **`evolu_history`** is append-only — `(ownerId, table, id, column, timestamp, value)`, one
  row per column write (`packages/common/src/local-first/Db.ts`). Its own comment notes that
  *"time travel is available when last-write-win isn't desired"*. It is written by
  `applyColumnChange` on every message application, so a freshly synced replica reconstructs
  the full history rather than only current state.
- **There is no hard delete.** `isDeleted` is a *system column* that user tables may not
  redefine, and deleting a row means `update(table, { id, isDeleted: true })`. A deleted row
  and its history both survive.

Two consequences, and they are why this shape was chosen over a WARD-owned log:

**The membership rule is the store's, not ours.** "Build the trie over rows with
`isDeleted = false`" is the same filter every other consumer of that store applies. A
WARD-specific rule — *"a row with an empty content part is not a leaf"* — would be a second,
private rule that can disagree with the first. The device's empty-parts leaf (`WardLeafAck`
with both parts empty) is the **signal to set the flag**, never an independent test for tree
membership.

**The tombstone is not a WARD decision.** The store retains history however we encode a
delete, so choosing "no tombstone" only ever hid past entries from a party seeing current
state alone. Reclaiming that privacy would have to happen at the store layer.

### Sweeping to a past state

Replay reconstructs the tree at any counter, which is what lets a second device catch up and
what lets a replica rebuild after losing its materialised state. Two requirements:

- **The counter must be a column on the row.** History is ordered by the store's own logical
  clock, and once two devices write, that order is not the WARD counter's order. "State at
  counter *N*" means, per row, the latest history value whose counter ≤ *N*.
- **Rows carry full sealed leaves, not diffs.** Replay must reconstruct each live leaf's
  `commit`, which is computed over the encoded parts. `isDeleted` is itself a column with
  history, so replay knows whether a row was deleted at counter *N* without anything extra.

### What replay does and does not prove

It detects that the replica is **missing something**: counters must be contiguous up to the
WM-attested counter. That is worth having, because an eventually-consistent store gives no
completeness signal of its own — "I have everything" and "I am still missing rows" are the
same observation.

It proves nothing about **authenticity or currency**. The history is the host's own record; a
malicious host can write a self-consistent one. The anchors are unchanged and both live
outside the store: the `mac`, which only a seed-holding device can compute, and the WM's
attestation of `(counter, mac)`. So replay narrows the device's role from *the only
completeness oracle* to *the authority on currency* — see the note in `apps/ward/common.py`.

### Open

`evolu_history` is an internal table with no exported history API. Reading it from the
application — raw SQL against the local database — needs confirming before the host code is
written. If it turns out to be inaccessible, a WARD-owned append-only log comes back, with the
counter, the sealed leaf and the `auth_commit` per row.

## Conformance

Two artefacts back this document.

**`core/tests/test_apps.ward.canonicity.py`** — a differential test run by `make test`. It
drives randomised operation sequences through the firmware's incremental deriver and asserts
after **every** operation that the result equals a from-scratch rebuild
(`core/tests/ward_trie_model.py`, this specification transcribed into deliberately naive
code).

Geometry matters far more than operation count, which was measured rather than assumed: a
sweep of 2880 operations over random keys never reached a `split_bit` above 8 — and depth is
what every known bug turned on, since all of them were about a node moving between levels. So
the test runs four key geometries, and **fails** if the sweep stops reaching the deep shapes
rather than merely reporting that it did not:

| geometry | what it forces |
|---|---|
| `random` | what real `entry_key`s are — HMAC outputs. Shallow, `split_bit` ≤ 8 |
| `shared_prefix` | keys agreeing on 160 bits: deep branches, `split_bit` up to ~168 |
| `ladder` | key *i* is *i* leading 1-bits: a compressed run at every level, and branch siblings throughout |
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
