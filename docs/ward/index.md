# WARD

WARD is an authenticated database for each wallet: the Trezor builds and verifies every entry,
a host stores and replicates them, and the WARD Manager orders the changes and attests that a head is current.

- [Leaf encryption](ward-leaf.md): `entry_key`, `sealed_identity` and `sealed_content`.
- [Trie canonical form](ward-trie.md): the trie, its root and its proofs.
- [Who talks to whom](ward-channels.md): the wallet and service channels.
- [Transitions and sessions](ward_transitions.md): the two authorizations of every transition, the WM attestation, and the session that binds a Trezor's WM authorization to its latest sync.
- [WARD Manager](ward_manager.md): its state and API, and how wardd rolls a restored WM forward from the WM's own signed records.
- [Threat model](threat_model.md): what each party learns, per use case.
- [Security gaps](gaps.md): review findings, fixes, and remaining release gates.
- [User stories](user_story.md): what a user expects, starting with the mini-WARD backup and restore.
- [mini-WARD to MVP migration](miniscript_to_mvp.md): carrying on-device records into the replicated store.
- [MVP to WARD Manager migration](mvp_to_final_migration.md): enrolling an existing wallet at its adopted head.
- [Testing](ward_testing.md): setup, every test and the command that runs it, the stack, and testing from a shell.
- [Adversarial testing](ward_adversarial_testing.md): the device against a host or WM that misbehaves on purpose.
