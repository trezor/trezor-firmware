# WARD threat model

What WARD protects, from whom, and what each party still learns. The leaf format is specified in
[WARD leaf encryption](ward-leaf.md), and the trie in [WARD trie canonical form](ward-trie.md).

## Parties

| Party | Holds | Trusted for |
| --- | --- | --- |
| Trezor | The seed; every key below | Everything: it is the only party that decides |
| Host | The application connected to the unlocked Trezor, its `wardd`, and `wardd`'s database of transitions | Availability only |
| Evolu relay | Encrypted Evolu messages that carry the transitions between `wardd` instances | Availability only |
| WARD Manager (WM) | Each ward's head `(counter, root)` and head nonce | Ordering and freshness, never content |
| Other Trezors of the wallet | The same seed | As the Trezor |

- The host can talk to the Trezor and ask for anything it can name, so it can ask about any identifier it can guess. It cannot pass a screen the user refuses.
- The Evolu relay and the WM never talk to the Trezor. They see what a host sends them.
- `wardd`'s database at rest, for example a stolen laptop, reveals what the host sees in the table below, minus the reads.
- A host is assumed hostile for integrity and freshness. The user decides what it may see by confirming on the Trezor.

## Keys

Every key comes from the seed, `SLIP21(seed, ["ward", name])`. The seed includes the passphrase, so every hidden wallet has its own keys and its own ward.

| Key | Purpose | Leaves the Trezor |
| --- | --- | --- |
| `K_path` | Computes `entry_key` | Only through the specified key export, after the user confirms |
| `K_ident` | Seals `leaf_identity` | Only through the specified key export, after the user confirms |
| `K_data` | Seals `leaf_content` | Only through the specified key export, after the user confirms |
| `K_sig` | Signs transitions; its Ed25519 public key is the `ward_id` | Never |
| `K_auth` | Authenticates the links between transitions | Never |

## entry_key

```
entry_key = HMAC-SHA256(K_path, "WARD PATH v1" || leaf_identity)
```

The trie path of an entry.

Why a keyed hash:

- **Hides the identifier from storage.** Identifiers are often public: an address, an xpub. An unkeyed hash of one can be found by hashing guesses. Without `K_path`, whoever holds the stored transitions cannot map a path to an identifier, or test whether an address has an entry.
- **Deterministic.** The Trezor derives the path of any identifier on its own, so a lookup is one pull. The host does not need to keep an index.
- **Fixed width and uniform.** Paths are 32 bytes and evenly spread, so the trie stays balanced, and the place of a leaf in the trie tells nothing about its identifier.
- **Separates scopes.** `leaf_identity` includes `device_id` and `app_id`. The same identifier gets a different path per device slot and per application.
- **Binds the identity.** `sealed_identity` stays out of the trie, because a candidate identity is checked by recomputing its HMAC.

What it does not hide:

- **The same entry over time.** An update keeps the path, so anyone who sees the stored transitions can tell which entries change, how often, and when.
- **Guessable identifiers, from the host.** A lookup shows no screen for the path itself, so the host connected to an unlocked Trezor can have it compute the path of any identifier it guesses. Values stay sealed.

## sealed_identity

```
sealed_identity = seal(K_ident, 0x04, leaf_identity)
```

The identity behind a path, stored beside the leaf and not in the trie.

Why it exists:

- **The path is one-way.** Listing a ward, or repairing it, needs the identity of each leaf. Without it, a key holder sees only paths.
- **It is kept out of the trie.** `entry_key` already authenticates it, so a wrong or missing identity is detected by recomputing the HMAC. A host can then replace a bad row without a transition: any read returns a freshly sealed identity.
- **It has its own key.** `K_ident` is a separate capability from `K_data`. Whoever holds only one can list identifiers without reading values, or read values without listing identifiers.
- **Random nonce.** Each seal draws a fresh 12-byte nonce, so two seals of one identity are unlinkable by their bytes.

What it does not hide:

- **Length.** There is no padding, so its size reveals the length of `app_id` plus the identifier.

## sealed_content

```
sealed_content = seal(K_data, 0x02, leaf_content)
leaf_content   = len8(entry_type) || entry_type || C_leaf:u32 || value
```

