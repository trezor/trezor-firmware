# WARD batch-update — security review

Security review of the proposed **batch-update** protocol (multiple queued intents committed as one
authenticated root transition; another Trezor of the same wallet verifies a transition was
Trezor-authorized and that the Evolu payload is complete; resistance to stale-base, host-rewrite,
split-batch, unwanted-delete, and rollback attacks).

This review reconciles **three** models that currently diverge:

1. **`ward-design.md` (target spec):** a single **Ed25519 `K_sig`** (WARD ID = its public key) signs
   CAS commits `0x10‖root_prev‖root_new‖C_new‖t_anchor` and rollbacks
   `0x11‖root_stuck‖root_prev‖C_stuck+1‖t_anchor`. WM is a pure freshness/non-omission register.
   Batch is *the* write primitive. Roots are content-addressed. **Rollback increments the counter.**
2. **Current implementation:** a single symmetric device HMAC
   `mac = HMAC(mac_key, wallet_id‖counter‖root)` (`mac_key = HMAC(SLIP21(seed,["AUTHDB MAC v1",
   domain]), wallet_id)`), plus WM Ed25519 ATTEST/FINAL (device verifies only). **One leaf per
   commit, `counter += 1`, no batch, no rollback, no fast-forward, no on-device lineage
   verification.** No WM server in-repo (host is a pure signer-client reacting to a 409).
3. **Proposed batch doc:** shared symmetric **`K_head` + `K_auth`** MACs, a `batch_digest`, WM as CAS
   register **+ history witness (`PrevAttest`)**, and a **backward-counter rollback** (to_counter =
   predecessor).

Severity: **HIGH** = exploitable integrity / anti-rollback break; **MED** = weakens a guarantee or a
defense-in-depth layer; **LOW** = documented residual / implementation-discipline requirement.

---

## Anti-rollback findings

### F1 (HIGH) — post-rollback authorization replay ("root resurrection")

The proposed backward-counter rollback sets the WM head counter *backward* to the predecessor
(`to_counter < from_counter`). Because `AuthCommit` binds only
`(ward_id, from_counter, from_root, to_counter, to_root[, batch_digest])` with **no monotone
epoch / `t_anchor`**, and because roots are content-addressed (they repeat when contents repeat —
`ward-design` §2.4), counters now recur. Concretely:

- Head at `(C=4, R4)`. User commits batch `B1` → `(C=5, R5)`, authorized by `AuthCommit_1` over
  `(4,R4)→(5,R5)`. WM head is `(5,R5)`.
- User rolls back to `(4,R4)`. WM head is `(4,R4)` again.
- `AuthCommit_1` is **still MAC-valid** and its `from`-coordinates `(4,R4)` match the current head.
  A malicious host replays it to WM; the successor check (`from==head`, `to_counter>from_counter`)
  passes → **the head is re-driven into the reverted batch `B1` with no device re-approval.**

This is exactly the "root resurrection" attack `ward-design` §2.4/§8.2 closes by making rollback
**increment** the counter (`C_stuck+1`) so old coordinates can never recur.

**Resolution (decided):** rollback is **forward-incrementing** — head → `(C_stuck+1, root_prev)` —
so the counter is strictly monotone across rollbacks and a stale `from_counter` can never match the
head again. See "Why `t_anchor`/epoch were dropped" below.

### F6 (MED) — WM history / `PrevAttest` breaks the trust boundary

`ward-design` §0/§2.4/§6 scope WM to **freshness and non-omission only** ("cannot forge state") and
make the **device signature chain the sole authenticated lineage**; WM-committed history / gossip was
"considered and rejected" (§6). Having WM sign lineage facts (`PrevAttest`) so the rollback
predecessor is authenticated *by WM* pushes WM past a pure register.

**Resolution:** authenticate the rollback predecessor from the **device family's own forward
`AuthCommit`/`K_sig` signature** (which already contains `root_prev`), exactly as `ward-design` §8.2
does. Treat any WM-stored history as an unauthenticated hint (like `parent_hash`/`target_hash`).

---

## Malicious-host findings

### F2 (was HIGH) — MOOT: `batch_digest` dropped

The original finding: canonicalizing `batch_digest` by writer-local `pending_id` and encoding
`base_counter` (Intent = `(pending_id, entry_key, op, value, base_counter)`) is **not
reconstructable** by another Trezor, because Evolu is keyed by `entry_key`, not `pending_id`, and a
verifier has neither the writer's `pending_id`s nor its `base_counter`s — so it cannot recompute the
digest to check `AuthCommit`.

**Resolution — `batch_digest` is dropped entirely (verified safe).** Under content-addressed roots
it is redundant with `to_root`:

