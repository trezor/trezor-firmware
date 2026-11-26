# Proposed migration from MVP to a WARD Manager

Manager enrollment currently starts at the empty wallet. For an existing MVP wallet, the proposed
handover preserves its entries, counter and pending work. Manager ordering starts at the imported
checkpoint.

1. Trusted upgrade information identifies the existing writer's locally adopted head. The replica
   reconstructs that head and verifies it can serve the entries. Missing history delays migration.
2. The Trezor authorizes one-time enrollment of that checkpoint with the intended manager. After
   durable enrollment, a fresh attestation lets the device confirm adoption. Retrying after
   interruption must converge on the same enrollment, and adoption must survive downgrade.
3. Other devices verify descent from their own heads. The manager cannot retroactively choose
   between competing MVP histories. Divergent entries and queued work must survive until the user
   resolves the conflict.

Cutover must prevent a blank device from enrolling the wallet at genesis before its writer imports
the checkpoint.
