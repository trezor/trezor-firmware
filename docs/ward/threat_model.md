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

A user can allow the device to persist a cached, attested head while the manager is unavailable.
If the device missed a revert, it can advance along a discarded branch and require recovery.
An entry proof establishes what the wallet stored, including a label its author may have entered incorrectly.

## What each party learns

| Party | Visible information |
| --- | --- |
| Wallet application | Its requests, supplied identifiers and values, and outcomes. Ordinary reads display the value on the Trezor. A confirmed offline export gives the host plaintext it can retain. |
| Local service and peers with replica access | Encrypted entries and identities, stable paths, sizes and history. A host observing a lookup can associate a known or guessed identifier with its path. |
| Evolu relay | Encrypted replication traffic, timing and volume. |
| WARD Manager | The wallet's stable public identifier, counters, roots and session timing. |

## Accepted security limitations

- **Freshness on screen.** A head was current when the manager signed. Another writer can advance
  it before the next read. Signing a write clears the device's freshness indication. On the wallet
  channel, detecting a manager regression can leave an earlier “current” label visible if recovery stops.
- **Application and relay authority.** The caller chooses the namespace, so a paired WARD host can
  request another application's entries. Connect also accepts a caller-selected endpoint that can
  receive the replica credential and request device operations beyond the selected WARD action.
  Device confirmation requirements still apply.
- **Production ordering.** Ordering requires a trusted manager that persists a head before attesting
  it. The development manager can expose a head before its save completes. Release devices lack a
  provisioned manager key and reject attestations.
- **Recovery completeness.** A host can withhold accepted changes after a manager restore or choose
  among genuine branches after repeated restores. A Trezor with a higher stored counter can detect
  regression. A replacement device can accept the older head as current.

Additional [security gaps](gaps.md) affect publication, display and availability.