- The trie root is a **collision-resistant commitment to the entire leaf set**, and the trie is a
  pure function of its contents (§2.4/§4.4). So `(from_root → to_root)` **uniquely determines** the
  logical batch (the set-difference of two committed leaf sets). There is no second logical batch
  from `from_root` reaching the same `to_root` (that would be a SHA-256 collision).
- The **device itself computes `to_root` locally** from the user-approved queued intents (§4.6). So
  `AuthCommit` over `to_root` already means *"this device applied the exact user-approved batch and
  reached this exact successor from this exact predecessor."*

Every attack `batch_digest` was meant to close is already closed without it:

| Attack | Closed by (no `batch_digest`) |
| --- | --- |
| Host swaps in a different write-set | `to_root` differs → needs a `K_auth` forgery; device only MACs a `to_root` it computed itself |
| Partial / tampered payload published | Reader replay reconstructs root ≠ `to_root` → rejected (§7 step 4). Replay, not a digest, enforces completeness |
| Replay old `AuthCommit` after rollback | Counter monotonicity (F1, forward-increment) — `from_counter` never matches the head again |
| Concurrent devices, same `from_root` → different `to_root` | WM successor-only CAS accepts one; loser rebases |
| Reassemble records from different historical batches | Any payload with `target_hash=to_root` must replay from `from_root` to `to_root`; only the genuine leaves do |
| "Logical intent" ambiguity (approved X, recorded as Y) | No distinct batch from `from_root` reaches the same `to_root`; user-facing binding is the on-device semantic confirmation (§9), not an on-wire digest |

Dropping it also makes verification **cheaper** (a verifier checks one MAC over the coordinate tuple
instead of recomputing an accumulator over all changed records). The only thing lost is a marginal
defense-in-depth binding that would matter solely under SHA-256 root collisions or if roots were ever
*not* content-addressed (§2.4 guarantees they are). Independent write-time checks remain mandatory:
per-leaf `C_new > C_old` (F12) and duplicate-`entry_key` rejection.

`AuthCommit` therefore binds `(ward_id, from_counter, from_root, to_counter, to_root)` only.

### F3 (was MED) — MOOT: resolved by dropping `batch_digest`

The concern was that a digest binding insertion order would conflict with §4.4/§7 order-independence
("reordering the published records is a no-op"; "order within a batch is irrelevant"). With
`batch_digest` dropped and `root_new` (content-addressed, order-independent) the sole authorized
value, there is no conflict.

### F4 (MED) — symmetric-only auth loses WM / third-party verifiability

With `K_auth` only, WM **cannot** verify `AuthCommit` (no `K_auth`), so WM stores any
structurally-valid transition and an unauthorized one is caught only later by another Trezor.
`ward-design`'s Ed25519 `K_sig` (WARD ID = pubkey) is both seed-shared across the family **and**
publicly verifiable, so WM can **reject unauthorized transitions at ingest** (defense in depth) and
any party can audit lineage — same family-only *authoring*, keyless *verification*.

**Resolution (decided):** ship the Ed25519 `K_sig` path in parallel behind a build flag
(`WARD_KSIG`) so a hardened WM *can* pre-filter, and so both can be benchmarked (MAC-only vs
MAC+signature). Symmetric `K_head`/`K_auth` remain mandatory.

### F7 (MED) — "replay before delete" protects the queue, not the WM head

Replay-before-delete correctly prevents wrongful queue deletion after a WM advance, but it does
**not** stop a malicious host from advancing WM to a `(to_counter, to_root)` the device cannot
reproduce → the device is "stuck ahead" → torn state (§4.3) requiring rollback. Also, "the previous
approval becomes invalid" needs a mechanism: a static MAC does not self-invalidate — that safety
relies on the F1 counter monotonicity (a stale approval can never re-match the head).

---

## Consistency / residual findings

### F5 (MED) — `head_mac` / `K_head` is integrity, not freshness

`head_mac = MAC(K_head, ward_id‖counter‖root)` is a static token with no nonce input, so it is
**replayable** for any recurring `(counter, root)` and establishes integrity, not currency. §2.5
warns that a symmetric MAC on the root invites treating the root as self-authenticating — "precisely
the mistake §2.4 and §8.2 exist to prevent." Keep `head_mac` only as a **counter-bound** integrity
token, never checked by root alone. Freshness stays on the WM nonce challenge.

### F8 (LOW) — read / head-serving freshness stays on the WM nonce path

Anti-rollback for reads (a malicious host serving a stale-but-authentic head) depends on the device's
nonce challenge + counter/timestamp monotonicity (§3.1/§6.1): the Trezor generates `nonce_read`, WM
signs `nonce_read‖C_latest‖root_head‖timestamp`, and the device checks `C_latest ≥ C_last`.
`head_mac` cannot substitute (no nonce).

### F9 (LOW) — wiped / restored device (SUNDR residual)

