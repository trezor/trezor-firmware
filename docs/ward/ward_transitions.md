# Transitions and sessions

A transition identifies the wallet and its starting and resulting heads. 
The counter advances by the number of changes. -- This should be verified for batch updates and 

The manager accepts one successor per head, so along its history each counter names one state. A lost race, a manager restored from backup, or the MVP without a manager can still produce different roots at the same counter; the root tells them apart.

## From approval to adoption

1. **Prepare.** The Trezor verifies the existing entry or its absence. For an ordinary write, the
   user sees the proposed value and what it replaces. A queued write uses the previously approved
   intent and checks for conflicts.
2. **Authorize.** The device derives the new root and authenticates the transition twice. A wallet
   authentication tag lets another Trezor verify the history later. A public signature authorizes
   publication and, with a manager, binds it to the active write session.
3. **Publish.** The service stores the encrypted changes. In the MVP it verifies the wallet
   signature. With a manager, the manager must also accept the transition from its current head.
4. **Adopt.** On sync the device verifies the resulting head. A missed publication response can
   leave the device behind. A queued change can settle once the device verifies it landed.

## Sessions

The Trezor signs the manager's single-use challenge and its own fresh nonce. The manager verifies
the signature, consumes the challenge and replaces the wallet's previous write session. A read-only
attestation leaves the active session in place.

A delayed write can land while both its session and predecessor remain current, even after the
device disconnects. A write displaced by another session or a competing change requires a new sync.


## Competing writers

For a live write, a wallet-authenticated retry token binds the original approval to the proposed
change and the entry's previous write counter. After sync the device can retry without another
approval if that counter matches. If the counter differs, an entry already holding the intended
result needs no write. A different result requires a user decision.

Device on a competing branch requires proof of descent from its own head. A higher counter alone is insufficient.
