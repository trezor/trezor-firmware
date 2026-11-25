# WARD adversarial testing

Tests that put the Trezor against a party that misbehaves on purpose: a host or replica serving
forged, stale or older data, or a WARD Manager signing what it should not. In each, the device
must refuse, and must say so, without moving its head. Setup and every other test are in
[WARD testing](ward_testing.md); the threats themselves are in the [threat model](threat_model.md).

## Setup

As in [WARD testing: Setup](ward_testing.md#setup): the two worktrees, a firmware shell with
`PYTHONPATH`, `ward_device_test` and `ward_unit_test`, and a connect-build T3T1 emulator.

The wardd methods below also need a wardd started with `--adversarial-tests`. The stack starts the
second device's wardd that way, and only that one:

```sh
node --import tsx $SUITE/packages/wardd/src/cli.ts --adversarial-tests ...   # prints:
ADVERSARIAL TESTS ENABLED: this wardd will serve older states on request
```

Without the flag, wardd refuses every `adversarial*` call with `bad_request`.

## Where the adversarial code lives

Each piece is marked with an `ADVERSARIAL TESTS` banner and every name starts with `adversarial`.

| Code | What it is |
| --- | --- |
| `$SUITE/packages/wardd/src/adversarial.ts` | the hostile behaviour; nothing in the normal paths imports it |
| `$SUITE/packages/wardd/src/server.ts` | the one gated block that dispatches the `adversarial*` calls |
| `$SUITE/packages/ward-core/src/relay.ts` | the two relay call names, documented as adversarial |
| `$FW/python/src/trezorlib/ward_adversarial.py` | the client helpers |
| `$FW/tools/ward_stack_adapter.py` | the "adversarial tests" phase of the stack |
| `$FW/tools/ward_shell.py` | `adversarial_older_head`, `adversarial_read` |

## wardd's adversarial methods

| Relay call | trezorlib | What wardd does | What the device must do |
| --- | --- | --- | --- |
| `adversarialCatchUpToOlderHead { counter }` | `ward_adversarial.adversarial_catch_up_to_older_head(session, client, counter)` | offers the head its own line passed through at `counter` as a `WardCatchUp` target | refuse before asking for any link: `WARD: the host offered head #N, older than this device's #M`; the caller gets `device_failure` |
| `adversarialServeEntry { request, counter }` | `ward_adversarial.AdversarialOlderTreeProvider(client, counter)` as the read's provider | answers the pull with a proof from the tree at `counter` | refuse the read: `WARD: entry does not match the trusted root` |

`counter` must be below wardd's current head. Both are logged in `wardd2.log` as
`ADVERSARIAL TEST: ...`. On the device, `emulator2.log` shows the refusal:

```
catch-up REFUSED: the host offered head #7, older than the stored #10
read REFUSED: entry=6694f89fdefe: the entry does not prove against the trusted root
```

## In the stack

`python tools/ward_stack.py` runs the adversarial phase after device 2 has stored head #10 and
caught up to #11 without the WM. With the WM down, device 2's wardd turns hostile:

- **ADVERSARIAL: an older head (#7) is refused.** wardd offers device 2 the head at #7.
- **ADVERSARIAL: a read answered from the tree at #7 is refused.** wardd answers a read of `q0` with
  a proof from the tree at #7.

The phase cannot be run alone: it needs the two devices, the conflicts and the catch-ups before it.
Run the whole stack, headless if no windows are wanted:

```sh
python tools/ward_stack.py --headless --once
grep -E "ADVERSARIAL|REFUSED" RUN_DIR/adapter.log RUN_DIR/wardd2.log RUN_DIR/emulator2.log
```

## Interactively, in a shell

With the stack running (see [WARD testing: Interactive testing](ward_testing.md#interactive-testing-in-a-shell)):

```sh
python -i tools/ward_shell.py RUN_DIR
```

```python
d2.status()                        # the head wardd serves, e.g. counter 13
d2.new_session()                   # the attack is a catch-up target: a session with no attested head
d2.adversarial_older_head(7)       # REFUSED -- ... older than this device's #N
d2.adversarial_read("contact2", 9) # REFUSED -- ... entry does not match the trusted root
d2.get("contact2")                 # the honest read still works
```

In a session that already synced, `adversarial_older_head` is refused earlier, with "this session
already has a WM-attested head": catch-up is only for a session without the WM.

Other attacks to try by hand, with only the ordinary commands:

| Attack | How | Expected |
| --- | --- | --- |
| Hide the WM so reads cannot be fresh | `wm_down(); d1.new_session(); d1.get("contact3")` | shown, but as "Unverified entry" with "Not reflecting changes since <date> UTC, nor user reverts." |
| Write while the WM is away | `wm_down(); d1.put("x", "1")` | `REFUSED: wm_unavailable`; the device's head does not move |
| Read a newer tree in a session that did not catch up to it | after `d2.catch_up()` in one session: `d2.new_session(); d2.get(...)` an entry changed since the stored head | `REFUSED`: the session proves against the stored head |

## Automated adversarial tests

Every automated test whose name or summary names a hostile input: forged, tampered, rolled back,
older, stale, replayed, another path, nonce, signer or wallet, a step from elsewhere, and similar.
The commands run exactly that test, from the shell the section names in [WARD testing:
Setup](ward_testing.md#setup). The complete list of tests is the [test
catalogue](ward_testing.md#test-catalogue).

### `core/tests/test_apps.ward.py` (83)

- **`TestWardTrie.test_membership_against_a_wrong_root_fails`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_membership_of_a_mutated_leaf_fails`** — Any edit to the sealed content changes the commitment, hence the leaf and root; so does moving it to another path.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_relabelled_split_bit_is_rejected`** — THE malleability attack, and the reason split_bit is inside the node hash.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_an_archived_attestation_cannot_be_re_dated`** — WHY THE COUNTER SITS BESIDE THE ROOT, stated as the attack it prevents.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_production_key_is_unprovisioned`** — Shipping with a placeholder is correct: a device that accepted a WM key from whoever offered one would be checking freshness against an adversary's clock.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_the_predecessor_is_bound_too`** — The whole point of naming a step rather than a head: an attestation for the same destination but a different origin is a different statement, so a host cannot pair one with a link that merely ends in the right place.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_every_signed_field_is_bound`** — Changing anything the signature covers must break it -- notably the nonce, which is what stops a host stockpiling anchors and replaying one later.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_another_signer_is_refused`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_preimage_names_both_endpoints`** — Binding only the destination would let a link be lifted out of its place in the history and replayed after a different predecessor -- which is what a chain exists to prevent.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_the_backward_chain_refuses_an_ORPHANED_candidate`** — THE PROPERTY THE BACKWARD WALK EXISTS FOR, and the forward fold does not have.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_the_backward_chain_refuses_every_way_of_lying_with_real_links`** — The mirror of the forward case: authentic links, wrong placement.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_the_chain_refuses_every_way_of_lying_with_real_links`** — Each link here is individually authentic; only its placement is wrong.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_it_binds_both_endpoints`** — Binding only the destination would let an authorisation be lifted out of its place and replayed after a different predecessor -- exactly what a predecessor check must prevent.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_another_wallet_cannot_use_it`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_head_init_cannot_be_replayed_as_an_advance`** — Its own tag, so the authorisation that opens a wallet's history cannot be re-presented as a step within it.
  `ward_unit_test test_apps.ward.py`

### `core/tests/test_apps.ward.settle.py` (8)

- **`TestWardClaimSettlement.test_a_multi_step_jump_is_not_decidable_and_stays_queued`** — The head moved several counters and one root cannot say where this claim sits.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_another_wallets_claim_is_untouched`** — Settlement is scoped by wallet_id, which is what stops one wallet's reconciliation from rewriting another's queued records.
  `ward_unit_test test_apps.ward.settle.py`

### `core/tests/test_apps.ward.store.py` (29)

- **`TestWardStore.test_wallets_cannot_see_each_others_records`** — A passphrase switch must not surface another wallet's entry at the same path.
  `ward_unit_test test_apps.ward.store.py`

### `core/tests/test_trezor.wire.codec.ward_context.py` (14)

- **`TestWardCodecExchange.test_a_stale_answer_is_dropped_and_its_lease_given_back`** — An answer to a question that already gave up must not become the NEXT question's.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`

### `tests/device_tests/misc/test_ward.py` (190) — connect build (T3T1)

- **`test_ward_rejects_a_tampered_leaf`** — A leaf the host edited is refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_tampered_leaf"`
- **`test_ward_rejects_a_leaf_served_from_another_path`** — The host answers a request for one entry with a different entry's real leaf.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_leaf_served_from_another_path"`
- **`test_ward_delete_entry_still_refuses_an_unproved_absence`** — Idempotence rests on the proof, so an unwitnessed denial is still refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_entry_still_refuses_an_unproved_absence"`
- **`test_ward_rejects_a_rolled_back_leaf`** — The host serves an OLDER version of an entry it really did hold once.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_rolled_back_leaf"`
- **`test_ward_rejects_an_unproved_denial`** — The host hides an entry by claiming it holds none.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_an_unproved_denial"`
- **`test_ward_refuses_an_attestation_from_the_wrong_signer`** — Only the provisioned WM key counts.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_an_attestation_from_the_wrong_signer"`
- **`test_ward_refuses_an_attestation_bound_to_another_nonce`** — A stockpiled anchor is useless: the signature is bound to a nonce the device minted for THIS round, which the WM could not have known in advance.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_an_attestation_bound_to_another_nonce"`
- **`test_ward_refuses_a_link_into_a_head_the_wm_did_not_attest`** — The LINK is what binds the WM's claim to actual contents.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_link_into_a_head_the_wm_did_not_attest"`
- **`test_ward_refuses_an_attested_counter_below_the_floor`** — Anti-rollback.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_an_attested_counter_below_the_floor"`
- **`test_ward_reconcile_refuses_a_multi_step_jump`** — RECONCILE ADOPTS AT MOST ONE STEP, and names the route that adopts more.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_reconcile_refuses_a_multi_step_jump"`
- **`test_ward_reconcile_refuses_a_step_from_elsewhere`** — ONE STEP IS NOT ENOUGH; it has to be one step FROM HERE.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_reconcile_refuses_a_step_from_elsewhere"`
- **`test_ward_a_write_authorises_its_advance_to_the_wm`** — CONNECT-MODE WRITES CARRY `wm_sig`, which is what lets a WM refuse an unauthorised advance.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_write_authorises_its_advance_to_the_wm"`
- **`test_ward_the_wm_refuses_an_unauthorised_advance`** — The other half of the same property, asserted where it bites: at the WM.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_the_wm_refuses_an_unauthorised_advance"`
- **`test_ward_refuses_a_different_state_at_the_same_counter`** — One counter names one state.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_different_state_at_the_same_counter"`
- **`test_ward_an_attestation_cannot_be_adopted_twice`** — The round closes on adoption, so a replayed reconcile has nothing to act on.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_an_attestation_cannot_be_adopted_twice"`
- **`test_ward_catch_up_refuses_a_head_older_than_the_stored_one`** — Serving a device an older head without the WM is detected before any link is asked.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_a_head_older_than_the_stored_one"`
- **`test_ward_catch_up_refuses_a_head_the_wm_never_attested`** — A LOST RACE, or a head built from authorisations that were never published: every link is genuine, but no WM signature names the head, so the device does not read from it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_a_head_the_wm_never_attested"`
- **`test_ward_catch_up_refuses_an_attestation_older_than_the_stored_head`** — THE TIMESTAMP FLOOR: every head on a branch a revert removed was attested before that revert, so an attestation older than the stored head's is refused before any link is asked.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_an_attestation_older_than_the_stored_head"`
- **`test_ward_without_the_wm_a_read_from_an_older_tree_is_refused`** — The other way to serve an older root: answer a read with a proof from an earlier tree.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_without_the_wm_a_read_from_an_older_tree_is_refused"`
- **`test_ward_catch_up_refuses_a_chain_that_does_not_reach_the_stored_head`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_a_chain_that_does_not_reach_the_stored_head"`
- **`test_ward_refuses_a_chain_that_does_not_start_at_its_own_head`** — The baseline is the device's own head, never one the host names.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_chain_that_does_not_start_at_its_own_head"`
- **`test_ward_refuses_an_unauthorised_link`** — Without K_auth a link cannot be minted, so the host cannot invent a step.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_an_unauthorised_link"`
- **`test_ward_refuses_a_chain_that_ends_somewhere_else`** — Descent is not currency.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_chain_that_ends_somewhere_else"`
- **`test_ward_a_device_on_a_lost_branch_cannot_catch_up`** — The gap WardRejoin exists for: the walk reaches this device's counter at another root.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_device_on_a_lost_branch_cannot_catch_up"`
- **`test_ward_rejoin_refuses_a_forged_link`** — Neither branch can be invented: every link needs K_auth, which the host does not hold.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_refuses_a_forged_link"`
- **`test_ward_scenario_wm_behind_to_an_older_tree_discards_its_entries`** — The same recovery onto an OLDER tree: the entries it lacks are gone, as the screen warned.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_scenario_wm_behind_to_an_older_tree_discards_its_entries"`
- **`test_ward_a_batch_link_cannot_jump_over_the_devices_head`** — SKIP-OVER SPLICING, the attack a variable-length step makes possible, refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_batch_link_cannot_jump_over_the_devices_head"`
- **`test_ward_attack_recovery_replay`** — RECOVERY REPLAY: the host re-presents a recovery that already happened.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_recovery_replay"`
- **`test_ward_attack_fork_and_switch`** — FORK & SWITCH: the host tries to move the device onto a branch the WM never accepted.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_fork_and_switch"`
- **`test_ward_attack_splicing_unrelated_genuine_transitions`** — SPLICING: stitch a genuine link from elsewhere into the walk, where its ends seem to fit.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_splicing_unrelated_genuine_transitions"`
- **`test_ward_attack_pending_revert_authorization`** — A REVERT the user approved but the host never published is a live authorisation -- until the wallet moves.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_pending_revert_authorization"`
- **`test_ward_attack_multiple_approved_demotions`** — TWO APPROVED DEMOTIONS: the host cannot land the one the user approved FIRST.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_multiple_approved_demotions"`
- **`test_ward_attack_a_write_from_an_ended_session_is_refused`** — THE HOST HOLDS A WRITE BACK AND SYNCS THE DEVICE AGAIN: the held write is dead.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_a_write_from_an_ended_session_is_refused"`
- **`test_ward_attack_another_devices_sync_ends_this_devices_session`** — THE SAME, WITH ANOTHER DEVICE OF THE WALLET SYNCING IN BETWEEN.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_another_devices_sync_ends_this_devices_session"`
- **`test_ward_attack_a_forged_retry_is_refused`** — A host cannot skip the confirmation by inventing a retry:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_a_forged_retry_is_refused"`
- **`test_ward_a_write_is_bound_to_the_latest_sync`** — The device binds to the nonce of the LATEST attestation it verified, not an earlier one: after two syncs, the write's `wm_sig` verifies under the second nonce only.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_write_is_bound_to_the_latest_sync"`
- **`test_ward_attack_a_revert_from_an_ended_session_is_refused`** — A DEMOTION THE USER APPROVED, HELD BACK PAST A NEW SYNC: refused like any other write.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_a_revert_from_an_ended_session_is_refused"`
- **`test_ward_attack_roll_forward_needs_a_detected_restore`** — Not in a round whose attestation did not find the WM behind:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_needs_a_detected_restore"`
- **`test_ward_attack_roll_forward_needs_the_wms_record`** — A step the WM never recorded as accepted -- a lost race, a write held back -- is not signed again:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_needs_the_wms_record"`
- **`test_ward_attack_roll_forward_needs_the_devices_own_mac`** — The WM's record alone is not enough either:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_needs_the_devices_own_mac"`
- **`test_ward_attack_roll_forward_starts_at_the_attested_head`** — The first step must start at the head the WM attests in this round, and each next one where the previous ended:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_starts_at_the_attested_head"`
- **`test_ward_attack_roll_forward_refuses_a_branch_off_this_devices_history`** — Genuine steps on another branch -- made by this wallet and accepted by a WM -- that reach this device's counter with another root are not signed again:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_refuses_a_branch_off_this_devices_history"`
- **`test_ward_pin_rejects_a_forged_leaf`** — A leaf the wallet never sealed fails its tag, and NOTHING is stored.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pin_rejects_a_forged_leaf"`
- **`test_ward_pin_rejects_a_leaf_that_is_not_in_the_trusted_root`** — Once the device holds a root, membership is required -- authenticity is not enough.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pin_rejects_a_leaf_that_is_not_in_the_trusted_root"`
- **`test_ward_one_wallet_does_not_settle_anothers_queued_change`** — Reconciling one hidden wallet must not touch another wallet's queued records.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_one_wallet_does_not_settle_anothers_queued_change"`
- **`test_ward_a_tampered_backup_is_refused_before_any_screen`** — EVERY field the device would write back is inside the MAC.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_tampered_backup_is_refused_before_any_screen"`
- **`test_ward_a_demotion_from_a_regressed_wm_records_the_wm_predecessor`** — The recorded link must name the head the REVERT was minted over, not the store's.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_demotion_from_a_regressed_wm_records_the_wm_predecessor"`

### `tests/device_tests/ward/test_ward_service_publish.py` (6) — service build

- **`test_an_attestation_for_another_head_is_refused`** — The check that makes this route stronger than reconcile.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_an_attestation_for_another_head_is_refused"`

### `tests/device_tests/ward/test_ward_service_sync.py` (9) — service build

- **`test_another_wallet_is_not_served_from_this_replica`** — A hidden wallet against a daemon that holds a different wallet's replica: refused.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_another_wallet_is_not_served_from_this_replica"`

### `tests/test_ward_wm.py` (29) — the mock WARD Manager

- **`test_an_authorisation_moves_the_head_at_most_once`** — THE PREDECESSOR CHECK, stated as the attack it closes.
  `pytest "tests/test_ward_wm.py::test_an_authorisation_moves_the_head_at_most_once"`
- **`test_a_new_sync_ends_the_session`** — An authorisation minted in one sync is refused once any device of the wallet syncs again:
  `pytest "tests/test_ward_wm.py::test_a_new_sync_ends_the_session"`
- **`test_only_a_fresh_device_proof_can_replace_the_write_session`** — Reads and consumed opening proofs preserve the current write session.
  `pytest "tests/test_ward_wm.py::test_only_a_fresh_device_proof_can_replace_the_write_session"`
- **`test_a_restored_wm_refuses_the_devices_authorisations`** — The session nonce is volatile, so a restore ends every session:
  `pytest "tests/test_ward_wm.py::test_a_restored_wm_refuses_the_devices_authorisations"`
- **`test_a_lost_race_has_no_record_to_be_signed_again_from`** — Two devices mint from the same head; one lands.
  `pytest "tests/test_ward_wm.py::test_a_lost_race_has_no_record_to_be_signed_again_from"`
- **`test_a_restored_wm_can_be_stopped_at_any_prefix`** — THE COST that remains:
  `pytest "tests/test_ward_wm.py::test_a_restored_wm_can_be_stopped_at_any_prefix"`
- **`test_a_re_enrolled_wm_refuses_a_kept_first_write`** — `head_init_sig` is not secret, so a WM that lost everything can be enrolled again at genesis.
  `pytest "tests/test_ward_wm.py::test_a_re_enrolled_wm_refuses_a_kept_first_write"`
- **`test_an_unauthorised_transition_is_refused`** — The WM verifies with `ward_id` alone -- no enrolment, and no second per-wallet secret.
  `pytest "tests/test_ward_wm.py::test_an_unauthorised_transition_is_refused"`

### `packages/ward-core/src/__tests__/serve.test.ts` (5)

- **`refuses a batch that does not start at the store counter`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts -t 'refuses a batch that does not start at the store counter'`

### `packages/ward-core/src/__tests__/wm.test.ts` (10)

- **`advances on a genuine wm_sig, and refuses a replay`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'advances on a genuine wm_sig, and refuses a replay'`
- **`accepts a batch of up to MAX_BATCH and a revert, and refuses a forged step`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'accepts a batch of up to MAX_BATCH and a revert, and refuses a forged step'`

### `packages/wardd/src/__tests__/host.test.ts` (38)

- **`refuses a result minted on a head that has since moved, and stores nothing of it`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result minted on a head that has since moved, and stores nothing of it'`
- **`refuses a result at the right counter but minted over a different root`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result at the right counter but minted over a different root'`
- **`refuses a sync from a device on another wallet`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a sync from a device on another wallet'`

- **`refuses a result minted before the same device synced again`** — a transition is invalidated by a new sync.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result minted before the same device synced again'`
- **`refuses a result once another device of the wallet has synced`** — a transition is invalidated by a new sync.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result once another device of the wallet has synced'`
- **`is refused by the WM itself when a host skips its own check`** — a transition is invalidated by a new sync.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is refused by the WM itself when a host skips its own check'`
- **`is not signed again by a device whose own head is off the replayed chain`** — roll-forward through the device.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is not signed again by a device whose own head is off the replayed chain'`
- **`the device refuses a forged or misplaced WM record, and signs nothing`** — roll-forward through the device.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'the device refuses a forged or misplaced WM record, and signs nothing'`

### `packages/wardd/src/__tests__/service.test.ts` (10)

- **`ADVERSARIAL: refuses a publish whose session a later sync ended`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'ADVERSARIAL: refuses a publish whose session a later sync ended'`


### `packages/wardd/src/__tests__/replica.test.ts` (8)

A peer holding the wallet's Evolu owner key stores corrupt rows on purpose. It can always deny service by deleting or withholding rows; these pin that corrupt rows do no more than that.

- **`rewriting a stored row under its id costs that head, and never walks a device back`** — A peer overwrites a genuine row's changes: the replica falls back one head, and the device holding the newer head refuses the older one.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "rewriting a stored row under its id costs that head, and never walks a device back"`
- **`a tower of corrupt rows stacked above the head does not hide it`** — Thirty chained corrupt rows: only the first is replayed and left out; nothing above it reaches genesis.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "a tower of corrupt rows stacked above the head does not hide it"`
- **`a corrupt second path into the real head is passed over for the genuine one`** — A newer corrupt row ending at the real head is tried first, left out, and the device walks the genuine chain.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "a corrupt second path into the real head is passed over for the genuine one"`
- **`with a WM, corrupt rows above its head do not move the head the replica serves`** — The replica is built at the WM's head, so corrupt rows above it are never replayed.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "with a WM, corrupt rows above its head do not move the head the replica serves"`

### `packages/wardd/src/__tests__/server.test.ts` (10)

- **`refuses the ADVERSARIAL TEST methods unless started with --adversarial-tests`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'refuses the ADVERSARIAL TEST methods unless started with --adversarial-tests'`
- **`serves an older state on request, and the device refuses it`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'serves an older state on request, and the device refuses it'`

### `packages/wardd/src/__tests__/wmServer.test.ts` (10)

- **`refuses a stale advance as a conflict`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'refuses a stale advance as a conflict'`
