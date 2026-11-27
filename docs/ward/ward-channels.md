# Participants and channels

| Participant | Responsibility |
| --- | --- |
| Wallet application | Requests an action on the unlocked wallet's connection. |
| Trezor | Holds wallet keys and the adopted head, verifies proofs and authorizes changes. |
| Local service (wardd) | Stores WARD records in a local Evolu database, serves proofs and coordinates publication and recovery. |
| Evolu replication service | Relays encrypted changes between hosts. Each host rebuilds its own tree. |
| WARD Manager | Keeps the current head and predecessor per wallet, orders changes and attests that head. The MVP runs without it. |

## Wallet channel

The wallet application relays exchanges between the Trezor and wardd on one device session.
On the paired Trezor Host Protocol, the user grants one host the WARD application role. Replacing
its pinned key requires a held confirmation. On older transports the device cannot identify the
host and asks before revealing stored values in ordinary entry operations.

The local service listens on loopback, checks browser origins and requires a client pairing token.
A separate WARD credential grants access to the replicated wallet store. 

## Dedicated service channel

In this configuration, the application requests an action and the Trezor contacts wardd
directly on a separate interface without host wallet mediation. 
