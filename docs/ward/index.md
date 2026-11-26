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
- [Transitions and write sessions](ward_transitions.md)
- [Recovery after a manager restore](ward_roll_forward.md)

## Security and use

- [Threat model and accepted limitations](threat_model.md) · [Security gaps](gaps.md)
- [Address labels, offline changes and backup](user_story.md)
- Proposed upgrades from [mini-WARD to MVP](miniscript_to_mvp.md) and [MVP to a manager](mvp_to_final_migration.md)
- [Verification coverage](ward_testing.md) · [Adversarial checks](ward_adversarial_testing.md)
