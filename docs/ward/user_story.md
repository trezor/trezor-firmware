# WARD user stories

## Showing an address label

When asked to display an address, the Trezor shows its label with a note that tells the user
whether the label is current. A label proven against the head the manager attested in this session
is marked current. A label proven against an older head, or read from the device's offline copy, is
marked as not checked as current: it was the label once but may have changed since. A local change
not yet published is marked as such. If lookup fails, the Trezor says the label is unavailable and
still displays the address. The caller supplies the address, so the screen alone cannot establish
ownership. Showing labels during transaction signing remains a proposal.

## Keeping a contact while offline

A user can pin a proven label for offline display or queue a new value for later publication.
Discarding a queued change removes the local intent. On reconnect, if the device detects a conflict,
the user can keep the published value, publish the queued one or defer the decision. A matching
later value can settle without another write. See [conflict detection limits](gaps.md#publication-and-reads).

On the wallet channel, several queued edits can be published as one transition. The Trezor verifies
each entry against the root produced by the preceding edit and remembers which transition it
offered. If the host disconnects after publication, the next sync can settle the whole batch when
the device verifies that exact transition. Another writer reaching the same counter is insufficient.

## Backing up local work

A confirmed export gives the host one named offline entry in plaintext. For a pending write, it
includes wallet authentication so a device of the same wallet can recognize the intent on restore.
Restoring the intent requires confirmation. Pinned copies carry no write authorization.

The seed and passphrase recover the wallet keys. Published entries also need the encrypted replica,
and unpublished work needs a surviving local record or an explicit backup. Automatic encrypted
snapshots and on-device selection from them remain proposals.
