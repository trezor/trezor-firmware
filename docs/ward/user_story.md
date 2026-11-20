# WARD user stories

What a user expects from WARD, written as stories with acceptance criteria. What each story
reveals, and to whom, follows the [threat model](threat_model.md).

## mini-WARD

The mini-WARD is what the Trezor keeps in its own flash, and can read with no host:

- **Offline copies:** WARD entries the user pinned, such as the label of an address.
- **Pending changes:** writes queued while offline and not yet published to the ward.

It is small, and it exists only on that Trezor. Losing, wiping or replacing the device loses it,
unless it was backed up.

Today the backup is manual. The host exports one record it names (`WardQueueGetEntry`) as a
plaintext blob with an intent MAC, and hands it back to restore it (`WardQueueSetEntry`). The two
policies below replace that.

### 1. Backup policy: automatic

> As a user, I want my mini-WARD backed up without doing anything, so that losing my Trezor does
> not lose my offline copies and my unpublished changes.

Acceptance criteria:

- **No user action.** Every change to the mini-WARD is backed up: a pin, a queued change, an
  erase, a change settling after a flush. The backup is made the next time the Trezor is connected
  to a host with WARD, with no screen and no confirmation.
- **Whole snapshot.** A backup holds the whole mini-WARD, not one named record. A host does not
  need to know an identifier to back it up.
- **Sealed.** The snapshot is sealed with AES-256-GCM under a key derived from the seed. Unlike
  today's manual export, the host cannot read it: a backup made without the user's consent must
  not reveal what a confirmed export would.
- **Bound to the wallet.** Each hidden wallet has its own key and its own backups. A backup of
  one wallet cannot be opened by another.
- **Versioned.** Each snapshot carries a backup counter and the time it was made. The host keeps
  several versions, not only the latest.
- **Never blocking.** A backup that fails, or a host that keeps none, never stops a WARD
  operation. The Trezor records which change was last backed up, so it can say when a backup is
  missing.
- **Reveals to the host:** when the mini-WARD changes, the size of each snapshot, and how many
  versions exist. Not identifiers, values, or the number of entries beyond what the size implies.

### 2. Restore policy: listing and selection on the Trezor

> As a user restoring my wallet onto a new or wiped Trezor, I want to see on the Trezor what a
> backup holds and choose what comes back, so that nothing the host picks lands on my device
> without my seeing it.

Acceptance criteria:

- **The host only offers.** The host sends the backups it holds. The Trezor opens and checks each
  one, and lists only those that open under this wallet's key. A modified backup, or one from
  another wallet, is not listed.
- **Choose a backup.** The Trezor lists the backups by backup counter and time, newest first, and
  the user picks one.
- **Choose the entries.** The Trezor lists the entries of that backup, page by page. Each row
  shows:
    - the domain and the key;
    - the value;
    - whether it is an offline copy or a pending change.

  The user selects all of them, none, or single entries.
- **Confirmed on the Trezor.** Nothing is restored before the user confirms the selection. The
  host cannot add, drop or reorder entries.
- **Restored as what they were:**
    - A pending change comes back pending, with no counter assigned. It is published by the next
      flush, against the head at that time.
    - An offline copy comes back marked as restored, not proven current, until a sync verifies it.
- **Conflicts are shown.** If the Trezor already holds an entry under the same key, the screen
  shows both values, and the user picks one, as the "Replace pending change" screen does today.
- **Capacity.** If the selection does not fit in flash, the Trezor says so before writing
  anything.
- **Reveals to the host:** which backup was chosen and how many entries were restored, from what
  the Trezor sends back. Not which entries, or their values.

## Address labels

### Labels in the signing flow

> As a user sending a transaction, I want the Trezor to show the label I gave each recipient
> address, so that I can recognise who I am paying.

Specified, not implemented: today only `DisplayAddress` shows a label.

Acceptance criteria:

- **On the output screen.** Each external output shows its full address, its amount, and the
  label WARD holds for that address, if any.
- **Mapped by the Trezor.** The Trezor derives the path from the address it is about to show and
  proves the label against its root. The host has no field to supply a label, and cannot attach
  one address's label to another.
- **Provenance shown.** The label says whether it is current, an offline copy, or not proven
  current. With no label, the screen says "No label", so a missing label is visible.
- **Never blocking.** A lookup that fails shows "Label unavailable", and the user still decides
  whether to sign.
- **Change outputs.** Recognised by their derivation path as today. A label does not make an
  output change, or the reverse.
- **No extra confirmations.** Reading a label during signing adds no screen of its own.
- **Reveals to the host:** which output addresses were looked up, and when. It built the
  transaction, so it knows the addresses already.

### Adding a contact while offline

> As a user with no connection to WARD, I want to add a contact on my Trezor now, so that the
> address carries its name right away and the contact reaches my other devices once I am back
> online.

A contact is an entry in the address book domain: the identifier is the address, the value is the
name. Offline, it is written as a pending change (`WardQueueSetEntry`).

Acceptance criteria:

- **Confirmed on the Trezor.** The screen shows the address and the name. If the mini-WARD
  already holds an entry for the address, the screen shows what is replaced.
- **Usable at once.** The pending contact labels the address offline, marked "Label not
  published yet."
- **Kept safe.** The pending change is in the mini-WARD, so the automatic backup covers it
  before it is published.
- **Published without asking again.** The next flush publishes it against the WM's head at that
  time, with no screen: the user confirmed when adding it. It stays pending until the WM accepts
  the transition, so a host that never publishes it loses nothing.
- **Conflicts.** If another device changed the same contact in the meantime, the user resolves
  it on the Trezor; see the next story.
- **Reveals to the host:** nothing while offline. At the flush: one more entry, or a changed one,
  its path and its size.

### Resolving a conflict between entries added offline

> As a user with two Trezors, I want to be asked when both added the same contact differently
> while offline, so that neither name is overwritten without my knowing.

Two devices queue a change to the same entry, each from the state it last synced. The first
flush publishes its change. The second device's change was formed without seeing it: a
conflict.

Implemented on this branch, as below. The stack (`tools/ward_stack.py`) runs it with two devices:
one entry resolved each way.

Acceptance criteria:

- **Detected by the Trezor.** A pending change records the counter of the head it was formed
  on. At the flush, the Trezor pulls the entry and reads its `C_leaf`. If the entry was written
  after that counter, by any device, the change is in conflict. The host does not decide this.
- **No conflict when nothing differs.** If the published value equals the queued one, or the
  entry was not written since, the change settles or is published as today, with no screen.
- **Held back, not published.** A change in conflict is left out of the batch. The other queued
  changes are published as usual.
- **Shown on the Trezor.** For each conflict, the screen shows the domain and key, then:
    - the published value, marked as written by another device, at change #N;
    - the queued value, marked as added offline on this device.

  A delete on either side is shown as "deleted".
- **The user picks:**
    - **Keep mine:** the queued change is published over the other device's.
    - **Keep theirs:** the queued change is dropped, and the published value stays. The
      Trezor keeps it as an offline copy.

  Until the user picks, the change stays pending. It is never resolved automatically, in
  either direction.
- **Restored changes.** A change restored from a backup has no recorded counter, so any
  published value that differs from it is a conflict.
- **Reveals to the host:** that an entry was held back, and its path; then, after the user picks,
  either a transition or none. Not the values.