The leaf itself. The trie commits to `SHA256(0x03 || sealed_content)`.

Why it is built this way:

- **The trie commits to ciphertext.** A host can compute the digest and serve proofs for leaves it cannot open, and the Trezor checks the proof before opening anything.
- **Authenticated encryption.** AES-256-GCM, so a modified leaf fails to open. The trie binds the ciphertext to its path, so a leaf cannot be moved to another path either.
- **Type and counter inside.** `entry_type` and `C_leaf` are sealed. The host cannot tell a pointer from a value, and cannot tell which transition wrote a leaf from the leaf alone.
- **Random nonce.** A rollback or a second Trezor can write the same `(entry_key, C_leaf)` again, so the nonce is never derived from the leaf.

What it does not hide:

- **Length.** There is no padding, so its size reveals the length of the value, and of a pointer's target identity.
- **Deletes.** A delete is an empty `sealed_content` at the path, visible to every party that stores the transition.

## Freshness

The trie proves that a leaf is in a tree. It does not prove the tree is the latest one. The WM does that:

1. The Trezor mints a nonce for the sync.
2. The WM signs its head together with that nonce.
3. The Trezor verifies the signature and adopts the head.

A host cannot replay an earlier attestation, because it does not know the nonce in advance. The Trezor's root moves only through such an adoption.

- **Fresh.** In a WARD session that adopted a WM-attested head, a read is proven against the WM's current head, and the screen shows no warning.
- **Not fresh.** Without the WM, a read is proven against the head the Trezor last adopted, and the screen shows "Not reflecting changes since <timestamp> UTC, nor user reverts.", dated by the WM's signed timestamp for that head. A host that fails the sync on purpose can show only an old value of this ward, and only under that warning.
- **Caught up without the WM.** A host can walk the Trezor forward along the wallet's own chain (`WardCatchUp`), as far as a head the WM once attested. Reads in that session prove against the newer head, under the warning dated by that attestation, and nothing is persisted.
- **Never older.** A head below the stored counter, or a read proved against an older tree, is refused, with or without the WM.
- **Never adopted.** With no stored head, there is nothing to prove against, and the read is refused.

