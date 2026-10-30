## Cache framework by stage

| Stage | Representation and interface checkpoint |
| --- | --- |
| 0 | `DataCache.get_secret`, `take_secret` and `delete_secret` delegate to main’s byte arrays. Secret-field declarations are shared class metadata; capacities and slot indices stay unchanged. Existing decorators still use the same plaintext backend. Storage-key reads/stores/clears use internal helpers; no new cache entries, owners or sealed holders are introduced. |
| 1 | Each declared secret byte array is replaced by an in-place `secbytes` holder. Public metadata remains a byte array. Secret context routing partitions the existing no-passphrase seed by owner. `take_secret` consumes a request value and requires retention into the exact target cache owner; self-assignment is a no-op. Owner revocation invalidates all secret slots without reallocating them. |
| 2 | The same opaque values are produced/used through typed kernel operations; coreapp metadata is not an authorization source. Existing node/public-key and boot ZKP reuse migrate with their consumers. |
| 3 | The storage-key access helpers select an independent RFC3394 wrapped-key backend; idle record keys are wrapped separately. Storage lock/wipe clears the cache; vault/VM reset does not redefine its unlock lifetime. |
| 4 | The hardware provider selects SAES GCM for protected records and independently for storage keys, with separate keys/nonces. Software fallback remains available. SIV/KWP stay separate leaves and do not enter later stages. |
| 5 | Existing protocol consumers use the established owner/provider contracts. Channel/session teardown and device-secret reset remain distinct lifetime events. |

| Cache present on main | Reuse preserved / handling | Lifetime | Stage |
| --- | --- | --- | --- |
| Wallet seed | Avoid repeated derivation and passphrase interaction; same declared 64-byte slot becomes sealed. | Session owner | 0 → 1 → 2 → 3 → 4 |
| No-passphrase seed | Avoid repeated PBKDF2. A sealed record cannot cross owner domains, so universal sessions receive an owner-local slot; real FIDO/no-session requests retain the sessionless slot. Bitcoin-only sessions allocate no FIDO slot. | Owning session or sessionless owner | 0 → 1 → 2 → 3 → 4 |
| Icarus / Icarus-Trezor secrets | Preserve both 96-byte slots and reuse; no wallet/Cardano holders are allocated in the sessionless cache. Main aliases the derivation for non-24-word mnemonics; the protected producer currently performs two derivation calls during a cold fill. | Session owner; universal builds | 0 → 1 → 2 → 3 → 4 |
| BIP32 / SLIP21 prefix LRU | Preserve up to ten prefixes and existing clone/release interfaces; retained nodes become opaque. | Keychain, with owner revocation | 1 → 2 → 3 → 4 |
| Four Cardano namespace roots | Preserve main’s eager policy. Four roots add eight derivation steps; for one namespace the work is `8 + 3N` versus `5N`, so fewer steps only for `N > 4`. | Keychain | 1 → 2 → 3 → 4 |
| HDNode public key | Preserve memoization through sealed-node writeback. The public slot already exists; kernel writeback is limited to the active owner’s node. | Node | 1 → 2 |
| ZKP context | Preserve main’s boot-time native reuse when moving ECC into the kernel. Its preallocated buffer already exists; it is native working state, not a serialized secret slot. | Boot | 2 |
| Storage DEK/SAK | Preserve unlocked operational state; adapt its existing access seam from plaintext to independent wrapping and hardware GCM. Temporary snapshots are erased after use. | Storage unlock/lock/wipe; independent of vault reset | 0 → 3 → 4 |

New credential-key sharing and transaction-context reuse are optional branches,
merged only at integration. Neither is part of Stage 0 or a prerequisite for
seed reuse. The five security-stage branch tips exclude both optimizations.
Public metadata, owner registries, nonce counters and live protocol key state
retain their appropriate representations; the framework does not serialize
native contexts or introduce a global trusted cache service.

## Container allocation comparison

The same 64-bit T3T1 universal non-frozen GCM emulator measured the actual old
Python constructors from `1e8c39c6d6` and the new constructors. Native holder
layout was held fixed. Values were empty; constructor and post-clear retained
heap matched. Class/module import costs, native BSS and peak stack are excluded.
These host figures are not ARM RAM figures.

| Container | Previous protected layout | Framework layout | Retained heap saved |
| --- | ---: | ---: | ---: |
| Codec session | 1,760 B; four holders in separate members | 1,504 B; four holders in the slot vector | 256 B |
| Sessionless | 1,376 B; wallet, no-passphrase and two Cardano holders | 800 B; only the existing no-passphrase holder | 576 B |
| Ten Codec sessions plus sessionless | 18,976 B | 15,840 B | 3,136 B |

The historical layout benchmark (`bench_cache_layout.py`) measures
constructors and clearing directly. Bitcoin-only sessions omit the additional
owner-local no-passphrase slot; their exact ARM/THP savings need separate
measurement. Stage 0 retains main’s plaintext payloads and adds no per-entry
wrapper objects.

