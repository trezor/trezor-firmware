# Secure buffers proof of concept

This prototype implements secure secret handling for
[issue #981](https://github.com/trezor/trezor-firmware/issues/981) on base
`6f1ab9a08e`. The cumulative branches separate preparation, implementation and
activation so the final integration changes can be reviewed in context. The
original PoC branch is preserved. This is not production-ready firmware.

## Milestones

Every branch includes the fixes and tests needed for its scope. C1, C2 and C3
use preparation commits inside their milestone branches. C2 enablement and the
C3 U5 default switch follow their backend implementations and tests.

| Stage | Branch suffix | Checkpoint | Scope |
| --- | --- | --- | --- |
| A | `a` | `ebe465c8b7` | Stub-only secbytes; no runtime change. Pyright identifies 17 plaintext consumers. |
| B1 | `b1` | `f5595c58b1` | Standalone AES sealing and bounded native API declarations; no producer activation. |
| B2 | `b2` | `e02cda3494` | Caller-bound byte vault, opaque objects, lifecycle, cache-owner preparation and complete native coreapp adapter. Application producers stay byte-backed. |
| THP prerequisite | `thp` | `c5ef9cf2f3` | Native legacy identity derivation, handshake error recovery and an owned, byte-compatible session-seed derivation task. |
| B3 | `b3` | `203dff12df` | Activate protected HDNodes, seeds and wallet/FIDO consumers; include lifetime fixes and scheduler-aware regression tests. The b branch aliases this checkpoint. |
| C1 | `c1` | `ba0638e3af` | Prepare opt-in crypto options and stack tooling, then migrate operations and tests into the kernel and remove native-open op 128. |
| C2 | `c2` | `c9196661b0` | Prepare wrapping interfaces; implement and test BHK wrapping, sealed storage caches and fault checks; enable the backends last. |
| C3 | `c3` | `135a04056a` | Prepare the SAES ABI; implement opt-in record/cache encryption, per-kernel-run key replacement and tests; switch U5 defaults last. |
| THP secbytes | `thp-secbytes` | `e302cf7f86` | Device-owned sealed device secret, kernel identity derivation and X25519, credential MACs, and native identity preservation across reset. |
| Hygiene | `hygiene` | `239ec49fa1` | SHA-2 schedule and Ed25519 intermediate erasure; residual unused-stack cleanup at vault, storage and secure-call boundaries; cleanup tests and changelog. |
| Timing/logging | `timing` | `614bf8e0e3` | Optional per-phase syscall cycle counts and logging configuration. Includes software and SAES paths and cleanup time. |
| Docs | `docs` | this branch | PoC notes and validation descriptions. Required stack-analysis tooling already lands in C1. |
| D | — | not started | Secure-world vault execution. |

Branch names use the prefix `petrsusil/secure-buffers-poc_`. There is no D
branch because its implementation has not started. Timing and logging are
absent before the timing branch. Hardware SAES first becomes the U5 default
at the end of C3; F4 and the emulator retain software SIV by default.

## THP boundaries

The prerequisite branch keeps THP compatible before B3 activates protected
wallet objects. It derives the legacy Curve25519 identity in zeroizing native
memory, keeps private identity keys out of Python, recovers from handshake key
failures, and prepares seed derivation under the new session owner. Its device
secret remains Python bytes. B1 and B2 do not activate protected producers.

The later THP stage changes `device.get_device_secret()` to return `secbytes`.
A separate applet-bound device owner works without a wallet session. The
kernel reads or provisions the existing 16-byte storage secret, derives the
legacy hardened identity, and seals its scalar. Noise retains a ciphertext
descriptor between packets and requests X25519 operations through the vault;
private identity scalars are never exported. Ephemeral Noise keys and transport
cipher state remain native coreapp secrets; this stage does not move the whole
THP protocol into the kernel or secure world.

Credential authentication derives its SLIP-21 key and computes HMAC in the
vault. Reset preserves the device secret natively while revoking old records.
Golden identities, credential compatibility, ownership, locking, reset,
repeated signing and passphrase handling are covered by regression tests.
The generic private-opening operation removed in C1 is not restored.

## Hygiene boundaries

Explicit cleanup erases SHA-2 schedules and Ed25519 intermediates, including
invalid-input exits. Existing transaction cleanup wipes vault scratch and
crypto contexts. After sensitive callees return, privileged kernel and secmon
boundaries scrub unused stack words below the current SP. Live frames, other
tasks' stacks and interrupt stacks are not erased. This is not a claim that all
registers or all firmware stack memory have been cleared.

The scrubber checks the linked stack bounds, handles an empty range, preserves
callee-saved registers and restores PRIMASK. Its interrupt guarantee applies
to privileged callers. Native tests observe erasure while C objects are still
alive; a separate CPU-emulation test executes the actual linked Thumb function:

```sh
nix-shell --run 'uv run --script core/tests/native/test_stack_scrub.py core/build/artifacts/T3W1/kernel.elf'
nix-shell --run 'uv run --script core/tests/native/test_stack_scrub.py core/build/artifacts/T3W1/secmon.elf'
```

## Validation and hardware limits

B1 and B2 pass native tests and emulator builds. The THP prerequisite and B3
pass the full THP suite, including ABP; B3 also passes its protected-seed units.
C1, C2 and C3 pass native suites, embedded T3W1 Bitcoin-only builds and ELF
placement checks. One C1 rustc/LLVM build crashed; retrying with
`RUST_MIN_STACK=16777216` passed without a firmware source workaround. Native suites
cover SIV, GCM and experimental ECB; C3 also exercises the secure-world SAES
interface through a software stand-in. Emulator checks cover THP, protected
seeds, identity and credential compatibility, owner revocation, lock and reset.
The protocol library's 140 tests pass. Embedded T3W1 Bitcoin-only builds and
kernel/coreapp/secmon ELF placement checks pass. The linked kernel and secmon
stack scrubbers pass CPU-emulation checks for bounds, live frames, MSP/PSP,
callee registers and interrupt-mask preservation.

These checks do not exercise physical SAES, DHUK/BHK behavior, hardware fault
injection or real DWT timings. Those need a supported physical device running
the matching firmware. The timing branch builds with
`TREZOR_VAULT_TIMING=1`, with info logging both enabled and disabled. Emulator
cycle counts are zero; they validate the logging path only.

To capture a connected device's serial debug output:

```sh
nix-shell --arg hardwareTest true --run './tools/read-device-log.sh /dev/ttyTREZOR > trezor.log 2>&1'
```

This command captures logs; tests or operations must be run separately against
the device. Device tests can also target an emulator through `core/emu.py`.
Use a headless temporary profile and a unique UDP base port. C1 and later THP
runs exclude the two ABP tests because that backup scope is not implemented.

The full style gate retains 14 known unsupported plaintext consumers: Cardano,
EOS public keys, CipherKeyValue, ECDH and identity signing. These are existing
PoC limits, not a passing type-check claim. Hardware execution remains
unverified. Final universal T3T1 and T2T1 embedded builds and stack-scrubber
tests pass. T2T1 has only about 0.5 KiB free in its first flash region in the
universal test preset; this margin needs care. All historical measurements
below predate this reconstruction.

## Footprint by stage

These are historical measurements from the original checkpoints, before the
fixes were folded back. They are not measurements of the rebuilt branch tips:
the 5 KiB kernel optimization now lands in C1, and B already includes the
additional operation support. Re-measure before using these deltas to budget
the rebuilt stages.

All five buildable production models were measured at every checkpoint, as
full-coin `-p test` images. A adds no code on any model. T3T2 does not build on
main itself (`tzsc_ensure_unlocked` unused under `-Werror`).

Firmware flash growth per stage, KiB, each against the previous stage. These
are exact content sizes, without alignment padding: on U5 the kernel `.flash`
plus coreapp up to the embedded bootloader, on F4 `.flash` plus `.flash2`. The
last two columns are the linker's padded image, which is what has to fit.

| Model | A | B | C1 | C2 | C3 | Total | Image at C3 | Free at C3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T2T1 | 0 | +21.0 | +53.3 | +3.0 | 0 | +77.2 | 1628.0 | 36.0 of 1664 |
| T2B1 | 0 | +21.0 | +53.8 | +2.5 | 0 | +77.2 | 1437.3 | 226.7 of 1664 |
| T3B1 | 0 | +20.7 | +53.3 | +0.5 | −1.0 | +73.6 | 1458.5 | 205.5 of 1664 |
| T3T1 | 0 | +20.7 | +53.3 | +1.0 | −1.5 | +73.6 | 1638.5 | 25.5 of 1664 |
| T3W1 | 0 | +16.3 | +65.3 | −1.5 | −2.5 | +77.7 | 2440.5 | 895.5 of 3336 |

A changes only stubs and comments (T3B1 differs by 4 B). On T3W1, C2 grows
secmon, a separate image, by 3.9 KiB and C3 shrinks it by 0.4 KiB. C3 does not
change F4, which keeps software SIV. C3 saves flash on U5: sealing records in
SAES costs about 1.5 KiB, and moving the storage cache there removes the
software SIV code (about 3 KiB).

On U5 the coreapp image starts on an 8 KiB boundary (`COREAPP_ALIGNMENT`), so
kernel growth first fills the padding before that boundary and the image only
grows in 8 KiB steps. C2 adds 0.5 to 1 KiB of kernel code, which fits in the
padding on every U5 model, so the padded image does not change.
The kernel sections are exact. Kernel `.flash` and `.bss`, bytes:

| Model | Base `.flash` | Δ B | Δ C1 | Δ C2 | Δ C3 | C3 `.flash` | Base `.bss` | Δ B | Δ C1 | Δ C2 | Δ C3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T2T1 | 121,344 | +6,656 | +62,976 | +3,072 | 0 | 194,048 | 7,012 | +1,704 | +192 | +128 | 0 |
| T2B1 | 98,816 | +6,656 | +63,488 | +2,560 | 0 | 171,520 | 5,564 | +1,704 | +192 | +128 | 0 |
| T3B1 | 116,224 | +6,656 | +62,976 | +512 | −1,024 | 185,344 | 6,628 | +1,704 | +192 | +64 | −552 |
| T3T1 | 136,704 | +6,656 | +62,976 | +1,024 | −1,536 | 205,824 | 7,692 | +1,704 | +192 | +64 | −552 |
| T3W1 | 143,872 | +7,168 | +75,264 | −1,536 | −2,560 | 222,208 | 23,728 | +1,704 | +188 | −32 | −568 |

On T3W1 the C2 and C3 work lands in secmon, which owns storage and SAES: secmon
code grows from 105,080 to 109,080 B in C2 and is 108,712 B after C3, and its
`.bss` goes from 2,644 to 2,740 B and 2,756 B. The T3W1 kernel shrinks in C2 and
C3 because the software key wrap and then the software record AES leave it. C3
frees kernel RAM everywhere it applies, since `record_ctx`, `wrapped_dek` and
the cache's software keys go.

In the original series, after C3 the kernel enables `crypto/bip32_vault` and
`crypto/ed25519_no_precomp`. HDNode includes only secp256k1, NIST P-256 and
Ed25519; standalone Ed25519-Keccak signing remains available. Ed25519
verification computes a small basepoint table on the stack instead of linking
the 3,840-byte table. Its three-bit window bounds that temporary table to
320 B, at the cost of more point additions during verification. Coreapp keeps
its existing crypto configuration.

On T3T1, full-coin `-p test` builds before and after this change reduce kernel
`.flash` from 205,824 to 200,704 B and the padded firmware image from 1,638.5 to
1,630.5 KiB. Kernel `.bss` is unchanged at 9,100 B. The vault message path stays
at 7,072 B of stack; the bootloader replacement path now uses 7,256 B including
SVC entry, leaving 936 B of the 8,192-byte kernel stack before the MSPLIM
reserve and interrupts. The previous five-bit window in table-free Ed25519
verification would exhaust that stack, so it must not be restored without
checking the complete replacement path.

Where the remaining space is:

| Model | Coreapp code: Δ B | Δ C1 | Padding before coreapp: C1 → C2 → C3 | Kernel RAM region free at C3 |
| --- | ---: | ---: | ---: | ---: |
| T2T1 | — | — | not padded | 6,580 of 16,128 B |
| T2B1 | — | — | not padded | 8,028 of 16,128 B |
| T3B1 | +14.2 KiB | −8.2 KiB | 512 → 0 → 1,024 B | 16,028 of 32,768 B |
| T3T1 | +14.2 KiB | −8.2 KiB | 4,096 → 3,072 → 4,608 B | 10,868 of 28,672 B |
| T3W1 | +9.3 KiB | −8.2 KiB | 1,536 → 3,072 → 5,632 B | 26,692 of 65,536 B |

- Coreapp code grows in B with the bindings and the Python lifecycle changes,
  and shrinks in C1 when the coreapp crypto adapter goes.
- At C2 the T3B1 kernel ended exactly at the boundary. SAES record sealing alone
  crossed it (+8 KiB padded image); with the storage cache in SAES it fits again,
  1,024 B short of it.
- The kernel RAM region holds the kernel stack, `.data` and `.bss`; it fits on
  every model.
- Coreapp `.bss` and `.data` grow by 1,248 B in B (780 B of it the owner task table and GC
  roots), shrink by 324 B in C1 and do not change in C2 or C3, on every model.

Kernel stack, static worst case, bytes. Stack size is from each kernel ELF:

| Model | Kernel stack | Base: deepest syscall | B: vault op | C1/C2: vault op | C1/C2: Ed25519 message | C3: Ed25519 message | Headroom at C3 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| T2T1, T2B1 | 10,240 | 7,032 | 2,040 | 6,204 | 7,048 | 7,048 | 3,192 |
| T3B1, T3T1 | 8,192 | 6,920 | 2,040 | 6,204 | 7,048 | 7,072 | 1,120 |
| T3W1 | 12,288 | 4,120 | 2,008 | 6,204 | 7,048 | 7,072 | 5,216 |

- The base column is the deepest existing syscall (`boot_image_replace` on
  T3T1). B stays below it.
- From C1 the Ed25519 message path is the deepest syscall on every model: SVC
  entry, the 2,288 B message snapshot, then Ed25519 signing (3,664 B). The
  deepest regular vault op is the BIP340 key tweak (4,652 B under the 1,552 B
  syscall chain).
- On T3B1 and T3T1 that leaves 1,120 B at C3; MSPLIM reserves 128 B of it, and
  interrupts nested in the syscall need the rest. C3 adds 24 B to the vault
  paths (the deepest regular op is then 6,228 B).
- The SLIP-21 op runs in its own noinline frame, so canonical signing and
  SLIP-21 leave the T3T1 vault paths at 6,220 B (regular op) and 7,064 B
  (Ed25519 message). Inlined, they had grown `vault_execute` by 336 B.
- C2 adds 476 B to kernel storage unlock (1,540 → 2,016 B) on U5 kernels, and
  484 B to secmon storage unlock on T3W1 (1,444 → 1,928 B). The new
  `vault_kek_wrap` smcall needs 568 B of secmon stack, and C3's
  `vault_saes_record` 1,448 B (1,200 B when a secure-mode kernel calls it
  directly). The SAES storage cache adds 456 B to storage unlock: 2,472 B in
  the T3T1 and T3B1 kernels, 2,384 B in secmon on T3W1.
- A path-insensitive bound that lets the message entry reach any op is 8,036 B,
  but that entry accepts only `VAULT_ED_SIGN`.

The stack figures come from the linked ELF: frames from the disassembly, worst
call chains, known function-pointer targets resolved, noreturn fatal paths cut.
They exclude exception stacking, nested interrupts and unresolved indirect
calls (`ui_progress`, the `is_canonical` callbacks). Hardware high-water marks
are still required.

```sh
git switch --detach <checkpoint>
nix-shell --run 'uv run xtask build firmware -m T3T1 -p test'
nix-shell --run 'uv run python core/tests/native/kernel_stack.py core/build/artifacts/T3T1/kernel.elf --vault'
arm-none-eabi-size -A core/build/artifacts/T3T1/kernel.elf
```

## Classification by attacker objective

Classify a value by what an attacker can recover or do with it. Algorithm names,
Python types and short lifetimes do not determine sensitivity. A decrypted AES
schedule, usable HMAC state or predictable nonce generator is as sensitive as
the key it represents.

| Attacker objective | Target material | Consequence and protection |
| --- | --- | --- |
| Reconstruct a wallet | Mnemonic/entropy, recovery shares, BIP39 seed, master extended private keys, Cardano roots | Wallet roots. One sub-threshold share is partial recovery material. |
| Obtain signing authority | Derived private scalars, private HDNodes, nonce scalars, secret signing state | An ECDSA nonce plus its signature and message exposes the key. |
| Decrypt other captured secrets | Storage DEK, vault record keys, expanded AES state, wrapping keys | Inherit the impact of everything they unlock. |
| Unlock or select a wallet | PIN, passphrase, unlock salt and verification intermediates | A passphrase plus the mnemonic reconstructs its wallet. |
| Impersonate a credential | FIDO credential keys, derivation roots, CredRandom | In scope. |
| Impersonate a device | THP device and attestation keys | Derived THP static keys stay native; the device secret and attestation remain outside wallet-vault migration. |
| Read or alter a session | Ephemeral DH keys, shared secrets, traffic keys | Deferred; short lifetime does not make them public. |
| Expose private data | Monero view keys, decrypted user data, xpubs, labels | View keys need secret storage; exported xpubs do not. |
| Forge state | Storage SAK, owner/type/length metadata | Integrity-sensitive; a SAK is not a DEK. |

A non-hardened child private key plus its parent xpub reveals the parent
private key ([BIP32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki#implications)).
Acceptance tests must attempt the objective, for example decrypting a record
with a captured DEK, rather than grep a dump for known key bytes.

## Stage A: type checking

`modtrezorcrypto-secbytes.h` declares `class secbytes` for the stub generator
only. `HDNode.private_key()`, `private_key_ext()`, `bip340.generate_secret()`
and `tweak_secret_key()` are typed to return it. Signing and public-key functions
for secp256k1, BIP340, Ed25519 and P-256, and `bip32.from_seed()`, accept it.
At runtime the values are still `bytes`.

Pyright then reports 17 errors at call sites that need plaintext keys: Cardano
`sign_ext` (6), ECDH session keys (3), EOS public key, `sign_identity`,
`CipherKeyValue`, THP static keys and four WebAuthn HMAC/encryption uses. Stage B
migrates the WebAuthn ones and adds four seed-holder errors (base, Evolu, two in
Cardano seed) in the original series. The rebuilt stages include SLIP-21
support; 14 unsupported consumers still fail the type gate.

## Stage B: coreapp vault

Secrets live in coreapp memory only as sealed records, and the record keys live
in the kernel. Crypto still runs in coreapp: before each operation the binding
opens a record into bounded native scratch through op 128, computes and wipes.

- **Records.** `secbytes` holds a compact sealed record of its value; a protected
  `HDNode` holds a sealed 107-byte node encoding (depth, child number, chain code,
  private key, cached public key, curve ID). There is no per-secret kernel slot
  and no pool to exhaust. The kernel keeps 64 owners, two 160-byte scratch
  payloads and the wrapped record keys.
- **Sealing.** `TREZOR_VAULT_MODE` selects AES-SIV (default; two AES-256 keys,
  deterministic), AES-GCM (64-bit per-boot nonce) or ECB (unauthenticated
  experiment, build warning). SIV and GCM authenticate owner, kind and length.
- **Keys.** Record keys are random per boot. In B they are wrapped per RFC 3394
  with a software key held in kernel RAM on every model.
- **Python API.** Call shapes are unchanged: `keychain.derive()`,
  `node.private_key()`, `secp256k1.sign(key, digest)`. `secbytes` has no buffer
  protocol, indexing, `.hex()` or plaintext getter; its repr is `<secbytes>`.
  `private_key()` returns an independent snapshot that later `derive()` or
  destruction does not change. Bitcoin signs directly from the node.
- **Ownership.** Kernel owners are bound to the calling applet. Coreapp activates
  request and session owners through a scheduler task table (780 B static) with
  hooks in `loop.py`. Request completion, `loop.close()`, `loop.clear()`, session
  end, cache eviction, `storage.wipe()` and VM init/deinit revoke owners without
  relying on Python unwinding.
- **Heap per value (SIV).** 32-byte key 64 B, the same as `bytes`; 64-byte seed
  96 B; protected node 144 B.

B is stronger than the design's coreapp vault: an idle coreapp RAM read sees only
ciphertext. During an operation the opened key sits in coreapp memory.

## Stage C1: kernel vault

All covered operations run in the kernel; coreapp sends ops and receives sealed
children or public results.

- One versioned syscall with a pointer-free request (496 B in SIV) and a union
  response (268 B). The verifier probes and copies the request and erases the
  copy. A second entry copies an Ed25519 message of up to 2,048 B into a kernel
  stack snapshot, so both signing passes see the same bytes.
- Kernel ops: canonical Ethereum/EOS ECDSA and SLIP-21; owners and revocation;
  BIP39 seed from storage; BIP32 derivation
  for secp256k1, P-256 and Ed25519; key snapshots; ECDSA; BIP340 generate, tweak
  and sign; P-256 sign; HMAC with public tags on messages up to 256 B; Ed25519 sign.
- Storage access: `SYSCALL_STORAGE_GET` refuses the mnemonic keys, including
  flag aliases. The seed is derived from storage inside the kernel.
- Every secret op checks the storage unlock state; cleanup stays allowed while
  locked. Task termination and the storage wipe syscall revoke vault owners.
- The kernel secp256k1 generator table is 2 KiB; coreapp keeps 22 KiB. The
  smaller table keeps the constant-time structure but changes the operation
  sequence, so physical leakage must be measured again.
- `76c4ab4916` retires op 128. A native test requires it to fail with a zeroed
  response.

## Stage C2: encrypted kernel vault

- **Record keys.** `vault_kek_wrap` wraps them under the BHK. Secure-mode kernels
  (T3T1, T3B1) call SAES directly; on T3W1, T3T2 and D002 a fixed-purpose smcall
  runs the whole wrap in secmon on a secure-world copy. There is no per-block
  AES oracle. F4 and the emulator keep the software key, so they make no
  RAM-dump claim.
- **Storage keys.** `sec/storage/key_cache.c` replaces `storage.c:cached_keys`
  wherever storage runs: in the kernel, or in secmon on secmon models. The
  32-byte DEK and 16-byte SAK are AES-SIV sealed under two independent keys,
  wrapped the same way. The cache follows storage unlock, lock, init and wipe,
  independently of vault owners. Persistent formats are unchanged. With
  `--secmon`, `check_vault_elf.py` checks the cache in secmon.
- **Fault hardening.** A single skipped branch no longer releases a secret:
    - The SIV tag and the RFC 3394 integrity block are compared twice. With CTR,
      one skipped tag check would otherwise turn ciphertext bit flips into
      chosen key bit flips, and each resulting public key reveals one key bit.
    - Owner access is re-evaluated after decryption, and the unlock state again
      before any result leaves the vault.
    - Each transaction verifies that scratch and the expanded record keys are
      zero; otherwise it revokes all owners.
    - `vault_kek_wrap` refuses an all-zero BHK. `secret_bhk_load()` installs one
      when the secret area cannot be read, which would otherwise fail open.
- During an operation the unwrapped keys and expanded schedules exist in kernel
  RAM; they are erased before return.

## Stage C3: hardware record encryption

With `TREZOR_VAULT_MODE=saes`, the default on U5, vault records are sealed with
AES-256-GCM in SAES instead of trezor-crypto table AES. The record format, ABI,
per-boot nonce counter and coreapp code are those of the GCM mode.

- **Record key.** The secure world generates a random 256-bit key at first use,
  has SAES wrap it under DHUK (`HAL_CRYPEx_WrapKey`) and erases the plaintext.
  For each record it unwraps the key into the SAES key registers
  (`HAL_CRYPEx_UnwrapKey`), so the key never exists in RAM after generation and
  no software AES runs on it. DHUK cannot be read by software and cannot be
  zero, unlike the BHK.
- **Placement.** Secure-mode kernels (T3T1, T3B1) call `vault_saes_record()`
  directly; on secmon models a `vault_saes_record` smcall runs it in secmon on a
  secure-world copy of the request. The kernel keeps only the nonce counter and
  AAD; `record_ctx` and `wrapped_dek` are gone, and the ELF check asserts it.
- **Checks.** `KEYVALID` is tested after the key is loaded, and each new key must
  pass a seal/open round trip. Tags are compared twice and results are
  multi-bit. A tag mismatch is the caller's error; any other failure makes the
  kernel revoke all owners and request a new key, as in C2.
- **Fallback.** Without SAES (D001) the same GCM records are sealed in software.
  F4 and the emulator keep SIV.
- **Heap.** GCM records carry an 8-byte nonce, so each value costs 16 B more
  than in SIV: 80 B for a 32-byte key, 112 B for a seed, 160 B for a node.
- **Storage key cache.** In the secure world of SAES builds the DEK/SAK cache is
  sealed the same way under a second DHUK-wrapped key (`vault_saes_storage()`),
  with its own per-boot nonce counter and the IV prefix `SK01`. No smcall
  reaches that key, so the kernel of a secmon model cannot use it. A cache
  wipe also drops the key. SAES builds then wrap nothing under the BHK, so
  secmon no longer exposes the `vault_kek_wrap` smcall.
- **Not verified on hardware.** The SAES driver path has only been compiled: wrapped-key
  loading followed by GCM with `pKey = NULL` and `CRYP_KEYNOCONFIG` follows the
  HAL's documented pattern, but has not run on hardware. The open question is
  whether switching `KEYSEL` from `CRYP_KEYSEL_HW` to `CRYP_KEYSEL_NORMAL` for
  the GCM pass clears the unwrapped key. If it does, the `KEYVALID` and
  round-trip checks fail closed: the vault refuses to seal, so U5 builds are
  unusable but not insecure. The likely fix is to keep `KEYSEL` at
  `CRYP_KEYSEL_HW` during the GCM pass.
- **Key and nonce lifetime.** On secmon models the record key lives in secmon
  and the GCM nonce counter in the kernel. Their lifetimes matched only because
  every kernel restart is a full MCU reset, which also clears secmon. The
  kernel now replaces the record key before its first record of every run
  (`f7934b6500`), so a restarted counter cannot meet an old key. A better fix
  is to let the secure world own the nonce: keep a counter in each SAES key
  slot, build the IV there on SEAL and return it for the record header, and
  reset it with the key. Then no kernel bug, restored counter or compromised
  secmon-model kernel can cause GCM nonce reuse, which would expose the XOR of
  two plaintexts and the GHASH key. The record format and smcall layout stay
  the same; the storage cache could drop its own counter the same way.

## Syscall timing

Up to C2, every vault syscall starts cold: the record keys are unwrapped (2 × 24
SAES block operations under the BHK in SIV, plus 4 SAES resets), two AES-256
schedules are expanded, and the records are opened and sealed in software AES
(about 16 blocks per node, 6 per 32-byte key). From C3 each record instead costs
one SAES key unwrap and one hardware GCM pass, plus an smcall on secmon models. EC operations also create and randomize a
ZKP context, one blinded generator multiplication with the 2 KiB table. A
5-level derivation pays this 5 times.

No timing has been measured on hardware. Build with the per-phase log and read
it from the VCP console:

```sh
nix-shell --run 'TREZOR_VAULT_TIMING=1 uv run xtask build firmware -m T3T1 -p test --dbg-console vcp --log-level info'
```

Each syscall then logs one line: `op ok ctx unwrap expand record/records op end
total`, in DWT cycles (160 MHz on U5). Without the variable no counter code is
built. The emulator reports zeros.

## Physical attacks

The vault adds an attacker-triggerable kernel operation with a distinct SAES
burst at a fixed offset before each secret is used. That gives a fault or
side-channel attacker a precise trigger and unlimited repetitions.

| Risk | Status |
| --- | --- |
| Skipped SIV tag check: CTR bit flips become a key-bit oracle | Mitigated in C2 by redundant checks; a second glitch is still possible |
| Skipped owner or unlock check | Mitigated in C2 by redundant checks |
| Skipped wipe leaves plaintext for a later RAM dump | Mitigated in C2 by wipe verification |
| Faulted signature reveals the key | Open: verify signatures before release |
| Altered key used after a double glitch | Open: compare the opened node's public key with its cached one |
| Power/EM analysis of software table AES with the per-boot record keys; inputs partly chosen (derivation paths, plaintext import) | Addressed on U5 by C3, which seals records and the storage key cache in SAES; not yet run on hardware |
| Repeated SAES unwraps of the same input give unlimited identical traces | Relies on SAES DPA countermeasures |
| Ed25519 has no scalar blinding | Pre-existing, now in the kernel |

## Potential improvements

The architecture stays: movable sealed records in coreapp, bounded owner state
in the kernel, and operations that return only public results or new records.
It needs no kernel allocation per secret and allows allocation-free holders.
SAES protects the record keys; wallet plaintext still exists briefly inside
kernel crypto operations, and coreapp supplies owner identities, so request
ownership manages lifetime but cannot stop compromised coreapp from asking for
signatures. In order of priority:

1. **Fixed: `ethereum_pubkeyhash()` (`af9c59efcb`).** A vault HDNode returned
   an all-zero address: the binding passed the public view, whose private key
   is zeroed, to `hdnode_get_ethereum_pubkeyhash()` and ignored its failure.
   It now hashes the public key the vault returns and raises on error, and a
   unit test checks the `m/44'/60'/0'/0/0` address of the "all" mnemonic.
   Ethereum and Tron signing and address display were blocked earlier anyway
   (canonical signing and SLIP-21 were not migrated), so no wrong address
   reached a user. Both are migrated now (`3497858812`, `db8479db0e`).
2. **Validate the SAES key path with a known key.** The new-key self-test
   proves that sealing and opening are consistent, but a consistently wrong key
   would pass too. A hardware test build should wrap a known key, compare
   ciphertext and tag with an independent GCM computation, and check wrong-key
   rejection and key replacement. This also settles the `KEYSEL` question,
   which the software stand-in cannot.
3. **Let the sealing key own its nonce.** One secure-world object per key holds
   the wrapped key, counter, exhaustion and failure state. SEAL allocates and
   returns the IV; OPEN takes the stored one. Key and counter can then never
   restart independently (GCM's uniqueness requirement,
   [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final)). A 32-bit
   counter with enforced exhaustion would then suffice.
4. **Derive whole paths in one operation.** `derive_path()` makes one syscall
   per index, and each repeats opening, ZKP context setup, fingerprinting,
   sealing and cleanup. A bounded `VAULT_DERIVE_PATH` fits the existing limit
   of 32 indexes (128 B of the 256 B request data): open once, derive, seal
   once, computing intermediate public keys only when derivation needs them.
   Today a failure partway leaves the node partly derived; committing only
   after the whole path succeeds is more predictable but changes behavior.
5. **Fetch the public view once.** `public_key()` and `serialize_public()` each
   make two `VAULT_PUBLIC` calls. Since `af9c59efcb` the kernel reports the
   node's curve and the shared `HDNode` view uses it instead of assuming
   secp256k1. Replacing the view with a dedicated public-information
   structure remains.
6. **Compact records only where it pays.** With 16 B GC blocks, a 12-byte GCM
   header (32-bit counter, after item 3) saves nothing for 32-byte keys
   (80 B) or 64-byte seeds (112 B) and 16 B per node (160 → 144 B). Dropping the
   33-byte cached public key from the 107-byte node encoding saves 32 B per
   node but costs a point multiplication per use. Keep the full tag and
   address-independent IVs; measure heap, signing latency and energy.
7. **Give sealed values a purpose.** Seeds, signing keys and MAC keys all use
   `SECRET_BYTES`, and a `private_key()` snapshot loses its node's curve, so
   one scalar can sign on any curve or key an HMAC. Authenticate a purpose in
   the existing kind byte, enforce it in the kernel, and sign directly from
   nodes for more algorithms to avoid snapshots.
8. **Narrow production capabilities.** Exclude ECB, which the build only warns
   about, and plaintext imports (`IMPORT_BYTES`, `IMPORT_NODE`,
   `from_seed(bytes)`) from production builds. Document that `destroy()`
   erases one copy and owner destruction revokes all. In `take()`, check the
   source record's length byte against the source allocation before copying:
   a corrupted record would otherwise make it read past the source object.

Suggested order after the fix in 1: hardware key validation (2), nonce ownership (3),
batched derivation and single public fetches (4, 5), measured compaction (6)
and purpose restrictions (7). Temporary-stack cleanup stays deferred.

## Limits and open gaps

| Gap | Proposal |
| --- | --- |
| ECB accepts relabelled and altered records | Remove it, or limit it to test builds |
| Copies of a record replay while the owner lives | Accept for immutable values; `destroy()` is not revocation |
| Owners are activated from a scheduler task table | Activate the scope in `with_context()` |
| C3's SAES path has not run on hardware; switching `KEYSEL` may clear the unwrapped key | Run the native and device suites on a U5 device; the self-test fails closed if the key is not loaded. If it fails, keep `KEYSEL` at `CRYP_KEYSEL_HW` for the GCM pass |
| The kernel chooses the GCM nonces for records sealed in secmon | Let the secure world own the nonce counter per key and return the IV on SEAL |
| Kernel stack headroom is 1,120 B on T3B1 and T3T1 | Measure the high-water mark on hardware; lower the 2,048 B Ed25519 bound if needed |
| Ed25519 messages over 2,048 B are refused | Chunked transfer into a bounded kernel buffer |
| Groestlcoin's curve is not on the vault allow-list; its signing fails | Add the curve or keep it on the legacy path |
| `IMPORT_BYTES`, `IMPORT_NODE` and `from_seed(bytes)` accept plaintext | Compile into test builds only |
| WebAuthn credential IDs and CredRandom still take the SLIP-21 key in coreapp | A kernel ChaCha20-Poly1305 operation for credential IDs; CredRandom through `hmac.tag` |
| A 64-byte seed record is accepted where `VAULT_SLIP21` expects a node | Outputs stay sealed; type records by purpose if that matters |
| Preauthorized flows (`DoPreauthorized`, CoinJoin) fail opening the seed | Retain the seed for the authorization's lifetime |
| SLIP39, Cardano, passphrase/PIN input, recovery | Remaining migration items |

Request and session owners are cooperative inside coreapp: compromised coreapp
can still ask the vault to sign with its own handles. Backup and recovery
display mnemonic words and are blocked by the storage deny-list; no
secret-display flow has been added. Nothing has run on hardware.

## Historical validation

At the original C2 checkpoint, T3T1:

- **Native.** ASan/UBSan suites pass in all three software sealing modes: 147
  AES-SIV Wycheproof vectors, every-byte tamper tests, storage key cache, P-256,
  Ed25519 and live-frame erasure checks. At C3 the `saes` mode also passes:
  record round trips at every length, tamper rejection, IV layout, multi-bit
  results, key failure and rekey, the dispatcher round trip, and the SAES
  storage key cache (separate key, nonces, every-byte tampering, wipe).
- **MicroPython.** 94 cases in 12 focused files pass on the emulator.
- **Device.** 96 passed, 12 skipped, 7 failed across Bitcoin message and
  transaction signing, Taproot and Solana. Six failures are Groestlcoin (curve
  not supported by the vault); one is the oversized Solana `large-multi` message.
- **ELF placement.** Passes for T3T1, and for T3W1 including the secmon storage
  cache; at C3 also no software record key or software cache path, both
  wrapped keys in secmon, and no BHK wrap smcall.
- **Builds.** The rebuilt stage tips are validated as described below. Every stage checkpoint builds for
  T2T1, T2B1, T3B1, T3T1 and T3W1. The emulator keeps SIV, so the MicroPython
  and device results above also hold at C3.

```sh
nix-shell --run 'uv run python core/tests/native/run_vault_tests.py --sanitize'
nix-shell --run 'uv run python core/tests/native/check_vault_elf.py \
  core/build/artifacts/T3W1/kernel.elf core/build/artifacts/T3W1/firmware.elf \
  --secmon core/build/artifacts/T3W1/secmon.elf'
./core/emu.py -h -t -P 38320 -q -c pytest \
  tests/device_tests/bitcoin/test_signmessage.py::test_signmessage
```

`--mode siv|gcm|ecb|saes` limits the native runner to one backend; `--sealing-only`
skips EC fixtures. The SHA-2 erasure test is
`core/tests/native/test_sha2_erasure.c`, built with and without
`-DSHA2_UNROLL_TRANSFORM`.