A freshly wiped device has no `C_last` and accepts any historical `(C, root)` from a malicious WM
with a fresh nonce signature. Inherited from `ward-design` §6.4; mitigations: second-device
fingerprint compare, multi-WARD k-of-n, or a user-recorded counter. Not closed by the batch protocol.

### F10 (LOW) — key derivation / rotation / signing-oracle discipline

`K_head`/`K_auth` (and config-gated `K_sig`) must be SLIP-21 domain-separated under `m/"ward"` (like
`K_index`/`K_data`), **never exposed via any generic "sign arbitrary bytes" API** (§1), and — being
seed-shared — cannot be rotated without re-authenticating history. Domain-separation tags
`TAG_HEAD`/`TAG_COMMIT`/`TAG_REVERT` must be disjoint from each other and from the ATTEST/FINAL and
read-challenge preimages.

### F11 (LOW) — batch atomicity ceiling (semantic tear)

A change set larger than the batch cap (§4.7, e.g. 50 leaves) splits across multiple CAS operations;
a host can stop mid-way, leaving a **semantically torn** state (§4.8). A per-transition authorization
does not fix cross-batch tears. If a single logical operation can exceed the cap, add the §4.8
intent-marker leaf (first batch names the total count + change-set digest; final batch clears it).

### F12 (LOW) — per-leaf counter monotonicity + random nonces (preserve)

The writing Trezor must decrypt each old leaf and enforce `C_new > C_old` **for every leaf in the
batch** before authorizing (§4.5, leaf-splicing defense), and nonces must be random per write
(rollback makes `(entry_key, C_leaf)` recur; a derived nonce would reuse under a fixed key and break
Poly1305). The current one-leaf implementation already does both — the batch path must preserve them
across all N leaves.

---

## Why `t_anchor` / epoch were dropped

`t_anchor` (the WM-attested commit time bound into the CAS signature in `ward-design` §1/§8.2) served
two roles, **neither of which is the core replay defense**:

1. **Rollback-age display (§8.2/§9):** the destructive rollback prompt shows `t_anchor_now − t_stuck`
   so a deep silent rewind reads as an implausible age ("created 3 months ago") to the human present
   at the prompt.
2. **Timestamp-monotonicity freshness (§6.1):** rejects an honest-but-broken / partitioned WM that
   regresses the clock; catches operator restore-from-backup.

The **replay defense (F1) is the counter**, not `t_anchor`. With **forward-incrementing** rollback
(head → `(C_stuck+1, root_prev)`), the tree counter is strictly monotone across rollbacks, so it *is*
the anti-replay epoch and closes F1 without `t_anchor` or a separate `epoch`.

**Cost of dropping `t_anchor`:** no age-based deep-rewind signal at the rollback prompt (the
one-step + counter-equality structural constraints still hold) and no clock-monotonicity freshness on
sync. **Epoch:** with forward-increment the tree counter already serves as the monotone anti-replay
sequence, so a separate `epoch` is redundant. A documented hook remains to add an explicit monotone
`epoch` only if a backward-counter rollback mode is ever reintroduced.

---

## Locked design decisions

- **D1 — Auth primitive:** symmetric **`K_head` + `K_auth`** MACs mandatory; Ed25519 `K_sig` present
  but config-gated (`WARD_KSIG`) to benchmark MAC-only vs MAC+signature (F4).
- **D2 — Rollback counter:** forward-increment, no `t_anchor` (F1 closed by counter monotonicity).
- **D3 — Scope:** firmware batch-commit primitive first (§4.1/§4.2), then host batching, then WM CAS,
  then cross-device verify + rollback.
- **D4 — `batch_digest`:** dropped (F2/F3 moot); `AuthCommit` binds coordinates only.

## Preimages (domain-separated)

```
head_mac   = MAC(K_head, TAG_HEAD   ‖ ward_id ‖ counter      ‖ root)
AuthCommit = MAC(K_auth, TAG_COMMIT ‖ ward_id ‖ from_counter ‖ from_root ‖ to_counter ‖ to_root)
AuthRevert = MAC(K_auth, TAG_REVERT ‖ ward_id ‖ from_counter ‖ from_root ‖ to_counter ‖ to_root)
# config-gated parallel benchmark path (WARD_KSIG):
SigCommit  = Ed25519(K_sig, TAG_COMMIT ‖ … same preimage as AuthCommit …)
```

`to_counter = from_counter + 1` for a whole batch (the counter is a transition/head-generation
counter — a batch of any n leaves is one transition). Every leaf in a batch shares `C_leaf =
to_counter`; per-leaf `C_new > C_old` still holds since any leaf's prior `C_old ≤ from_counter <
to_counter`. Rollback: also `to_counter = from_counter + 1`, `to_root = root_prev` (forward-increment,
D2) — so every head move (commit or rollback) is a uniform +1.