## Earlier reuse measurements

Pre-framework protected layout, T3T1 non-frozen universal emulator, GCM, 2026-10-29. Eight operations per row;
one cold fill is included in the reuse variant. Output equality and expected
producer-miss counts are checked. Passphrase UI time is excluded. These host
observations do not predict hardware timeouts.

| Cache | Forced misses, total µs | Reuse, total µs | Work without → with reuse |
| --- | ---: | ---: | --- |
| `session_seed` | 6,515 | 908 | 8 → 1 seed derivations |
| `no_passphrase_seed` | 6,738 | 952 | 8 → 1 seed derivations |
| `cardano_icarus` | 51,895 | 6,450 | 16 → 2 Icarus derivations |
| `keychain_prefix` | 2,809 | 1,789 | 8 → 1 root/prefix fills |
| `slip21_prefix` | 777 | 497 | 8 → 1 root/prefix fills |
| `cardano_prefix` | 2,961 | 2,675 | 40 → 32 child derivation steps, including four eager roots |
| `credential_key` | 1,198 | 466 | 8 → 1 credential-key derivations; warm seed |

Workload heap deltas are emitted as `observed_heap_delta`; they include output
lists, finalization effects and benchmark bookkeeping. They are neither peak
RAM nor the incremental size of the cache. Holder allocations are measured
separately. Removing reuse does not reclaim already reserved static contexts
or preallocated sealed holders. The 97-byte software storage-cache object
excludes the 33-byte fallback wrapping-key state used in production on F4.

Native optimized host build, median of five batches per row. Each record
batch seals and opens 64 records; public-key batches perform 32 reads.
Storage batches read all 48 key bytes 1,000 times. Sanitized runs verify
correctness separately and are excluded from these timing figures.

| Mode / workload | Forced setup / plaintext, µs | Reuse / protected, µs | Work or retained-state checkpoint |
| --- | ---: | ---: | --- |
| GCM / `record_context_alternating` | 1,009.2 | 223.9 | 128 → 1 setups; 352 B context in both builds |
| GCM / `record_context_grouped` | 988.3 | 231.9 | 128 → 1 setups; 352 B context in both builds |
| GCM / `node_public_zkp_cold` | 2,270.7 | 1,089.7 | 32 → 1 point multiplications; 32 ZKP initializations in both columns |
| GCM / `node_public_zkp_warm` | 1,600.0 | 355.4 | 32 → 1 point multiplications; 1 ZKP initializations in both columns |
| GCM / `storage_key_protection` | 16.9 | 13,543.9 | 48 B plaintext → 97 B wrapped-cache object; test KEK/provider state excluded |
| SIV / `record_context_alternating` | 1,759.0 | 242.3 | 128 → 1 setups; 512 B context in both builds |
| SIV / `record_context_grouped` | 1,824.8 | 234.7 | 128 → 1 setups; 512 B context in both builds |
| SIV / `node_public_zkp_cold` | 2,552.7 | 1,277.1 | 32 → 1 point multiplications; 32 ZKP initializations in both columns |
| SIV / `node_public_zkp_warm` | 1,884.7 | 579.7 | 32 → 1 point multiplications; 1 ZKP initializations in both columns |
| SIV / `storage_key_protection` | 15.5 | 13,617.9 | 48 B plaintext → 97 B wrapped-cache object; test KEK/provider state excluded |
| KWP / `record_context_alternating` | 2,009.9 | 1,978.2 | 128 → 128 setups; 256 B context in both builds |
| KWP / `record_context_grouped` | 2,129.4 | 1,218.2 | 128 → 2 setups; 256 B context in both builds |
| KWP / `node_public_zkp_cold` | 3,484.4 | 1,841.7 | 32 → 1 point multiplications; 32 ZKP initializations in both columns |
| KWP / `node_public_zkp_warm` | 2,924.4 | 1,125.6 | 32 → 1 point multiplications; 1 ZKP initializations in both columns |
| KWP / `storage_key_protection` | 15.8 | 13,650.0 | 48 B plaintext → 97 B wrapped-cache object; test KEK/provider state excluded |

The storage implementation is the same RFC3394 software cache in all three
record builds; variation between those rows is host measurement noise, not a
mode-dependent storage-cache choice. Hardware record sealing has no software
expanded-key cache. The native provider uses deterministic test entropy and
software AES stand-ins, so it cannot measure SAES or secmon latency.

[Raw observations](cache-measurements-2026-10-29.json) record the source,
compiler flags, archive digest, sanitizer status and repetitions. The opt-in
historical MicroPython measurement (`bench_secure_buffer_caches.py`)
uses real producers and eviction/clear paths; the
historical native measurement (`measure_vault_caches.py`)
uses the actual vault dispatcher, sealing and storage-cache implementations.
Timing is reported without flaky pass/fail thresholds. Native tests assert
setup/point-multiplication/initialization counts and erasure; both suites check
unchanged outputs. Hardware cache-benefit evidence is still pending.