The stored head moves only on a live attestation. [Progress without the WM](#progress-without-the-wm) explains why.

## Progress without the WM

When a sync fails, the Trezor could still move its stored head forward along links that `wardd`
holds. It does not. This section gives the reason and analyses a variant anchored on cached WM
attestations.

### Why links alone never move the stored head

A link is a transition `(c, r) -> (c', r')` with an `auth_commit` under `K_auth`. That proves a
device of this wallet formed it. It does not prove the WM accepted it, or that the WM still stands
on it. `auth_commit` binds only the transition, so a link stays valid forever.

Some genuine links are not on the WM's current line:

- **A lost race.** The Trezor authorises `(c-1, r) -> (c, A)` and publishes it, but another writer
  lands `(c, B)` first. The host keeps the authorisation for `A`.
- **A branch removed by a revert.** The WM's register is restored from 57 to 10, and the user
  holds to confirm `WardRollback` or `WardRejoin`. The links 10 → … → 57 stay genuine.

Suppose a failed sync persisted the furthest head that the links reach. Then a host could do this:

1. Make the sync fail. It always can, because it relays the WM.
2. Serve a Trezor links from its stored head up a branch the WM does not hold: the losing `A`, or
   10 → … → 57 to a Trezor that last synced below 10.
3. The Trezor persists that head.

The results:

- The Trezor stores and shows values that the WM does not hold, in every later session, not just
  this one.
- The counter floor rises above the WM's line. Every later sync fails, because the WM's head no
  longer descends from the stored head, or is below it. Only a `WardRejoin` or `WardRollback`
  brings the Trezor back. The host engineered that hold screen, and it asks the user to discard
  changes that the WM actually holds.
- Writes built on that head lose at the WM.

`ac7c4a19d9` removed exactly this: an archived anchor that raised the persisted counter with no
live attestation, and so undid a confirmed recovery. `WardCatchUp` therefore keeps the walked-to
head for the session only, under the warning. A host can show an old or abandoned value for one
session, but it cannot move the floor.

### Catching up to a cached attestation

`WardCatchUp` goes only as far as the WM once vouched for. `wardd` keeps one verified attestation
per WM head nonce, with the round nonce it was signed over, and replicates it through Evolu with
the links.
While the WM is down, `wardd` names the newest head on its replica's chain that a kept attestation
names, which may be below the replica's head. The Trezor then:

1. Refuses a head below its stored counter.
2. Verifies the attestation's signature over the host-supplied nonce. This is not
   `verify_round_attestation`: it does not need this round's nonce, and it latches nothing.
3. Refuses an attestation whose timestamp is older than the stored head's (the timestamp floor).
4. Walks the links back from the named head to its stored head.
5. Reads from the named head for this session only. Nothing is persisted.

Without the WM, the screen says "Not reflecting changes since <timestamp> UTC, nor user reverts."
The timestamp is the WM's, signed, for the head the read proves against: the caught-up head, or
the stored head, which `adopt` now stores with its timestamp. A head stored before timestamps were
kept shows the undated "Not proven current; may be out of date."

What this adds over links alone:

- **No never-accepted heads.** A lost race, or a head that a host builds from authorisations it
  collected but never published, has no attestation. Every value shown was the ward's state at
  some point.
- **A signed date.** The Trezor has no clock, so it shows the date and the user judges how old
  that is.
- **The timestamp floor.** A Trezor refuses cached attestations whose signed timestamp is earlier
  than the time it stored. Equal timestamps can occur in the same second, and clock or register
  recovery can affect ordering. See [cached catch-up](gaps.md#cached-catch-up-and-proof-views).

What it does not fix:

- **"Was the head" is not "is on the WM's line".** A Trezor that last synced before a regression of
  the WM's register can still be walked up the abandoned branch, as far as the WM attested before
  it regressed. The warning names this: the value does not reflect reverts. This is why the head is
  not persisted by default. Persisting it would raise the floor above the WM's restored head, and the
  Trezor would need a `WardRollback`; see [When the caught-up head is persisted](#when-the-caught-up-head-is-persisted).
- **The host chooses the head.** It can stop at any attested head between the stored head and the
  newest it holds. The date shows how old that is.
- **The timestamp is now security-relevant.** The floor relies on the WM's clock never going
  backwards, including across a restore of its register. The timestamp is in seconds since the
  Unix epoch. A WM that colludes with the host is out of scope either way, because it can sign a
  live attestation for anything.
- **A weaker form of the epoch.** `ac7c4a19d9` leaves a GAP note for a counter epoch that a revert
  bumps and the preimage binds. The epoch needs a wire break and a WM change, but it does not
  depend on a clock.

The service channel on this branch still falls back to the stored head without catching up: it
has no `WardCatchUp` RPC.

### When the caught-up head is persisted

Whether `WardCatchUp` keeps the head it reaches depends on the deployment and, with a WM, on the
user. `WardCatchUpAck.persisted` says which happened.

| Build | User setting | `WardCatchUp` needs | Head |
| --- | --- | --- | --- |
| With a WM (default) | off (default) | a cached attestation, no older than the stored head's | this session only |
| With a WM (default) | on, for this wallet | the same | persisted |
| Without a WM (`--ward-without-wm`, the MVP) | none | the chain alone | persisted |

**Without a WM (the MVP).** There is nothing to attest a head, so the chain is the only authority
and catch-up is how the stored head moves at all:

- The host (`wardd --without-wm`) catches the device up to genesis first, then after every write
  it has stored: its `sync` is that catch-up, and its `flush` stores each change and catches up to
  it. A write derives from the stored head. In place of a `wm_sig` it carries the step signed for
  the host under K_sig (tag `WARD STEP v1`, no head nonce), and `wardd` stores only a step that
  verifies against `ward_id`. The device adopts its own write by catching up one link.
- `WardSync`, and with it every WM route (ingest, reconcile, the chain walk, rejoin, rollback), is
  refused. `WardSetPersistWithoutWm` is refused too.
- Every read shows "Not proven current; may be out of date.": no head is ever attested, so there is
  no timestamp to date it by.
- **What this gives up.** The attack in [Why links alone never move the stored head](#why-links-alone-never-move-the-stored-head)
  is open: a host can persist a lost race, or a branch a revert removed. With no WM there is also no
  compare-and-swap, so two devices writing at once fork the chain, and nothing short of a WM can
  rejoin them. The MVP accepts this until a WM exists.

**With a WM, when the user allows it.** `WardSetPersistWithoutWm` turns persisting on for the active
wallet. Allowing it is held to confirm; withdrawing needs no screen. Persisting still requires the
cached attestation and the timestamp floor. A Trezor that missed a regression of the WM's register
can keep a head on the abandoned branch until recovery with the WM. The timestamp floor also has
the ordering limits described above. The setting is stored per wallet in flash (keys 0x18..),
and enabling it requires the confirmed request.

**Which build a device is cannot be asked over the wire.** The test suite tells them apart by how
the device answers `WardSetPersistWithoutWm` (`ward_wm` marker in `tests/conftest.py`). A host must
not let a device's claim decide what it trusts.

## What each party learns

| | Host | Evolu relay | WM |
| --- | --- | --- | --- |
| Identifiers | Those it names; a path for any it guesses | No | No |
| Values | What the user lets the Trezor show | No | No |
| Entry type | No; a pointer read shows as two pulls | No | No |
| Which entry is read, and when | Yes | No | No |
| Which entry changes, and when | Yes | No | No |
| Number of entries, sizes, deletes | Yes | Message count and sizes | No |
| Transitions: counter, root, batch size | Yes | When one is published | Counter, root and time |
| Ward identity, and when it is used | `ward_id` | The Evolu owner, not the `ward_id` | `ward_id`, once per WARD session |

## Use cases

Each use case states what it expects from WARD and what it reveals beyond the table above.

### Labeling

An application stores a label per address or account, and the Trezor shows it next to the address
(`DisplayAddress`). The identifier is the address or xpub; the value is the label.

- **Expects:**
    - The label shown is the one the user stored, for this address, in this wallet.
    - It is current when the WM attested the session, and marked otherwise:
        - "Label proven current." with the WM;
        - an offline note without it;
        - "No label for this address." when absence is proven.
    - The host cannot supply or suppress a label: there is no wire field for one, and a failed lookup still shows the address.
- **Reveals:**
    - **Host:** the path of each address it asks about. It knows the addresses anyway. It also
      learns the number of labels, their lengths, and when each label changes.
    - **Evolu relay and WM:** nothing about addresses or labels.

### Labels in the signing flow

While signing a transaction, the Trezor looks up the label of each output address and shows it
with the address on the output's confirmation screen. Specified, not implemented: on this branch
only `DisplayAddress` may read labels (`label._CAPABILITIES`).

- **Expects:**
    - The full address is always shown. The label is shown beside it, never instead of it.
    - The label is looked up by the address on the screen, so a substituted address cannot carry
      the label of the intended one. Only the Trezor writes labels, after the user confirmed, so
      a host cannot create a label for its own address.
    - Each label shows its provenance, as with `DisplayAddress`. An address the user expects to
      be labelled showing "No label" is the warning sign.
    - A failed lookup shows "Label unavailable" and signing continues. Labels inform the user;
      they never decide whether a transaction is signed.
    - Change outputs are recognised by their derivation path, not by a label.
- **Reveals:**
    - **Host:** the path of each output address, at signing time. The host built the
      transaction, so it knows the addresses anyway. Pulls in the middle of signing add round
      trips the host can time.
    - **Evolu relay and WM:** nothing more than for `DisplayAddress`.
- **Stale label:** without the WM, a host can serve the device's last head. A label the user has
  since changed or deleted can then appear, under the "not proven current" note.

### Adding a contact while offline

The user adds an address book entry with no host: the identifier is the address, the value is
the name. It is queued in the Trezor's flash (`WardQueueSetEntry`) and published by a later
`WardFlushQueue`.

- **Expects:**
    - The contact is added only after the user confirms its address and name on the Trezor.
    - Until it is published, the address is labelled from the Trezor's own store, marked
      "Label not published yet."
    - The flush re-derives the change against the current head and publishes exactly what was
      confirmed. The host cannot change the address or the name: the pending record is
      authenticated under `K_auth`.
    - The record stays pending until the WM accepts the transition. A host that drops it can
      delay the contact, never lose it.
- **Reveals:**
    - **While offline:** nothing.
    - **At the flush:** the path and size of the entry, and the time. Several queued contacts in
      one batch hide their order.
- **Conflict:** if another device changed the same address in the meantime, the flush asks the
  user; see the next use case. A host cannot cause a conflict, but it can choose when to flush.

### Resolving a conflict between entries added offline

Two Trezors of one wallet queue different values for the same entry while offline. The first
flush publishes; the second device's change was formed without seeing it. The second device's
flush shows both values: "Keep your value?" publishes the queued one; declining it, then holding
"Keep published value?", discards it; declining both leaves it pending.

- **Expects:**
    - The Trezor detects the conflict itself. The pending change records the counter of the
      head it was formed on, and the published leaf carries its `C_leaf`, sealed and proved
      against the root. A host cannot hide a conflict, or invent one, without failing the proof.
    - A change in conflict is held back from the batch and shown on the Trezor with both values.
      The user keeps one; nothing is resolved automatically.
    - Equal values, or an entry not written since, are no conflict and need no screen.
- **Reveals:**
    - **Host:** that a change was held back, and its path, and later whether the user kept it.
      It does not learn either value.
    - **Evolu relay and WM:** a transition if the user keeps the queued value, none otherwise.
- **What the host can still do:** delay the flush. It cannot pick the winner: an older
  published value fails the proof against the Trezor's root, and the user decides.
- **Limit:** the base is the stored counter, so a change queued while an earlier change of the
  same entry from this device was still unconfirmed is shown as a conflict with itself.

### Catching up without the WM

A Trezor whose WM is unreachable, for example a second device joining while the WM is down, is
walked forward by its host along the wallet's chain (`WardCatchUp`).

- **Expects:**
    - The named head carries a WM attestation the host kept from an earlier round, no older than
      the stored head's.
    - Every link is authorised by a device of this wallet, and the walk lands exactly on the
      stored head, so the head is genuine and descends from it.
    - Reads in that session prove against the new head, under "Not reflecting changes since
      <timestamp> UTC, nor user reverts."
    - Nothing is persisted by default: the stored root and counter move only with the WM.
      Persisting would let a host walk a device back up a branch the user discarded with a revert;
      see [Progress without the WM](#progress-without-the-wm). The user may allow it per wallet,
      and a firmware built without a WM always persists; see
      [When the caught-up head is persisted](#when-the-caught-up-head-is-persisted).
    - A head below the stored counter is refused before any link is asked for, and a read proved
      against an older tree fails.
- **Reveals:** nothing beyond the chain and the attestations the host already stores.
- **What the host can still do:** stop short of the newest attested head, or, for a Trezor that
  missed a regression of the WM's register, follow a branch a revert later removed. Both are
  shown with the date of the head they read from.

### Passphrase wallet

A hidden wallet behind a passphrase has its own ward.

- **Expects:**
    - Nothing links two hidden wallets cryptographically. Each has its own keys, its own `ward_id`, and its own Evolu node, which the Trezor derives from the seed.
    - A wrong passphrase opens an empty ward, not an error that confirms the passphrase was wrong.
- **Reveals:**
    - **WM:** one `ward_id` per hidden wallet that uses WARD, and the activity of each. The Evolu relay likewise sees one owner per hidden wallet.
    - **Host:** which ward the session uses, and when. The host connected to the Trezor already sees which session is open.
    - **Anyone correlating timing or network origin:** possibly that several wards belong to one user. WARD does not prevent this.

### Per-device setting

An entry that belongs to one Trezor of the wallet, such as a display preference. `device_id` is the device's slot, 1 to 255, and is part of `leaf_identity`. This is specified but not yet on the wire: this branch writes `device_id` empty.

- **Expects:**
    - Each Trezor reads and writes its own entry, under its own path.
    - The setting of one device cannot be served as another's, because the slot is in the HMAC input.
- **Reveals:**
    - **The number of devices, to the host.** The same setting exists under one path per slot. The host can count paths that are always read and written by a single device. A host that sees each Trezor's pulls can map paths to devices. The Evolu relay and the WM see no paths.
    - **Which device acts.** Writes to a per-device path tell the host which slot wrote, and the slot sizes are visible.

### Read an entry

`WardGetEntry`: the Trezor pulls the leaf, proves it, opens it and shows it. A pointer is followed one hop.

- **Expects:**
    - The value is authentic.
    - The value is current when the session is fresh.
    - An absent entry is proven absent, and is shown differently from an empty value.
    - The user confirms the reveal.
- **Reveals:**
    - **Host:** the path read, and the time. A pointer adds a second pull for its target's path, which links the alias to its target.
    - **WM:** the sync that opened the session, not the read.

### Write, update or delete

`WardSetEntry`, `WardDeleteEntry`: the Trezor derives the new leaf and root, the user confirms, the host stores the transition, and the WM accepts it by compare-and-swap.

- **Expects:**
    - Only the Trezor builds a leaf.
    - The screen names what is replaced.
    - The transition lands only on the head it was built on.
    - A lost race is refused, not merged.
- **Reveals:**
    - **Host:** the path, the sizes, an update versus a delete, and the time.
    - **Evolu relay:** one more encrypted message, and its size.
    - **WM:** one more transition of this ward.

### Pointer

`WardSetPointer`: an alias whose value is the target's `leaf_identity`, in the same `app_id`.

- **Expects:**
    - A read of the alias shows the target's current value against the same root.
    - A pointer cannot leave its domain or chain to another pointer.
    - A deleted target reads as "not found".
- **Reveals:**
    - **When written:** nothing more than a value. The type is sealed, and the size reveals the length of the target's identity.
    - **When read:** the link between the alias's path and the target's path, through the two pulls.

### Offline queue and batch

The `WardQueue*` requests hold changes on the Trezor; `WardFlushQueue` publishes up to `MAX_BATCH` of them as one transition.

- **Expects:**
    - Queued changes stay on the Trezor until flushed.
    - A flush publishes exactly what the user queued, and settles each change once the WM accepts it.
- **Reveals:**
    - **Before the flush:** nothing.
    - **At the flush:** the number of changes, and their paths and sizes, all at once. Batching hides the order and timing of the individual changes.

### Offline copy

`WardPinCachedEntry` keeps a verified value in the Trezor's flash, and `WardQueueGetEntry` reads it with no host.

- **Expects:**
    - A read without any host, marked as an offline copy.
    - A miss is reported as a miss, never as an empty value.
- **Reveals:**
    - **Host:** the pin itself is a read, revealed as a read. Later offline reads reveal nothing.

### Several Trezors of one wallet

Each Trezor syncs to the WM's head at the start of a WARD session, and catches up along the chain.

- **Expects:**
    - Every device ends on the WM's head.
    - A device that diverged is told so, and rejoins only after the user confirms what is discarded.
- **Reveals:**
    - **WM:** syncs from several devices look the same, so it cannot count devices from the protocol. It sees when each session starts.
    - **Host:** which device it is connected to.

### Revert

`WardRollback` restores a verified historical state when the WM's head cannot be served or its
register has regressed.

- **Expects:**
    - The user sees the device and WM counters, the verified target counter, the new counter, and
      how many changes followed the target. They hold to confirm.
    - The WM accepts the revert as its own transition.
- **Reveals:**
    - **WM and host:** that a revert happened, and how far back it went.
- **What the host supplies:** authenticated links with archived WM receipts for the historical
  occurrences, followed by the data needed to serve the restored state. See [verified rollback](gaps.md#verified-rollback).

### Key export and listing

Specified, not implemented on this branch. `WARDExportKeys` releases `K_path`, `K_ident` and `K_data` to the host after the user confirms.

- **Expects:**
    - Only the user can release the keys.
    - The host keeps them in memory only.
    - `K_sig` and `K_auth` never leave, so a host holding the keys still cannot write.
- **Reveals:** everything stored in the ward, to that host, from then on: identifiers, values, entry types and pointer targets.

## Security gaps

See the [security review](gaps.md) for the current findings and status.
