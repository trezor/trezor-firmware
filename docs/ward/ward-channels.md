# Participants and channels

| Participant | Responsibility |
| --- | --- |
| Wallet application | Requests an action on the unlocked wallet's connection. |
| Trezor | Holds wallet keys and the adopted head, verifies proofs and authorizes changes. |
| Local service (wardd) | Maintains the replica, serves proofs and coordinates publication and recovery. |
| Evolu replication service | Distributes encrypted replica data among hosts. |
| WARD Manager | Orders wallet-authorized changes and attests its current head. The MVP runs without it. |

## Wallet channel

The wallet application relays exchanges between the Trezor and wardd on one device session.
On the paired Trezor Host Protocol, the user grants one host the WARD application role. Replacing
its pinned key requires a held confirmation. On older transports the device cannot identify the
host and asks before revealing stored values in ordinary entry operations. See the
[display exceptions](gaps.md#access-and-display).

The local service listens on loopback, checks browser origins and requires a client pairing token.
A separate WARD credential grants access to the replicated wallet store. The
[threat model](threat_model.md#accepted-security-limitations) describes the trust placed in the selected endpoint.

## Dedicated service channel

In this deprecated configuration, the application requests an action and the Trezor contacts wardd
directly on a separate interface. A paired service transport pins the first service host's key.
An identity-free transport relies on control of the interface. Both require a manager.
