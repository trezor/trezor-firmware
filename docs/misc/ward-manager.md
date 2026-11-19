# WARD Manager 

The encrypted WARD Manager is a REST service.
It stores each ward's authoritative head transition. 
It signs freshness attestations and accepted commits with Ed25519. 



## Transition

A transition is one wallet-authorized step of a ward from one head to the
next. It names the predecessor head it builds on, the successor checkpoint it
produces, and whether it is a normal commit or a revert. The device authorizes
it and the wallet key signs it, so the manager can verify it but cannot forge
or alter it.

The manager accepts transitions in order. Each accepted transition becomes the
ward's head, and the manager stores the latest one. A ward at genesis has no
accepted transition: its head is counter 0, an empty root, and no MAC.

Both API calls carry a transition as a `transition` JSON object. 
The commit request supplies a proposed one, and the attest response returns the latest accepted one.

| JSON field | Meaning |
| --- | --- |
| `wardId` | Wallet public key used to verify the transition signature. |
| `fromCounter`, `fromRoot` | Counter, and root of the predecessor head. |
| `counter`, `root`, `mac` | Successor checkpoint. The counter must equal `fromCounter + 1` and the MAC must be nonzero. |
| `authCommit` | Device-produced [HMAC](#transition-authorization-authcommit) authorizing the step: `AuthCommit` for a commit, `AuthRevert` for a revert. |
| `signature` | Wallet's Ed25519 signature over the [transition bytes](#signed-bytes). |
| `kind` |  `commit` or `revert`  |

### Transition authorization (`authCommit`)

`authCommit` is an HMAC-SHA256 that the device computes when it performs a
batch or a revert 

```text
AuthCommit = HMAC-SHA256(K_auth, "WARD COMMIT v1" || wardId || fromCounter:u32
                         || fromRoot || counter:u32 || root)
AuthRevert = HMAC-SHA256(K_auth, "WARD REVERT v1" || wardId || fromCounter:u32
                         || fromRoot || counter:u32 || root)
```


The MAC covers only the step: the counters and roots on both sides. It does
not cover `mac` or `kind`; the tag string separates a commit from a revert.

The manager cannot verify `authCommit` and stores it opaquely. 
It authenticates the request with the wallet `signature`, which covers
`authCommit`. Another device of the same wallet verifies `authCommit` when it
walks the chain from its trusted anchor to the attested head
(`verify_chain_step()`), so a manager cannot introduce a step that no device
of the wallet authorized. 

## HTTP API specification

| Call | Purpose |
| --- | --- |
| `POST /ward/attest` | Obtain the latest accepted transition with a challenge-bound signature that it is the current head. |
| `POST /ward/commit` | Advance the checkpoint using a wallet-signed transition and obtain the manager's signature over the accepted transition. |

### `POST /ward/attest`

| JSON field | Meaning |
| --- | --- |
| `wardId` | Required. Wallet public key that identifies the ward. |
| `nonce` | Required. Caller's 32-byte challenge, bound into the attestation signature. |

The response is the ward's latest accepted transition, with a manager
attestation that it is still the head.

| JSON field | Meaning |
| --- | --- |
| `wardId` | Ward the response is for. |
| `transition` | Latest accepted [transition](#transition). Its `counter`, `root`, and `mac` are the current head. Absent at genesis, where the head is counter 0, an empty root, and no MAC. |
| `nonce` | Nonce provided by Trezor as attestation challenge. |
| `timestamp` | Attestation time: the greater of the current Unix time and the stored head timestamp. |
| `signature` | Manager's Ed25519 signature over the [attestation bytes](#signed-bytes), bound to the caller's `nonce`. |

`WardManager.attest()` reads the stored head and its transition and leaves
the database unchanged. The wallet signature inside `transition` lets the
device check the transition's authorization; the manager signature proves that
it is still the head. During wallet-relayed sync, `wardd` forwards both to the
device in `WARDIngestAttestation`.

### `POST /ward/commit`

| JSON field | Meaning |
| --- | --- |
| `transition` | Required. The proposed [transition](#transition). Its `fromCounter` and `fromRoot` name the expected current head, which the manager compares with its stored head. |
| `recoveryLeaves` | Optional. `{entryKey, valueDigest}` items |

The request carries no leaf payloads. Sealed identities, contents, nonces,
and tags go only to Evolu as `wardTransition` rows, which `wardd` writes
before it calls the manager.

The manager processes a commit in these steps.

1. Verify the wallet `signature` with the public key in `wardId`. On failure,
   return HTTP 403.
2. Verify that `counter` equals `fromCounter + 1`. On failure, return HTTP 400.
3. If the proposed transition equals the latest accepted one, it is a retry:
   return the same response again.
4. Compare the latest accepted transition's `counter` and `root` with the
   proposed transition's `fromCounter` and `fromRoot`. On a mismatch, return
   HTTP 409 with the latest transition.
5. Store the proposed transition as the latest accepted one, together with the
   recovery leaves if provided.
6. Respond with `wardId`, the accepted `transition`, the acceptance
   `timestamp` (UTC seconds), and the manager's finalization `signature` over
   both:
   `"WARD FINAL v1" || kindByte || wardId || fromCounter:u32 || fromRoot || counter:u32 || root || mac || authCommit || timestamp:u64`.
   These are the bytes the wallet signed, under the manager's domain tag,
   followed by when the manager accepted them. A retry returns the same
   timestamp and signature.

`wardd` passes the finalization `signature` and `timestamp` to the device in
`WARDConfirmBatchByWM` for a commit or `WARDConfirmRevertByWM` for a revert.
The device rebuilds the transition from its own pending batch and verifies the
signature before it installs the new head. A manager can therefore finalize
only the exact transition the device performed: the same predecessor,
successor, kind, and `authCommit`. The device does not display the time here.

`wardd` also stores the `timestamp` and `signature` in Evolu, in a
`wardAcceptance` row keyed like the transition by `(wardId, counter, root)`.
When the latest head cannot be rebuilt from the data in Evolu, `wardd` asks the
device to revert it and sends the stored acceptance in `WARDPerformRevert`. The
device rebuilds the stuck head's transition, verifies the signature, and shows
when the manager accepted that change on the revert screen.
