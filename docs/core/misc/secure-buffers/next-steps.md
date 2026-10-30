## Follow-up plan

| Order | Work | Completion evidence |
| --- | --- | --- |
| 1 | Review Stage 0 independently against the stack’s main baseline; port it to the intended upstream revision without unrelated changes. | Existing cache policies, values and invalidation remain identical; review storage snapshot overhead and 32-bit flash/RAM/stack costs. |
| 2 | Validate Stage 1, kernel operations, hardware record sealing and protocol migration on hardware, including universal and Bitcoin-only variants. | Boot, seed/passphrase reuse, Cardano, WebAuthn/U2F, storage lock/unlock, session replacement and restart pass at each relevant endpoint. Distinguish known USB failures using the final transport correction in a separate validation branch where necessary. |
| 3 | Verify the implemented key-type and bound-node signing contracts at each affected endpoint. | Cross-curve misuse and independently substitutable Cardano scalar/prefix inputs are rejected; matching native, emulator and hardware regressions pass. Do not mark the stages complete while the recorded gaps remain. |
| 4 | Exercise hardware key/nonce lifetimes and fault handling. | Kernel/secmon restart, storage lock/wipe and vault reset cannot reuse a GCM key/nonce pair or couple record and storage-cache lifetimes. Authentication/key-readiness failures release no plaintext. |
| 5 | Measure optional credential-key and transaction-context reuse independently on hardware. | Identical outputs; latency, retained RAM and peak stack captured with reuse off/on. Seed reuse is warm in both credential-key cases. Include grouped/alternating GCM/SIV/KWP operations and owner cancellation. Keep these features optional unless their benefit justifies them. |
| 6 | Revisit inherited Cardano eager-root policy only as a separate optimization. | Compare one address and repeated/mixed namespaces against lazy roots; preserve derivation vectors and session teardown. |
| 7 | Prepare upstream changes in Stage 0 → 5 order. | Each stage is independently reviewable, functional and validated; cache backend adaptations stay with that stage. Keep SIV/KWP unmerged; carry only GCM through later stages. Keep any USB correction separate. |

## Required stage sequence

`cache-framework` (0) → `wallet-integration` (1) → `kernel-ops` (2) →
`key-wrap` (3) → `cipher-base` → `gcm` / `record-sealing` (4) → `thp-vault` (5).
All branch names use `petrsusil/secure-buffers-cache-stages_`. SIV and KWP are
siblings of GCM, outside its ancestry and the later stage sequence.

## Post-migration cleanup stages

| Stage | Work | Completion evidence |
| --- | --- | --- |
| 6 | Migrate to the canonical provider interfaces, then remove compatibility aliases, forwarding headers and unused build-selection forms. | No callers remain on removed interfaces; wire ABI, cache policies and security boundaries are unchanged. Measure source and linked-flash changes. |
| 7 | Compact the THP descriptor and measure the effect on native and opaque key variants. | Shared C/Rust size contract, bounded RPC expansion, unchanged identity/handshake/reset behavior, and measured channel RAM/stack. |

These stages are proposed and have no implementation branches yet. Full main
compatibility is required for device identity, credentials, wire messages,
pairing/reset behavior, storage formats and upgrade/downgrade behavior; no host
update, re-pairing or data migration is part of these cleanups. Security
cleanup at each earlier stage remains part of that stage’s completion boundary.

## Current boundary

Stages 0–5 are based on main `005a137a18`. Only GCM continues through the
security stages; SIV and KWP remain independent provider-base alternatives.
The bound-node Cardano contract is implemented from wallet activation and
preserved by the typed kernel stage. Hardware coverage is pending for the
rewritten checkpoints. Existing results validate only their recorded revisions.

Hardware workflows advance in order **1 → 3 → 5 → 2 → 4**, dispatching each
only after its predecessor completes successfully. Run 41024223378 validates
the rebased Stage-1 candidate `0d53d0f841`.
