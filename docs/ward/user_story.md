# WARD user stories

## Showing an address label

When asked to display an address, the Trezor can show its label and the source of that label. If
lookup fails, it still displays the address. The caller supplies the address, so the screen alone
cannot establish ownership. Showing labels during transaction signing remains a proposal.

## Keeping a contact while offline

A user can pin a proven label for offline display or queue a new value for later publication.
Discarding a queued change removes the local intent. On reconnect, if the device detects a conflict,
the user can keep the published value, publish the queued one or defer the decision. A matching
later value can settle without another write. See [conflict detection limits](gaps.md#publication-and-reads).

## Backing up local work

A confirmed export gives the host one named offline entry in plaintext. For a pending write, it
includes wallet authentication so a device of the same wallet can recognize the intent on restore.
Restoring the intent requires confirmation. Pinned copies carry no write authorization.

The seed and passphrase recover the wallet keys. Published entries also need the encrypted replica,
and unpublished work needs a surviving local record or an explicit backup. Automatic encrypted
snapshots and on-device selection from them remain proposals.
