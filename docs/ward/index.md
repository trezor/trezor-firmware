# WARD

WARD lets a Trezor verify wallet data, such as address labels, while a host stores the encrypted
entries. For each passphrase wallet, the device tracks a **head** consisting of a change counter
and a root that commits to the entries.

The MVP authenticates each change against the device's own history. Two writers can produce
competing histories. The manager-backed design adds a [WARD Manager](ward_manager.md) that orders
changes across devices and attests the head it holds.

## Architecture

- [Participants and channels](ward-channels.md)
- [Entry privacy](ward_leaf_encryption.md) and [the authenticated tree](ward-trie.md)
- [A write from approval to adoption](ward_transitions.md#from-approval-to-adoption) and [competing writers](ward_transitions.md#competing-writers)
- [Catching up a second Trezor](ward_manager.md#catching-up-a-second-trezor)
- [Recovery after a manager restore](ward_roll_forward.md)
- [Recovery after data loss in Evolu](ward-trie.md#recovery-after-data-loss-in-evolu)

## Security and use

- [Threat model and accepted limitations](threat_model.md) · [Security gaps](gaps.md)
- [Address labels, offline changes and backup](user_story.md)

## Implementation

- [Implementation plan: firmware, host, online services and Suite](implementation/index.md)
