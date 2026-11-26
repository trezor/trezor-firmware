# WARD threat model

WARD trusts the Trezor to protect wallet keys, verify proofs and display the user's choices. Devices
with the same seed and passphrase share authority. A host can delay publication or withhold data.
Even with a manager's signature, ordinary adoption requires wallet-authorized history consistent
with the device's stored head.

## What a verified read means

| Source | What the device knows |
| --- | --- |
| Live manager sync | The manager attested the head in this sync, and the device verified its wallet history. |
| Cached manager attestation | The manager held this head at the signed time. Later changes and reverts may be missing. By default the head is used only for reads in this session. |
| Manager-free MVP | The device verified and persisted a chain from its own head. The replica may omit a later change or a competing branch. |
| Local record | A pinned copy reflects the last value saved on this Trezor. A pending change may still be unpublished. |

TBC: 
A user can allow the device to persist a cached, attested head while the manager is unavailable.
If the device missed a revert, it can advance along a discarded branch and require recovery.

## What each party learns

| Party | Visible information |
| --- | --- |
| Wallet application | Its requests, supplied identifiers and values, and outcomes. Offline export gives the host plaintext it can retain -> encryption at rest guarantees, not "in motion" |
| Local service and peers with replica access | Encrypted entries and identities, stable paths, sizes and history. A host observing a lookup can associate a known or guessed identifier with its path. |
| Evolu relay | Encrypted replication traffic, timing and volume. |
| WARD Manager | The wallet's stable public identifier, counters, roots and session timing. |

## Accepted security limitations

- **Freshness on screen.** There are no guarantees on freshness while working on multiple devices and hosts in parallel. 
- **Recovery completeness.** A host can withhold accepted changes after a manager restore or choose
  among genuine branches after repeated restores. A Trezor with a higher stored counter can detect
  regression. A replacement device can accept the older head as current.
