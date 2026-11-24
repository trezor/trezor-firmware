# WARD testing

How to set up, run and read every WARD test: the automated suites, the end-to-end stack, and
interactive testing from a shell. Tests that put the device against a hostile host, replica or
WARD Manager are collected in [WARD adversarial testing](ward_adversarial_testing.md).

## Setup

### Checkouts

| Repository | Branch | Worktree (`$FW`, `$SUITE` below) |
| --- | --- | --- |
| trezor-firmware | `petrsusil/ward-draft` | `trezor-firmware/.worktrees/ward-draft` |
| trezor-suite | `petrsusil/ward-draft` | `trezor-suite-petrsusil/.worktrees/ward-draft` |

```sh
export FW=~/GitHub_authdb/trezor-firmware/.worktrees/ward-draft
export SUITE=~/GitHub_authdb/trezor-suite-petrsusil/.worktrees/ward-draft
```

Once per checkout:

```sh
# firmware: the worktree has no virtualenv of its own; it uses the main checkout's
(cd ~/GitHub_authdb/trezor-firmware && uv sync)
cd "$FW" && git -c protocol.file.allow=always submodule update --init --recursive

# Suite
cd "$SUITE" && yarn install
```

### Every firmware shell

```sh
cd "$FW"
nix-shell
source ~/GitHub_authdb/trezor-firmware/.venv/bin/activate
export PYTHONPATH=$PWD/python/src   # this branch's trezorlib, not the main checkout's

# The venv's `xtask` builds the MAIN checkout. This one builds the worktree:
xtask_draft() { python -c 'import sys; sys.path.insert(0, "core/tools"); from trezor_core_tools.xtask import main; sys.exit(main())' "$@"; }

# Runs pytest node ids against a throwaway emulator (temporary profile, its own port block).
EMU=${EMU:-core/build-xtask/artifacts/T3T1/firmware-emu}
ward_device_test() { ./core/emu.py --executable "$EMU" -h -t -P 38000 -q -c pytest -p no:cacheprovider "$@"; }

# Runs firmware unit-test FILES inside the emulator binary.
ward_unit_test() { (cd core/tests && MICROPYTHON="$FW/$EMU -X heapsize=2M" TREZOR_PROFILE_DIR="$(mktemp -d)" ./run_tests.sh "$@"); }
```

### Emulator builds

Every build writes `core/build-xtask/artifacts/<MODEL>/firmware-emu`, so building another variant
replaces the previous one of the same model.

| Build | Command | Used by |
| --- | --- | --- |
| Connect build | `xtask_draft build firmware --emulator -m T3T1 -p test --frozen false` | unit tests, most device tests, the stack |
| Service build | the same, plus `--enable-ward-service-channel` | `tests/device_tests/ward/test_ward_service_*` |
| THP service build | `-m T3W1` and `--enable-ward-service-channel --ward-service-thp` | `tests/device_tests/thp/*`, with `EMU=core/build-xtask/artifacts/T3W1/firmware-emu` |
| MVP build (no WM) | the connect build, plus `--ward-without-wm` | tests marked `ward_wm("without")`; every other WARD test skips |

The builds are not frozen: firmware Python edits are picked up when the emulator restarts. A new
or changed protobuf message needs a rebuild, because message definitions are compiled in. Switching
`--ward-without-wm` on or off also needs the upymod build cache removed first
(`rm -rf core/build-xtask/{debug,release}/build/upymod-* core/build-xtask/{debug,release}/deps/*upymod*`),
or the emulator keeps the previous `utils.USE_WARD_WM`.

### Suite shell

```sh
cd "$SUITE"
```

## Running everything

| What | Command | Shell |
| --- | --- | --- |
| Firmware unit tests | `ward_unit_test test_apps.ward*.py test_storage.cache_thp_ward_service.py test_trezor.wire.codec.ward_context.py` | firmware |
| Device tests, connect build (about 18 minutes) | `ward_device_test tests/device_tests/misc/test_ward.py tests/device_tests/misc/test_display_address.py tests/device_tests/ward/test_ward_app_role_v1.py` | firmware |
| Device tests, service build | `ward_device_test tests/device_tests/ward` | firmware |
| Device tests, THP | `EMU=core/build-xtask/artifacts/T3W1/firmware-emu ward_device_test tests/device_tests/thp -k ward` | firmware |
| trezorlib, launcher and mock WM | `WARDD_SUITE_DIR=$SUITE pytest python/tests/test_ward_trie.py python/tests/test_ward_relay.py tests/test_ward_stack.py tests/test_ward_wm.py` | firmware |
| ward-core, wardd | `yarn workspace @trezor/ward-core test:unit --coverage=0` and `yarn workspace @trezor/wardd test:unit --coverage=0` | Suite |
| End-to-end stack, no windows | `python tools/ward_stack.py --headless --once` | firmware |

`python/tests/test_ward_relay.py` runs part of its tests against the real wardd only when
`WARDD_SUITE_DIR` points at the Suite worktree; without it those are skipped.

## The end-to-end stack

`tools/ward_stack.py` starts every component in its own terminal, each with its own log in the run
directory it prints:

| Terminal | Log | What it is |
| --- | --- | --- |
| Evolu relay (database) | `relay.log` | the relay the replicas sync through; logs each message stored and retrieved |
| WARD Manager | `wm.log` | `packages/wardd/src/wmCli.ts`; logs every enrolment, attestation and advance |
| wardd | `wardd.log` | device 1's daemon; logs every call and each replica rebuild |
| Trezor emulator | `emulator.log` | device 1; WARD lines only, unless `--emulator-full-log` |
| wardd (second device) | `wardd2.log` | device 2's daemon, idle until the adapter starts it; runs with `--adversarial-tests` |
| Trezor emulator (second device) | `emulator2.log` | device 2, the same wallet (SLIP-14 seed) |
| WARD adapter | `adapter.log` | `tools/ward_stack_adapter.py`: the scripted session below |

```sh
python tools/ward_stack.py                       # terminals, emulator displays shown
python tools/ward_stack.py --confirm-delay 1     # leave each screen up for a second
python tools/ward_stack.py --headless --once     # no windows; stop after one session
python tools/ward_stack.py --full-log            # also merge every log into full.log
tools/ward_stack.py --stop RUN_DIR               # stop it from anywhere
```

In the adapter's terminal, Enter reruns the session and `q` stops the stack. In the WARD Manager's
terminal, Enter stops the WM and Enter again starts it; creating or removing `RUN_DIR/wm.down` does
the same.

The steps cannot be run one by one: each builds on the state the previous ones left. A run prints
`ok` or `FAIL` for each:

**one session through wardd**

1. store opened
1. synced with the WM
1. entry written and adopted
1. entry read back on screen
1. the WM attested this session's head: no freshness warning
1. pointer written and adopted
1. pointer read follows one hop to the target's value
1. entry updated and adopted
1. pointer sees the update
1. three queued changes flushed as one batch
1. entry deleted and adopted
1. pointer to a deleted entry reads as not found
1. replica and WM agree

**the same device with the WM down**

1. WM taken down
1. wardd reports the WM unavailable
1. sync without the WM fails
1. read proves against the last adopted head, with the warning

**a second device, and conflicting changes queued offline**

1. second device started: its own wardd and emulator
1. device 2's wardd filled its replica from the relay, without the WM
1. device 2 caught up without the WM
1. device 2 reads what it caught up to, under the warning
1. both devices queued contact1 and contact2 offline, with different values
1. WM back up
1. device 1 flushed its queue: one transition with both contacts
1. the WM accepted it
1. the relay stored it (Evolu)
1. device 2's wardd received device 1's transition from the relay
1. device 2 synced to the WM head
1. device 2 was shown both conflicts
1. contact1 resolved KEEP ORIGINAL, contact2 KEEP NEW: one transition
1. device 2 reads contact1 = alice_from_A (original kept)
1. device 2 reads contact2 = bob_from_B (new kept)
1. device 2's queued contact1 became an offline copy of the original
1. device 1 reads contact1 = alice_from_A
1. device 1 reads contact2 = bob_from_B, fresh
1. both wardd replicas and the WM agree

**device 1 moves on; device 2 without the WM**

1. device 1 progressed: contact3 written
1. WM taken down
1. device 2's wardd received it from the relay
1. device 2 caught up #10 -> #11 without the WM
1. device 2 reads contact3, not proven current

**adversarial tests (wardd serves an older state)**

1. ADVERSARIAL: an older head (#7) is refused
1. ADVERSARIAL: a read answered from the tree at #7 is refused
1. WM back up

**add an entry, then delete it**

1. a write from the session before the WM restart is refused
1. entry added: the root moved
1. entry deleted: device 1 adopted the root from before the add
1. device 2's replica rebuilt the same root from the relay

**the WM restored from a backup, rolled forward**

1. WM restored from the backup at #10 (taken when both replicas and the WM agreed)
1. device 1 detected the restored WM during sync, and the user approved
1. device 1 signed #10 -> #13 again; the WM accepted them
1. device 1 showed when the WM accepted the last restored change
1. the WM is back at #13, and the replica agrees
1. device 1 adopted it: the next sync just reconciles

The launcher itself is tested without opening windows by `tests/test_ward_stack.py`, listed below.

## Interactive testing in a shell

Start the stack, then open a Python shell on it with the run directory it printed. Every screen is
confirmed over debuglink and printed; with `--manual`, confirm on the emulator display yourself.

```sh
python tools/ward_stack.py --confirm-delay 1          # note the run directory
python -i tools/ward_shell.py /tmp/ward-stack-XXXXXXXX
```

| Command | What it does |
| --- | --- |
| `d1.sync()` | sync device 1 with the WM and adopt its head |
| `d1.put("contact", "alice")` | write an entry, have wardd store and publish it, sync |
| `d1.point("alias", "contact")` | write a pointer |
| `d1.get("contact")` | read an entry; the screen shows the value, and the warning when not fresh |
| `d1.delete("contact")` | delete an entry |
| `d1.queue("contact", "bob")` | queue a change on the device, offline |
| `d1.local("contact")` | read the device's own copy, with no host |
| `d1.flush()` | publish the queue; conflicts are asked on the device |
| `d1.status()` | wardd's replica head, the WM's head, and whether the WM is reachable |
| `d1.new_session()` | a fresh session: no attested head until it syncs |
| `wm_down()`, `wm_up()` | stop and start the WARD Manager |
| `start_second()` | start device 2 and its wardd, if the adapter has not |
| `d2.catch_up()` | follow the wallet's chain without the WM, to the newest head a WM attestation wardd kept names |
| `d2.answer("ward_conflict_keep_new", False)` | decline the next "Keep your value?" question |

A refused operation prints `REFUSED` with the device's reason instead of raising.

### Recipes

**Freshness.** A read is fresh only in a session that adopted a WM-attested head.

```python
d1.sync(); d1.get("contact3")          # "Entry", no warning
wm_down(); d1.new_session()
d1.sync()                              # REFUSED: wm_unavailable
d1.get("contact3")                     # "Unverified entry", "Not reflecting changes since <date> UTC, nor user reverts."
wm_up(); d1.sync(); d1.get("contact3") # fresh again
```

**Catch up without the WM.** The new head is used for this session only.

```python
wm_down(); d1.put("x", "1")            # REFUSED: a write needs the WM
wm_up(); d1.put("x", "1"); wm_down()
d2.new_session(); d2.catch_up()        # device 2 follows the chain to device 1's head, which the WM attested
d2.get("x")                            # the value, under the warning dated by that attestation
d2.new_session(); d2.get("x")          # REFUSED: this session proves against the stored head again,
                                       # and wardd serves the newer tree
```

**Conflicting offline changes.** Both devices change the same entry while offline.

```python
wm_down()
d1.new_session(); d2.new_session()
d1.queue("contact9", "from_1"); d2.queue("contact9", "from_2")
wm_up(); d1.sync(); d1.flush()                 # device 1 publishes first
d2.status()                                    # wait until its counter is d1.status()["counter"]:
                                               # wardd2 receives the transition through the relay
d2.sync()
d2.answer("ward_conflict_keep_new", False)     # keep the original: decline "Keep your value?"
d2.flush()                                     # then confirm "Keep published value?"
d2.get("contact9")                             # from_1
```

Answer `True` (or nothing) to keep device 2's value instead. The emulator logs say what each device
queued, the conflict and how it was resolved:

```sh
grep apps.ward RUN_DIR/emulator2.log
```

**Add, then delete.** The root after the delete equals the root before the add.

```python
before = d1.status()["root"]
d1.put("temp", "short_lived"); d1.delete("temp")
d1.status()["root"] == before          # True
```

## End-to-end scripts in Suite

Two scripts in `packages/connect-cli/e2e` drive real firmware through connect-cli. They start their
own emulator, so stop the stack first: they use the default ports.

| Script | What it covers | Run (from `$FW`, after building the stated emulator) |
| --- | --- | --- |
| `ward-wardd.sh` | wardd as the local WARD service on a connect build: sync, queue, flush (single and batched), a second emulator of the same wallet catching up through the Python and Rust bindings, the Java binding reading the same store | `python3 core/emu.py -q -a -t -s -c bash $SUITE/packages/connect-cli/e2e/ward-wardd.sh` |
| `ward-queue.sh` | the device's own queue: queue, show, back up, discard, restore; on a service build also the online half against `ward-service-daemon.py` | `python3 core/emu.py -q -a -t -s -c bash $SUITE/packages/connect-cli/e2e/ward-queue.sh` |

Each script's header states which build it needs.

## Test catalogue

Every automated test, what it checks, and the command that runs exactly that test. Run the
commands from the shell their section names (Setup).

### Firmware unit tests

MicroPython tests run inside the emulator binary. The runner takes whole files, so each command below runs the file that holds the test; the test is reported by name in its output.


#### `core/tests/test_apps.ward.canonicity.py` (3)

Run the file: `ward_unit_test test_apps.ward.canonicity.py`

- **`TestWardTrieCanonicity.test_derived_root_matches_a_rebuild_and_reaches_the_hard_shapes`** — Every op in every geometry lands on the canonical root -- and the sweep is required to have reached the shapes that have actually broken.
  `ward_unit_test test_apps.ward.canonicity.py`
- **`TestWardTrieCanonicity.test_a_delete_needs_nothing_but_its_proof`** — What the sibling-kind witness used to be needed for, and no longer is.
  `ward_unit_test test_apps.ward.canonicity.py`
- **`TestWardTrieCanonicity.test_the_model_agrees_with_the_firmware_on_an_empty_tree`** — Both sides must spell "empty" the same way, or D2 reopens on one of them.
  `ward_unit_test test_apps.ward.canonicity.py`

#### `core/tests/test_apps.ward.handlers.py` (4)

Run the file: `ward_unit_test test_apps.ward.handlers.py`

- **`TestWardHandlerWiring.test_every_ward_request_resolves_to_a_callable`**
  `ward_unit_test test_apps.ward.handlers.py`
- **`TestWardHandlerWiring.test_the_set_of_dispatched_ward_messages_is_exactly_this_list`** — Guards both directions, which one list alone cannot.
  `ward_unit_test test_apps.ward.handlers.py`
- **`TestWardRevealPolicy.test_every_revealing_message_reaches_the_filter`**
  `ward_unit_test test_apps.ward.handlers.py`
- **`TestWardRevealPolicy.test_the_revealing_set_is_exactly_this_list`** — Pinned by name, so adding a handler that shows a stored value is a deliberate act.
  `ward_unit_test test_apps.ward.handlers.py`

#### `core/tests/test_apps.ward.py` (82)

Run the file: `ward_unit_test test_apps.ward.py`

- **`TestWardKeys.test_frozen_vectors`** — Pins the keyed path byte-for-byte against the reference implementation.
  `ward_unit_test test_apps.ward.py`
- **`TestWardKeys.test_scope_layout`** — The offline store's record name (not the trie path): scope = app_id \|\| 0x00 \|\| key_type \|\| 0x00 \|\| device_id(1B).
  `ward_unit_test test_apps.ward.py`
- **`TestWardKeys.test_scope_rejects_nul`** — The delimiters are only unambiguous while the fields cannot contain them.
  `ward_unit_test test_apps.ward.py`
- **`TestWardKeys.test_scope_rejects_out_of_range_device_id`** — device_id occupies exactly one byte, so a wider value has no encoding.
  `ward_unit_test test_apps.ward.py`
- **`TestWardKeys.test_nul_in_app_id_is_unambiguous`** — leaf_identity length-prefixes every field, so NUL is ordinary data in app_id too: the re-split that the offline store's NUL-delimited scope must refuse cannot happen here.
  `ward_unit_test test_apps.ward.py`
- **`TestWardKeys.test_identifier_may_contain_nul`** — identifier is the terminal field, so NUL in it is unambiguous and allowed.
  `ward_unit_test test_apps.ward.py`
- **`TestWardKeys.test_domain_separation`** — Changing any leaf_identity field must change the path.
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_known_answer`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_pack_layouts`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_non_canonical_identity_is_refused`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_pack_identity_rejects_oversized_fields`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_parts_are_bound_to_key_domain_and_bytes`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_empty_value_is_not_a_delete`** — b"" is a present value: its sealing is non-empty.
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_fresh_nonce_per_write`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardLeaf.test_only_the_sealed_content_is_committed`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_bit_order_is_msb_first`** — bit 0 is the TOP bit of byte 0.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_frozen_membership_proof`** — The sealed content, the proof and the root, byte-for-byte across implementations.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_frozen_nonmembership_proof`** — Absence is proved by the leaf that occupies the absent key's path.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_membership_against_a_wrong_root_fails`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_membership_of_a_mutated_leaf_fails`** — Any edit to the sealed content changes the commitment, hence the leaf and root; so does moving it to another path.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_witness_equal_to_target_proves_nothing`** — Otherwise a membership proof would double as a proof of absence.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_false_absence_by_boundary_shift_is_rejected`** — A PRESENT key proved absent, using its own membership proof.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_preimage_operands_are_fixed_width`** — The same ambiguity, in every other preimage that concatenates opaque bytes.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_relabelled_split_bit_is_rejected`** — THE malleability attack, and the reason split_bit is inside the node hash.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_proof_shape_is_enforced`** — A proof must describe a real root-to-leaf path before anything is hashed.
  `ward_unit_test test_apps.ward.py`
- **`TestWardTrie.test_proof_length_is_bounded_by_the_key_space`** — No cap is needed: split_bit is one byte and strictly increases, so a valid proof cannot exceed 256 elements however many the host sends.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_first_insert_needs_an_empty_device`** — With no proof and no witness the device's own record is the only authority.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_update_must_prove_the_current_leaf`** — A host cannot swap a value without first proving what is there now.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_delete_promotes_the_sibling_unchanged`** — The collapsing sibling takes the branch's place with its hash untouched.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_emptying_the_tree_yields_a_root_that_says_so`** — Deleting the last entry gives EMPTY_ROOT, never None.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_an_emptied_tree_accepts_a_first_insert_again`** — ...and EMPTY_ROOT still counts as empty where that matters.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_an_empty_tree_holds_nothing_to_replace`** — An update or a delete against an empty tree is refused, not silently derived.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_delete_promotes_a_branch_sibling_unchanged`** — THE case this module used to get wrong, twice.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_insert_above_an_existing_branch`** — The second bug: the new key parts from its witness inside a COMPRESSED run.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_insert_below_the_witness_path`** — The simpler case: the keys part deeper than every existing branch.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_reconstruct_refuses_wrong_width_operands`** — Checked in the fold itself, so no future caller can forget.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_insert_refuses_a_wrong_width_witness`** — A DataError, not an IndexError: the read path that would have caught it first is skipped on a fresh device and an emptied tree, so insert checks for itself.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_insert_witness_must_prove_absence_against_the_device_root`** — Each failed claim raises, through the same check the read path uses.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_an_unsettled_root_is_refused_not_read_as_empty`** — None is "cannot verify", and `root_for_write` refuses it before the trie is reached.
  `ward_unit_test test_apps.ward.py`
- **`TestWardComputeNewRoot.test_root_for_write_never_reads_none_as_empty`** — Not even at counter 0: that is this device's floor, and a second device of a wallet with history starts there too.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_an_archived_attestation_cannot_be_re_dated`** — WHY THE COUNTER SITS BESIDE THE ROOT, stated as the attack it prevents.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_debug_key_matches_its_seed`** — The compiled debug pubkey really is this seed's, or every test below is vacuous.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_production_key_is_unprovisioned`** — Shipping with a placeholder is correct: a device that accepted a WM key from whoever offered one would be checking freshness against an adversary's clock.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_the_empty_tree_is_attestable_too`** — An absent root encodes as EMPTY_ROOT rather than being skipped, so "empty" is still a state the WM can attest at a given counter -- otherwise it could not name one at all, and a wallet with nothing in it could never be synced.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_attestation_preimage_layout`** — Both ends, in order, at fixed width -- and the version byte that says so.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_the_predecessor_is_bound_too`** — The whole point of naming a step rather than a head: an attestation for the same destination but a different origin is a different statement, so a host cannot pair one with a link that merely ends in the right place.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_genesis_attests_itself`** — Counter 0 has no predecessor, so the step is `(0, empty) -> (0, empty)`.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_a_genuine_attestation_verifies`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_every_signed_field_is_bound`** — Changing anything the signature covers must break it -- notably the nonce, which is what stops a host stockpiling anchors and replaying one later.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_another_signer_is_refused`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_a_zero_signature_never_verifies`** — Not paranoia.
  `ward_unit_test test_apps.ward.py`
- **`TestWardAttestation.test_a_malformed_signature_is_refused`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_a_claim_distinguishes_two_candidates_at_one_counter`** — What the counter-path settlement in `offline_store.reconcile_pending` now rests on.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_empty_root_sentinel`** — A root inside a preimage is fixed-width, so the empty tree needs an encoding no real root can take.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_preimage_names_both_endpoints`** — Binding only the destination would let a link be lifted out of its place in the history and replayed after a different predecessor -- which is what a chain exists to prevent.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_every_field_is_bound`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_a_revert_is_not_a_commit`** — Same endpoints, different meaning.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_a_genuine_chain_folds_to_its_head`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_a_genuine_chain_folds_BACKWARDS_to_its_tail`** — The direction `verify_chain` actually walks.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_the_backward_chain_refuses_an_ORPHANED_candidate`** — THE PROPERTY THE BACKWARD WALK EXISTS FOR, and the forward fold does not have.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_a_batch_link_folds_in_both_directions`** — One transition carrying MAX_BATCH changes is a single genuine step, either way.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_the_backward_chain_refuses_every_way_of_lying_with_real_links`** — The mirror of the forward case: authentic links, wrong placement.
  `ward_unit_test test_apps.ward.py`
- **`TestWardCas.test_the_chain_refuses_every_way_of_lying_with_real_links`** — Each link here is individually authentic; only its placement is wrong.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_a_signature_verifies_against_ward_id_alone`** — `ward_id` IS the verifying key, so a WM needs nothing but the identifier it keys by.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_it_binds_both_endpoints`** — Binding only the destination would let an authorisation be lifted out of its place and replayed after a different predecessor -- exactly what a compare-and-swap must prevent.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_another_wallet_cannot_use_it`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_head_init_cannot_be_replayed_as_an_advance`** — Its own tag, so the authorisation that opens a wallet's history cannot be re-presented as a step within it.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_the_tag_is_the_only_thing_separating_the_two_authenticators`** — WHAT CHANGED, AND WHY THIS TEST STILL MATTERS.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_operands_must_be_fixed_width`** — Same reason as everywhere else in WARD: a short operand lets the preimage be re-split.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_known_answer`** — Fixed vectors, so this agrees with `tests/ward_keys.py` -- which implements the same two preimages independently, over `trezorlib._ed25519` rather than the crypto module.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_a_malformed_signature_is_refused_not_raised`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardRecordCommit.test_the_flags_are_normalised_out`** — A record is marked OFFERED after its claim is filed and loses PENDING when the claim settles, so a commitment covering the flags would stop matching the record it was filed for -- and the claim would silently decline to settle anything.
  `ward_unit_test test_apps.ward.py`
- **`TestWardRecordCommit.test_the_value_and_the_identity_are_covered`** — The point of the commitment.
  `ward_unit_test test_apps.ward.py`
- **`TestWardRecordCommit.test_a_change_of_form_is_a_different_record`** — Compact and full records name the same entry differently, and a claim filed against one must not settle the other: the form is part of what was offered.
  `ward_unit_test test_apps.ward.py`
- **`TestWardRecordCommit.test_it_is_stable`** — Re-encoding the same record must produce the same commitment, or a claim would never match the record it was filed for.
  `ward_unit_test test_apps.ward.py`
- **`TestWardSealedPartIsStrict.test_short_or_unknown_scheme_is_refused`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardSealedPartIsStrict.test_an_empty_part_is_a_delete`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardDemotionConsent.test_it_matches_only_the_transition_that_was_approved`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardDemotionConsent.test_it_stops_matching_once_the_device_has_moved`** — THE BUG THIS CLOSES, stated as the sequence that reaches it.
  `ward_unit_test test_apps.ward.py`
- **`TestWardDemotionConsent.test_one_hold_buys_one_descent`**
  `ward_unit_test test_apps.ward.py`
- **`TestWardDemotionConsent.test_an_absent_authorisation_matches_nothing`** — Absent is the safe answer, and it is what an unset cache slot reads back as.
  `ward_unit_test test_apps.ward.py`
- **`TestWardWmAuthorisation.test_it_is_bound_to_the_session_nonce`** — An authorisation is good only for the sync it was minted in:
  `ward_unit_test test_apps.ward.py`

#### `core/tests/test_apps.ward.service.py` (12)

Run the file: `ward_unit_test test_apps.ward.service.py`

- **`TestWardServiceBinding.test_nothing_is_bound_to_begin_with`**
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceBinding.test_every_field_comes_back`** — The interface number is part of it on purpose: a channel id can be closed and reallocated on a DIFFERENT interface, so the id alone cannot answer "is this still my service?".
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceBinding.test_it_can_be_forgotten`**
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceBinding.test_a_full_width_channel_id_survives`** — Two bytes, so the top of the range must not be truncated.
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_it_asks_the_service_and_returns_the_answer`**
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_an_answer_on_another_session_is_refused`** — A reply carrying someone else's session id is not this conversation's reply, and acting on it would mean acting on a message meant for something else.
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_an_unexpected_type_is_refused`** — Not interpreted, not ignored: the daemon is the only party on this channel, so a surprise means the conversation has desynchronised.
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_no_answer_fails_closed`** — A daemon that stops answering must not hang the workflow the user is waiting on.
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_an_unbound_service_is_not_asked`**
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_fetch_names_the_head_the_device_holds`** — HEAD-AWARE, which is the whole difference from the connect-mode request.
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_fetch_refuses_rather_than_serving_an_unverifiable_proof`** — `WardSyncRequired` is an answer, not a failure -- but it is not a VALUE either, and the direction matters: a read that fell back to anything else would be a way to force an old value onto the screen.
  `ward_unit_test test_apps.ward.service.py`
- **`TestWardServiceRpc.test_fetch_syncs_once_and_then_gives_up`** — ONE SYNC AND ONE RETRY.
  `ward_unit_test test_apps.ward.service.py`

#### `core/tests/test_apps.ward.service_messages.py` (9)

Run the file: `ward_unit_test test_apps.ward.service_messages.py`

- **`TestWardServiceMessages.test_every_service_message_is_reachable_by_wire_id`** — The device resolves a wire id to a class, so a mismatch between the enum and the generated class is what would break decoding -- and nothing else would notice.
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_the_open_handshake_round_trips`**
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_a_sync_exchange_round_trips`**
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_an_empty_chain_is_distinguishable`** — No links is the ordinary "nothing changed" answer, not a malformed one.
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_a_fetch_names_the_head_it_asks_about`**
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_the_sync_required_answer_round_trips`**
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_a_publish_carries_both_authenticators`** — `auth_commit` is for another device of this wallet; `wm_sig` is for the WM.
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_a_publish_outcome_round_trips_either_way`**
  `ward_unit_test test_apps.ward.service_messages.py`
- **`TestWardServiceMessages.test_the_wallet_host_results_carry_no_leaf`** — The point of these being separate messages: an emptied `WardLeafAck` would be read by the host as a DELETION, so a service build must answer with a different type entirely.
  `ward_unit_test test_apps.ward.service_messages.py`

#### `core/tests/test_apps.ward.settle.py` (8)

Run the file: `ward_unit_test test_apps.ward.settle.py`

- **`TestWardClaimSettlement.test_a_lost_race_leaves_the_change_queued`** — THE BUG 3a9ca2ebbf FIXED, stated as the scenario that produces it.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_a_won_race_settles_the_change`** — The converse, and the reason "never settle without a chain" was not the answer.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_a_multi_step_jump_is_not_decidable_and_stays_queued`** — The head moved several counters and one root cannot say where this claim sits.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_a_verified_chain_settles_by_its_own_authorisation`** — The precise path: the caller crossed the transitions and says which.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_another_wallets_claim_is_untouched`** — Settlement is scoped by wallet_id, which is what stops one wallet's reconciliation from rewriting another's queued records.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_an_unreadable_record_is_warned_about_then_skipped`** — One corrupt record must not block every sync, but it is skipped only after a warning.
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_declining_the_warning_changes_nothing`**
  `ward_unit_test test_apps.ward.settle.py`
- **`TestWardClaimSettlement.test_named_tells_a_corrupt_entry_from_another_unreadable_record`** — `get` says CORRUPT for both; only `named` says which one an erase would remove.
  `ward_unit_test test_apps.ward.settle.py`

#### `core/tests/test_apps.ward.store.py` (29)

Run the file: `ward_unit_test test_apps.ward.store.py`

- **`TestWardStore.test_a_record_survives_a_reboot_byte_for_byte`** — The whole point of flash over the session cache.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_wallets_cannot_see_each_others_records`** — A passphrase switch must not surface another wallet's entry at the same path.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_both_wallets_survive_switching_across_reboots`** — Write A, cycle, write B, cycle, and both are still there.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_full_store_refuses_and_keeps_everything`** — Full means full: the write fails and not one existing record moves.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_full_store_still_accepts_a_replacement`** — Being full blocks NEW records, not updates to ones already held.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_an_unknown_version_is_not_findable_by_identity`** — The frozen-prefix contract, and the boundary between its two lookups.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_deleting_frees_the_slot_and_leaves_neighbours_alone`**
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_deleting_something_that_is_not_there_is_a_no_op`**
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_listing_is_scoped_to_one_wallet`** — Enumeration is where a missing filter leaks another hidden wallet's existence.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_replacement_keeps_the_slot_it_had`** — A record is addressed by its slot, and a rewrite must not move it.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_both_forms_live_in_one_pool_and_are_found_by_their_own_name`** — A compact record is a different VERSION with a different key, in the same slot pool.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_record_may_change_form_in_place`** — Rewriting an entry compactly must TAKE OVER its slot, not leave the old form behind.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_records_never_collide_with_root_slots`** — The two key ranges are disjoint, and a root write must not disturb a record.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_root_slot_keeps_the_wm_timestamp_beside_the_head`** — The WM's timestamp for the adopted head dates the warning a read without the WM shows, and floors which cached attestation `WardCatchUp` accepts.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_wallet_setting_is_its_own_and_gives_its_slot_back`** — Off by default, per wallet, and a wallet with nothing turned on holds no slot.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_record_header_must_name_its_own_wallet_and_key`** — A mismatched header is a programming error, not a recoverable state.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_compact_record_is_scoped_by_its_name_alone`** — No wallet tag, so the NAME has to do the scoping -- and it does, being a hash over wallet_id.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_the_stored_wallet_tag_is_truncated_and_that_is_deliberate`** — Records key on the FIRST 7 BYTES of wallet_id; root slots keep all 16.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_the_byte_budget_binds_before_the_slots_do`** — Big records run out of BYTES long before they run out of slots, and that is the point.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_replacement_pays_only_the_difference`** — Otherwise a store near its budget could not shrink a record -- the write would be refused for space the record it replaces was already using.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_longer_replacement_is_refused_when_it_no_longer_fits`** — The same identity again with a BIGGER record, at a budget that cannot take the difference.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_record_past_the_cap_is_refused`** — The capacity guarantee is per RECORD, not per value.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_operands_are_checked`** — The wallet_id is fixed-width; the identity is variable but never empty.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_an_unreadable_record_is_findable_by_slot_and_removable`** — The other half of the frozen header: a record whose IDENTITY cannot be parsed.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_root_write_reports_whether_it_landed`** — A full root store REFUSES, and says so, rather than silently doing nothing.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_claim_round_trips_and_is_scoped_to_its_wallet`** — The journal's slot layer: persistence, wallet scoping, and refusal to overflow.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_claims_survive_a_reboot_and_cover_every_record_slot`** — Claims are in flash BECAUSE the session is where they used to be lost.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_a_claim_rejects_operands_of_the_wrong_width`** — A short claim would parse into plausible-looking garbage, so it never gets written.
  `ward_unit_test test_apps.ward.store.py`
- **`TestWardStore.test_freeing_a_record_slot_drops_its_claim`** — A claim that survives always names the entry it was filed for.
  `ward_unit_test test_apps.ward.store.py`

#### `core/tests/test_storage.cache_thp_ward_service.py` (6)

Run the file: `ward_unit_test test_storage.cache_thp_ward_service.py`

- **`TestWardServiceSession.test_it_is_recognisable_and_not_a_wallet_session`**
  `ward_unit_test test_storage.cache_thp_ward_service.py`
- **`TestWardServiceSession.test_an_ordinary_session_is_not_mistaken_for_it`**
  `ward_unit_test test_storage.cache_thp_ward_service.py`
- **`TestWardServiceSession.test_it_is_reachable_by_pointer_after_the_fact`** — How the service is found: by (channel, session) recovered from a stored pointer, not by whichever channel is currently being served.
  `ward_unit_test test_storage.cache_thp_ward_service.py`
- **`TestWardServiceSession.test_only_one_service_session_exists_at_a_time`** — A second open replaces the first rather than accumulating.
  `ward_unit_test test_storage.cache_thp_ward_service.py`
- **`TestWardServiceSession.test_it_survives_pressure_that_evicts_wallet_sessions`** — THE POINT OF THE EXEMPTION.
  `ward_unit_test test_storage.cache_thp_ward_service.py`
- **`TestWardServiceSessionState.test_the_state_is_distinct`**
  `ward_unit_test test_storage.cache_thp_ward_service.py`

#### `core/tests/test_trezor.wire.codec.ward_context.py` (14)

Run the file: `ward_unit_test test_trezor.wire.codec.ward_context.py`

- **`TestWardCodecContext.test_unsolicited_traffic_never_reaches_the_shared_buffer`** — The reason there are two sources at all.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecContext.test_the_tier_is_chosen_when_the_message_arrives_not_when_the_read_starts`** — The race that a flag consulted before the wait could not win.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecContext.test_a_lease_taken_during_an_rpc_goes_back_after_it`** — `holds_shared`/`release` must follow the POOLED tier, not the active one.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecContext.test_it_carries_what_a_service_link_is_read_for`** — `apps.ward.service._rpc` logs and tears down through these on EITHER transport.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecContext.test_the_endpoint_has_no_session`** — `wardd` must not create or activate a protocol-v1 wallet session.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecReaderSurvives.test_an_unexpected_exception_does_not_stop_the_reader`** — `FirmwareError` and `MemoryError` are not `WireError`, and used to escape.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecReaderSurvives.test_a_teardown_reaches_a_read_already_in_progress`** — The hole this pair of mechanisms exists to close.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_the_request_goes_out_and_the_answer_comes_back`**
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_an_exception_in_the_mailbox_is_raised_at_the_caller`** — How a mangled frame fails the operation AT ONCE rather than at its deadline.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_a_second_question_in_flight_is_refused`** — One stream and no request ids: two questions would make the two answers indistinguishable.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_the_flag_is_cleared_even_when_the_write_fails`** — Otherwise the reader would keep routing into a mailbox nobody reads, and the interface would never bootstrap again -- a service that is gone with nothing to say so.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_a_stale_answer_is_dropped_and_its_lease_given_back`** — An answer to a question that already gave up must not become the NEXT question's.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_tearing_down_frees_the_endpoint_to_be_bound_again`** — No channel closes, and that is the point: the reader keeps reading, so a daemon that restarts announces itself and is heard.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`
- **`TestWardCodecExchange.test_without_a_reader_there_is_nothing_to_ask`** — Reachable for real: the reader is torn down and respawned on every MicroPython session restart, so this is a state an operation can meet.
  `ward_unit_test test_trezor.wire.codec.ward_context.py`

### Device tests

pytest against a throwaway emulator (`ward_device_test`, see Setup). A test written for another build is reported as skipped, not failed.


#### `tests/device_tests/misc/test_ward.py` (185) — connect build (T3T1)

Run the file: `ward_device_test tests/device_tests/misc/test_ward.py`

- **`test_ward_pull_names_only_the_opaque_key`** — The request must carry a 32-byte key and NOTHING that reveals the entry.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pull_names_only_the_opaque_key"`
- **`test_ward_pull_key_is_the_expected_hmac`** — The key is not merely opaque, it is the RIGHT 32 bytes.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pull_key_is_the_expected_hmac"`
- **`test_ward_pull_key_is_deterministic_and_domain_separated`** — Same (app_id, identifier) -> same key; different app_id -> different key.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pull_key_is_deterministic_and_domain_separated"`
- **`test_ward_leaf_round_trips_through_the_host`** — A leaf the device built, stored verbatim by the host, decodes back to the same value when the device reads it again.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_leaf_round_trips_through_the_host"`
- **`test_ward_leaf_is_sealed_and_hides_what_it_holds`** — What the host ends up holding must reveal neither the identifier nor the value.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_leaf_is_sealed_and_hides_what_it_holds"`
- **`test_ward_sealed_leaf_really_contains_the_preimage`** — ...and it is genuinely the right plaintext under there, not just opaque bytes.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_sealed_leaf_really_contains_the_preimage"`
- **`test_ward_sealed_part_is_bound_to_its_path`** — A leaf cannot be served for another entry's path.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_sealed_part_is_bound_to_its_path"`
- **`test_ward_delete_returns_a_leaf_with_both_parts_empty`** — A full delete, not a tombstone: the host removes the record entirely.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_returns_a_leaf_with_both_parts_empty"`
- **`test_ward_add_then_delete_from_genesis_is_the_empty_tree`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_add_then_delete_from_genesis_is_the_empty_tree"`
- **`test_ward_add_then_delete_restores_the_root_exactly`** — History independence: the tree depends on what it holds, not on what it once held.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_add_then_delete_restores_the_root_exactly"`
- **`test_ward_an_entry_added_first_and_deleted_last_leaves_no_trace`** — The same root as a tree the entry was NEVER added to, whatever came in between.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_an_entry_added_first_and_deleted_last_leaves_no_trace"`
- **`test_ward_pointer_is_a_sealed_leaf_naming_its_target`** — A pointer is an ordinary leaf at its own path whose content is entry_type "pointer" and whose value is the target's leaf_identity, in the same app_id.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pointer_is_a_sealed_leaf_naming_its_target"`
- **`test_ward_read_follows_a_pointer_one_hop`** — A read of the pointer pulls the pointer, then its target against the same root, and shows the target's value with what it points to.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_read_follows_a_pointer_one_hop"`
- **`test_ward_pointer_to_an_absent_target_reads_as_not_found`** — The target need not exist when the pointer is written; reading it is then a proven absence, not an error.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pointer_to_an_absent_target_reads_as_not_found"`
- **`test_ward_pointer_to_a_pointer_is_refused`** — Only one hop is followed: a chain fails the read rather than being walked.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pointer_to_a_pointer_is_refused"`
- **`test_ward_pointer_cannot_point_at_itself`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pointer_cannot_point_at_itself"`
- **`test_ward_overwriting_a_pointer_shows_what_it_pointed_to`** — A value written over a pointer names the replaced target, not raw identity bytes.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_overwriting_a_pointer_shows_what_it_pointed_to"`
- **`test_ward_rejects_a_tampered_leaf`** — A leaf the host edited is refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_tampered_leaf"`
- **`test_ward_rejects_a_leaf_served_from_another_path`** — The host answers a request for one entry with a different entry's real leaf.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_leaf_served_from_another_path"`
- **`test_ward_get_entry_pulls_and_shows`** — The device pulls the value from the host and renders it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_get_entry_pulls_and_shows"`
- **`test_ward_get_entry_without_the_wm_proves_against_the_stored_head_and_warns`** — No WM this session (a new session that never synced): the read is still PROVED, against the head this device last adopted, but its freshness is not -- so it says so.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_get_entry_without_the_wm_proves_against_the_stored_head_and_warns"`
- **`test_ward_get_entry_absent_is_distinct_from_empty`** — A missing entry (provider returns None) must not look like an entry whose value happens to be empty: the device says it was not found.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_get_entry_absent_is_distinct_from_empty"`
- **`test_ward_get_entry_empty_value_is_shown_as_an_entry`** — The converse of the above, end to end: a present-but-empty value IS an entry.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_get_entry_empty_value_is_shown_as_an_entry"`
- **`test_ward_get_entry_serves_the_right_one_of_several`** — The store holds several leaves under opaque keys and serves the one asked for.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_get_entry_serves_the_right_one_of_several"`
- **`test_ward_set_entry_add_shows_the_new_value`** — Writing a key the host does not hold is an ADD: nothing is being replaced, so the screen must not claim otherwise.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_set_entry_add_shows_the_new_value"`
- **`test_ward_set_entry_update_names_the_value_it_replaces`** — Writing a key the host already holds is an OVERWRITE.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_set_entry_update_names_the_value_it_replaces"`
- **`test_ward_set_entry_rejects_an_absent_value`** — An absent value is refused, rather than silently blanking the entry.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_set_entry_rejects_an_absent_value"`
- **`test_ward_delete_entry_names_the_value_being_removed`** — Confirming a deletion by key alone tells the user nothing about what they lose, so the device pulls the entry and puts its value on screen.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_entry_names_the_value_being_removed"`
- **`test_ward_delete_entry_is_idempotent_on_a_proved_absence`** — Deleting a path that already holds nothing succeeds, and changes nothing.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_entry_is_idempotent_on_a_proved_absence"`
- **`test_ward_delete_entry_retry_after_a_lost_response_succeeds`** — A lost response is now a no-op rather than a stuck state.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_entry_retry_after_a_lost_response_succeeds"`
- **`test_ward_delete_entry_still_refuses_an_unproved_absence`** — Idempotence rests on the proof, so an unwitnessed denial is still refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_entry_still_refuses_an_unproved_absence"`
- **`test_ward_apply_refuses_to_drop_a_no_change_result_on_a_live_entry`** — Host-side guard: "nothing changed" must not be applied over an entry that exists.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_apply_refuses_to_drop_a_no_change_result_on_a_live_entry"`
- **`test_ward_delete_entry_deletes_an_empty_valued_entry`** — An entry whose value is empty still exists, so deleting it must be allowed.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_entry_deletes_an_empty_valued_entry"`
- **`test_ward_rejects_an_incomplete_key`** — Every request validates (app_id, identifier) before deriving, pulling or showing.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_an_incomplete_key"`
- **`test_ward_rejects_a_rolled_back_leaf`** — The host serves an OLDER version of an entry it really did hold once.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_rolled_back_leaf"`
- **`test_ward_rejects_an_unproved_denial`** — The host hides an entry by claiming it holds none.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_an_unproved_denial"`
- **`test_ward_rejects_a_membership_answer_without_a_proof`** — A leaf offered with no proof at all is refused once a root is held.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejects_a_membership_answer_without_a_proof"`
- **`test_ward_accepts_a_proved_absence`** — The converse: a properly witnessed absence is accepted and shown as not found.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_accepts_a_proved_absence"`
- **`test_ward_verifies_a_present_entry_against_the_root`** — And a well-proved present entry still shows its value.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_verifies_a_present_entry_against_the_root"`
- **`test_ward_root_survives_a_new_session`** — A root written in one session is still there in the next.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_root_survives_a_new_session"`
- **`test_ward_is_isolated_per_hidden_wallet`** — Two hidden wallets share a device and share nothing else.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_is_isolated_per_hidden_wallet"`
- **`test_ward_adopts_an_attested_tree_it_never_built`** — The device adopts a tree built somewhere else, and then verifies against it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_adopts_an_attested_tree_it_never_built"`
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
- **`test_ward_reconcile_refuses_a_lower_counter_outside_recovery`** — A DEMOTION NEEDS THE USER, and the round is where that consent is recorded.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_reconcile_refuses_a_lower_counter_outside_recovery"`
- **`test_ward_a_write_authorises_its_advance_to_the_wm`** — CONNECT-MODE WRITES CARRY `wm_sig`, which is what lets a WM refuse an unauthorised advance.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_write_authorises_its_advance_to_the_wm"`
- **`test_ward_the_wm_refuses_an_unauthorised_advance`** — The other half of the same property, asserted where it bites: at the WM.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_the_wm_refuses_an_unauthorised_advance"`
- **`test_ward_refuses_a_different_state_at_the_same_counter`** — One counter names one state.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_different_state_at_the_same_counter"`
- **`test_ward_reconcile_needs_an_attestation_first`** — A root on its own adopts nothing -- otherwise the host could simply announce one.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_reconcile_needs_an_attestation_first"`
- **`test_ward_an_attestation_cannot_be_adopted_twice`** — The round closes on adoption, so a replayed reconcile has nothing to act on.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_an_attestation_cannot_be_adopted_twice"`
- **`test_ward_a_write_does_not_move_the_head_until_confirmed`** — THE invariant of commit-on-WM-confirmation, asserted directly.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_write_does_not_move_the_head_until_confirmed"`
- **`test_ward_a_published_write_syncs_cleanly`** — Publish what the write produced and the next sync is a no-op, not a conflict.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_published_write_syncs_cleanly"`
- **`test_ward_an_unpublished_write_simply_does_not_happen`** — A write the host never publishes leaves no trace, instead of wedging the wallet.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_an_unpublished_write_simply_does_not_happen"`
- **`test_ward_catches_up_across_transitions_it_never_saw`** — The device adopts a head two steps ahead, by verifying each step.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catches_up_across_transitions_it_never_saw"`
- **`test_ward_catch_up_without_the_wm_reads_the_newer_head_with_the_warning`** — No WM: a cached attestation and the chain move the session's reads forward, and the screen says the value does not reflect anything since the WM's timestamp for that head.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_without_the_wm_reads_the_newer_head_with_the_warning"`
- **`test_ward_catch_up_refuses_a_head_the_wm_never_attested`** — A LOST RACE, or a head built from authorisations that were never published: every link is genuine, but no WM signature names the head, so the device does not read from it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_a_head_the_wm_never_attested"`
- **`test_ward_catch_up_refuses_an_attestation_older_than_the_stored_head`** — THE TIMESTAMP FLOOR: every head on a branch a revert removed was attested before that revert, so an attestation older than the stored head's is refused before any link is asked.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_an_attestation_older_than_the_stored_head"`
- **`test_ward_catch_up_persists_nothing`** — The next session reads the STORED head again: a proof against the caught-up tree fails.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_persists_nothing"`
- **`test_ward_catch_up_persists_when_the_user_allows_it`** — THE USER'S SETTING: the cached-attested head becomes the STORED head, so a later session reads from it too -- still under the dated warning, since no WM attested it live.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_persists_when_the_user_allows_it"`
- **`test_ward_catch_up_stops_persisting_once_the_user_withdraws`** — Withdrawing needs no screen, and the next catch-up is for its session only again.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_stops_persisting_once_the_user_withdraws"`
- **`test_ward_persisting_still_refuses_an_attestation_older_than_the_stored_head`** — The setting changes what is KEPT, not what is accepted: the timestamp floor still holds.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_persisting_still_refuses_an_attestation_older_than_the_stored_head"`
- **`test_ward_without_a_wm_catches_up_and_writes_on_its_own_chain`** — THE MVP LOOP (MVP build): catch up to genesis, write, store the write, catch up to it. Every head is moved by the chain alone and persisted, the write is signed for the HOST (TAG_STEP) so it can refuse one this wallet did not make, and a read is proved but never current.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_without_a_wm_catches_up_and_writes_on_its_own_chain"`
- **`test_ward_without_a_wm_refuses_the_wm_routes_and_the_setting`** — MVP build: `WardSync` and `WardSetPersistWithoutWm` are refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_without_a_wm_refuses_the_wm_routes_and_the_setting"`
- **`test_ward_without_a_wm_still_refuses_an_older_head_or_a_foreign_chain`** — MVP build: the chain is the only authority here, so its two checks matter more, not less.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_without_a_wm_still_refuses_an_older_head_or_a_foreign_chain"`
- **`test_ward_catch_up_refuses_a_head_older_than_the_stored_one`** — Serving a device an older head without the WM is detected before any link is asked.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_a_head_older_than_the_stored_one"`
- **`test_ward_without_the_wm_a_read_from_an_older_tree_is_refused`** — The other way to serve an older root: answer a read with a proof from an earlier tree.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_without_the_wm_a_read_from_an_older_tree_is_refused"`
- **`test_ward_catch_up_refuses_a_chain_that_does_not_reach_the_stored_head`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_refuses_a_chain_that_does_not_reach_the_stored_head"`
- **`test_ward_catch_up_is_refused_with_an_attested_head`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catch_up_is_refused_with_an_attested_head"`
- **`test_ward_catches_up_further_than_one_ack_can_carry`** — THE REASON THE WALK IS A PULL, and the case the old forward push could not express.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catches_up_further_than_one_ack_can_carry"`
- **`test_ward_catches_up_across_a_revert_to_a_state_below_its_own_head`** — The walk crosses a DEMOTION, and the state it restores is one from below this device.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catches_up_across_a_revert_to_a_state_below_its_own_head"`
- **`test_ward_verify_chain_brings_a_fresh_session_online`** — Adopting through the chain latches the session online, exactly as reconcile does.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_verify_chain_brings_a_fresh_session_online"`
- **`test_ward_refuses_a_chain_with_a_gap`** — A jump longer than any batch may carry is refused, however authentic the link.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_chain_with_a_gap"`
- **`test_ward_refuses_a_chain_that_does_not_start_at_its_own_head`** — The baseline is the device's own head, never one the host names.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_chain_that_does_not_start_at_its_own_head"`
- **`test_ward_refuses_an_unauthorised_link`** — Without K_auth a link cannot be minted, so the host cannot invent a step.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_an_unauthorised_link"`
- **`test_ward_refuses_a_chain_that_ends_somewhere_else`** — Descent is not currency.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_chain_that_ends_somewhere_else"`
- **`test_ward_a_write_emits_its_own_authorisation`** — Each write hands back the link that authorises it, and the host records it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_write_emits_its_own_authorisation"`
- **`test_ward_a_device_on_a_lost_branch_cannot_catch_up`** — The gap WardRejoin exists for: the walk reaches this device's counter at another root.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_device_on_a_lost_branch_cannot_catch_up"`
- **`test_ward_rejoin_adopts_the_wm_head_after_the_wm_lost_a_branch`** — Both branches proved, the loss shown, the WM's head adopted -- and verified against.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_adopts_the_wm_head_after_the_wm_lost_a_branch"`
- **`test_ward_rejoin_declined_leaves_the_device_where_it_was`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_declined_leaves_the_device_where_it_was"`
- **`test_ward_rejoin_needs_the_devices_own_branch`** — No proof of this device's branch, no rejoin: that proof is what makes the fork genuine.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_needs_the_devices_own_branch"`
- **`test_ward_rejoin_refuses_a_fork_point_that_is_not_the_latest`** — Naming a LOWER counter would inflate the count on screen; the branches must part above it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_refuses_a_fork_point_that_is_not_the_latest"`
- **`test_ward_rejoin_refuses_a_fork_point_at_or_above_a_head`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_refuses_a_fork_point_at_or_above_a_head"`
- **`test_ward_rejoin_refuses_a_device_that_is_not_on_a_fork`** — A device on the WM's own branch catches up with verify_chain; the branches never part.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_refuses_a_device_that_is_not_on_a_fork"`
- **`test_ward_rejoin_needs_an_attested_round`** — The WM's head comes from this round's attestation, never from the host.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_needs_an_attested_round"`
- **`test_ward_rejoin_refuses_a_forged_link`** — Neither branch can be invented: every link needs K_auth, which the host does not hold.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_refuses_a_forged_link"`
- **`test_ward_scenario_fast_forward_one_step_needs_no_confirmation`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_scenario_fast_forward_one_step_needs_no_confirmation"`
- **`test_ward_scenario_fast_forward_across_a_gap`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_scenario_fast_forward_across_a_gap"`
- **`test_ward_scenario_wm_behind_refuses_ingest_and_recovers_by_rollback`** — DR restore on the WM.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_scenario_wm_behind_refuses_ingest_and_recovers_by_rollback"`
- **`test_ward_scenario_wm_behind_to_an_older_tree_discards_its_entries`** — The same recovery onto an OLDER tree: the entries it lacks are gone, as the screen warned.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_scenario_wm_behind_to_an_older_tree_discards_its_entries"`
- **`test_ward_a_batch_link_cannot_jump_over_the_devices_head`** — SKIP-OVER SPLICING, the attack a variable-length step makes possible, refused.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_batch_link_cannot_jump_over_the_devices_head"`
- **`test_ward_catches_up_across_another_devices_batch`** — A batch of n changes is ONE authorised transition: one link, the counter moved by n.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_catches_up_across_another_devices_batch"`
- **`test_ward_rejoin_across_a_batch_counts_changes_and_refuses_a_point_inside_it`** — The WM's branch is one batch link 2 -> 5; this device's branch is 2 -> 3 -> 4.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rejoin_across_a_batch_counts_changes_and_refuses_a_point_inside_it"`
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
- **`test_ward_a_write_is_bound_to_the_latest_sync`** — The device binds to the nonce of the LATEST attestation it verified, not an earlier one: after two syncs, the write's `wm_sig` verifies under the second nonce only.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_write_is_bound_to_the_latest_sync"`
- **`test_ward_attack_a_revert_from_an_ended_session_is_refused`** — A DEMOTION THE USER APPROVED, HELD BACK PAST A NEW SYNC: refused like any other write.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_a_revert_from_an_ended_session_is_refused"`
- **`test_ward_roll_forward_brings_a_restored_wm_back`** — The device signs each accepted step again for the current session; submitted as ordinary advances they return the WM to the head the device holds, and the next sync just reconciles.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_roll_forward_brings_a_restored_wm_back"`
- **`test_ward_roll_forward_runs_in_pages_with_one_approval`** — Pages of one round:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_roll_forward_runs_in_pages_with_one_approval"`
- **`test_ward_attack_roll_forward_needs_a_detected_restore`** — Not in a round whose attestation did not find the WM behind:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_needs_a_detected_restore"`
- **`test_ward_roll_forward_declined_signs_nothing`** — The user can decline:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_roll_forward_declined_signs_nothing"`
- **`test_ward_roll_forward_signatures_are_bound_to_the_round`** — The re-signed steps belong to the round they were minted in, like any other authorisation:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_roll_forward_signatures_are_bound_to_the_round"`
- **`test_ward_attack_roll_forward_needs_the_wms_record`** — A step the WM never recorded as accepted -- a lost race, a write held back -- is not signed again:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_needs_the_wms_record"`
- **`test_ward_attack_roll_forward_needs_the_devices_own_mac`** — The WM's record alone is not enough either:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_needs_the_devices_own_mac"`
- **`test_ward_attack_roll_forward_starts_at_the_attested_head`** — The first step must start at the head the WM attests in this round, and each next one where the previous ended:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_starts_at_the_attested_head"`
- **`test_ward_attack_roll_forward_refuses_a_branch_off_this_devices_history`** — Genuine steps on another branch -- made by this wallet and accepted by a WM -- that reach this device's counter with another root are not signed again:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_attack_roll_forward_refuses_a_branch_off_this_devices_history"`
- **`test_ward_batched_flush_publishes_one_transition_for_several_changes`** — Three queued changes, one flush: one link F -> F+3, one authorisation, three leaves.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_batched_flush_publishes_one_transition_for_several_changes"`
- **`test_ward_a_batch_that_loses_the_race_stays_queued_whole`** — All or nothing at the WM too: another device wins, the batch is refused as one, and every change in it is offered again -- rebuilt on the new head.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_batch_that_loses_the_race_stays_queued_whole"`
- **`test_ward_a_batch_is_capped_at_max_batch`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_batch_is_capped_at_max_batch"`
- **`test_ward_a_batch_with_one_bad_proof_files_nothing`** — The second change's proof is wrong: the whole batch aborts, and nothing is offered.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_batch_with_one_bad_proof_files_nothing"`
- **`test_ward_rollback_undoes_the_last_write`** — The wallet returns to the state before its most recent change.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rollback_undoes_the_last_write"`
- **`test_ward_rollback_requires_the_root_at_the_requested_counter`** — A historical root must match the counter being restored.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rollback_requires_the_root_at_the_requested_counter"`
- **`test_ward_rollback_needs_wm_acceptance_for_older_links`** — Historical links need WM receipts tied to their accepted occurrences.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rollback_needs_wm_acceptance_for_older_links"`
- **`test_ward_rollback_count_comes_from_the_attested_counter`** — The number on the screen is authenticated, which is what makes it worth showing.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rollback_count_comes_from_the_attested_counter"`
- **`test_ward_rollback_from_a_regressed_wm_is_the_same_operation`** — The WM's register is lost; the demotion extends the WM's head, not this device's.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rollback_from_a_regressed_wm_is_the_same_operation"`
- **`test_ward_rollback_still_requires_a_genuine_attestation`** — Consent does not replace verification.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rollback_still_requires_a_genuine_attestation"`
- **`test_ward_delete_keeps_the_root_canonical_when_a_branch_is_promoted`** — A branch sibling promotes unchanged, and the device stays on the CANONICAL root.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_keeps_the_root_canonical_when_a_branch_is_promoted"`
- **`test_ward_deleting_the_last_entry_keeps_verifying`** — Emptying the tree must not turn verification off.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_deleting_the_last_entry_keeps_verifying"`
- **`test_ward_an_emptied_tree_can_be_written_to_again`** — ...and the fix must not brick the wallet it protects.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_an_emptied_tree_can_be_written_to_again"`
- **`test_ward_sync_reports_the_device_counter`** — The round opener also answers "where are you".
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_sync_reports_the_device_counter"`
- **`test_ward_sync_counter_reports_the_confirmed_head`** — WardSyncAck.counter reports the confirmed head, which is now the only head there is.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_sync_counter_reports_the_confirmed_head"`
- **`test_ward_write_authorises_its_transition_over_mac_heads`** — Every write carries an authorisation over the transition it made.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_write_authorises_its_transition_over_mac_heads"`
- **`test_ward_offline_read_serves_the_pinned_value`** — The motivating case: a host that never syncs is still served.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_offline_read_serves_the_pinned_value"`
- **`test_ward_pinned_entry_survives_a_power_cycle`** — Flash, not the session cache.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pinned_entry_survives_a_power_cycle"`
- **`test_ward_offline_read_of_an_unpinned_entry_says_so`** — A miss is reported as a miss -- never as an empty value, and never by pulling.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_offline_read_of_an_unpinned_entry_says_so"`
- **`test_ward_pin_needs_a_synced_session`** — An unsynced device keeps NOTHING, even a leaf it could authenticate.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pin_needs_a_synced_session"`
- **`test_ward_pin_rejects_a_forged_leaf`** — A leaf the wallet never sealed fails its tag, and NOTHING is stored.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pin_rejects_a_forged_leaf"`
- **`test_ward_pin_rejects_a_leaf_that_is_not_in_the_trusted_root`** — Once the device holds a root, membership is required -- authenticity is not enough.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_pin_rejects_a_leaf_that_is_not_in_the_trusted_root"`
- **`test_ward_a_pinned_entry_survives_the_head_moving`** — Advancing the head leaves a record alone -- it is not rewritten and not removed.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_pinned_entry_survives_the_head_moving"`
- **`test_ward_repinning_an_identical_value_neither_asks_nor_writes`** — Nothing was replaced, so there is nothing to authorise.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_repinning_an_identical_value_neither_asks_nor_writes"`
- **`test_ward_replacing_a_pinned_value_needs_its_own_confirmation`** — Replacement destroys the previous copy, so it is confirmed like a deletion.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_replacing_a_pinned_value_needs_its_own_confirmation"`
- **`test_ward_cancelling_a_replacement_leaves_the_old_copy`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_cancelling_a_replacement_leaves_the_old_copy"`
- **`test_ward_erase_removes_the_copy_only_after_confirmation`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_erase_removes_the_copy_only_after_confirmation"`
- **`test_ward_erasing_something_not_kept_is_a_silent_no_op`** — No screen, because a hold that always means "nothing happened" trains the user to approve without reading -- the same reasoning as the idempotent delete.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_erasing_something_not_kept_is_a_silent_no_op"`
- **`test_ward_deleting_an_entry_leaves_the_offline_copy`** — Two different questions, and one confirmation cannot stand for both.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_deleting_an_entry_leaves_the_offline_copy"`
- **`test_ward_offline_write_is_queued_not_applied`** — With no host to pull from there is no current state, so no root and no counter can be derived.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_offline_write_is_queued_not_applied"`
- **`test_ward_a_queued_write_outlives_the_session_that_made_it`** — Flash, not the session cache -- and the session is the thing that would lose it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_queued_write_outlives_the_session_that_made_it"`
- **`test_ward_flush_publishes_the_queued_change_sealed`** — Sealing happens on the way OUT, which is the whole reason records sit in flash in the clear: `storage.c` covers them until they leave the device, and not after.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_flush_publishes_the_queued_change_sealed"`
- **`test_ward_conflict_keep_original_discards_the_queued_change`** — Queued offline at #0; another device publishes the same entry at #1.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_conflict_keep_original_discards_the_queued_change"`
- **`test_ward_conflict_keep_new_publishes_over_the_other_device`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_conflict_keep_new_publishes_over_the_other_device"`
- **`test_ward_conflict_declined_twice_stays_pending`** — Neither answer: the flush stops and the change is still queued, unresolved.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_conflict_declined_twice_stays_pending"`
- **`test_ward_conflict_with_the_same_value_settles_without_a_screen`**
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_conflict_with_the_same_value_settles_without_a_screen"`
- **`test_ward_no_conflict_when_the_entry_was_published_before_queueing`** — Queued at #1 over a value published at #1: formed in view of it, so no question.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_no_conflict_when_the_entry_was_published_before_queueing"`
- **`test_ward_flush_needs_a_synced_session`** — With no trusted root there is nothing to derive against and nothing to prove the pulled leaf with.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_flush_needs_a_synced_session"`
- **`test_ward_a_change_stays_queued_until_the_wm_confirms_it`** — Handing the leaf to the host is not the change taking effect.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_change_stays_queued_until_the_wm_confirms_it"`
- **`test_ward_an_offered_change_settles_in_a_later_session`** — The claim that settles a flush outlives the session that filed it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_an_offered_change_settles_in_a_later_session"`
- **`test_ward_one_wallet_does_not_settle_anothers_queued_change`** — Reconciling one hidden wallet must not touch another wallet's queued records.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_one_wallet_does_not_settle_anothers_queued_change"`
- **`test_ward_a_confirmed_change_becomes_an_offline_copy`** — Clearing the pending flag is a REWRITE, never a delete: the record stays on as the cached copy of the value that was just published.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_confirmed_change_becomes_an_offline_copy"`
- **`test_ward_discarding_a_queued_change_is_confirmed_and_says_what_it_is`** — Erasing a pending record DISCARDS a change that was never published -- calling that a deletion would suggest WARD ever had it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_discarding_a_queued_change_is_confirmed_and_says_what_it_is"`
- **`test_ward_delete_requires_a_connection`** — A queued delete cannot be made safe yet: `EMPTY_PART` is plaintext, so any host can construct a delete leaf for any entry_key, and uploading queued deletes would hand a host the power to delete anything.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_delete_requires_a_connection"`
- **`test_ward_set_entry_refuses_offline_and_names_the_queue_request`** — The online write no longer falls back to queueing, and the refusal says what to use.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_set_entry_refuses_offline_and_names_the_queue_request"`
- **`test_ward_get_entry_refuses_offline_and_names_the_queue_request`** — Same for a read with NO stored head: nothing to prove against, so it refuses.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_get_entry_refuses_offline_and_names_the_queue_request"`
- **`test_ward_queue_delete_discards_a_queued_change`** — The queue delete removes a change that was never published -- and nothing else.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_queue_delete_discards_a_queued_change"`
- **`test_ward_queue_delete_of_nothing_is_reported_not_raised`** — "Nothing was queued" is an ANSWER.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_queue_delete_of_nothing_is_reported_not_raised"`
- **`test_ward_queue_delete_will_not_touch_a_pinned_copy`** — A pinned read and a queued write live in the same store and are NOT the same question.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_queue_delete_will_not_touch_a_pinned_copy"`
- **`test_ward_a_queued_change_round_trips_through_a_backup`** — Export a queued change, lose it, put it back -- and the device can tell it is its own.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_queued_change_round_trips_through_a_backup"`
- **`test_ward_a_restored_change_still_publishes`** — The restore has to produce a record `flush_queue` can actually derive from, not just one that reads back.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_restored_change_still_publishes"`
- **`test_ward_a_tampered_backup_is_refused_before_any_screen`** — EVERY field the device would write back is inside the MAC.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_tampered_backup_is_refused_before_any_screen"`
- **`test_ward_a_pinned_copy_exports_no_intent_mac`** — A pinned read is not an intent: WARD already holds that value and there is nothing to re-queue.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_pinned_copy_exports_no_intent_mac"`
- **`test_ward_restoring_over_a_pending_change_names_both`** — A restore lands on a path that may already hold a later change, and the screen has to say so.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_restoring_over_a_pending_change_names_both"`
- **`test_ward_restoring_over_a_pinned_copy_says_which_it_is`** — A pinned copy is not a pending change, and the screen must not call it one.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_restoring_over_a_pinned_copy_says_which_it_is"`
- **`test_ward_queueing_a_longer_value_over_a_shorter_one`** — The same (app_id, identifier) again, with a value that no longer fits where the old one did.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_queueing_a_longer_value_over_a_shorter_one"`
- **`test_ward_a_value_past_the_cap_is_refused_and_the_old_one_survives`** — The other end of the same path: a value too long to store at all.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_value_past_the_cap_is_refused_and_the_old_one_survives"`
- **`test_ward_replacing_an_entry_keeps_its_place_in_the_queue`** — add(1), add(2a), add(3), get(2a), add(2b) with 2b LONGER, set(2a) from the backup.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_replacing_an_entry_keeps_its_place_in_the_queue"`
- **`test_ward_a_compact_record_reads_and_backs_up_like_any_other`** — `compact` keeps a HASH of the identity instead of the identity, and nothing above notices.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_compact_record_reads_and_backs_up_like_any_other"`
- **`test_ward_a_compact_record_is_published_when_it_is_named`** — A compact record cannot be published by "take the next one" -- and it says so.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_compact_record_is_published_when_it_is_named"`
- **`test_ward_naming_an_entry_publishes_that_one_not_the_first`** — The named flush is not only for compact records: it picks the entry, whatever form it is in.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_naming_an_entry_publishes_that_one_not_the_first"`
- **`test_ward_both_record_forms_share_one_store`** — A full and a compact record of different entries, side by side.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_both_record_forms_share_one_store"`
- **`test_ward_rewriting_an_entry_compactly_replaces_it`** — Changing form must take over the slot, not leave the old form behind.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_rewriting_an_entry_compactly_replaces_it"`
- **`test_ward_a_named_flush_may_hand_over_the_same_change_twice`** — The offered flag stops the UNNAMED loop repeating itself; a caller naming an entry overrides it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_named_flush_may_hand_over_the_same_change_twice"`
- **`test_ward_takes_an_unmoved_head`** — Re-confirming the same head is an ordinary, frequent thing: a host that syncs twice without writing gets the same attestation content back.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_takes_an_unmoved_head"`
- **`test_ward_takes_a_wm_restored_onto_its_own_head`** — A WM restored onto the device's own head attests it like any other head, and the device takes it.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_takes_a_wm_restored_onto_its_own_head"`
- **`test_ward_refuses_a_wm_restored_below_its_head`** — A WM restored below the device's head is refused by the counter floor.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_refuses_a_wm_restored_below_its_head"`
- **`test_ward_enrolment_then_a_write`** — The connect-mode enrolment flow end to end, on a WM that has never seen this wallet.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_enrolment_then_a_write"`
- **`test_ward_demotion_consent_does_not_survive_an_unrelated_adoption`** — CONSENT IS FOR A DESCENT FROM A PARTICULAR HEAD, not for a destination in the abstract.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_demotion_consent_does_not_survive_an_unrelated_adoption"`
- **`test_ward_a_demotion_from_a_regressed_wm_records_the_wm_predecessor`** — The recorded link must name the head the REVERT was minted over, not the store's.
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_demotion_from_a_regressed_wm_records_the_wm_predecessor"`
- **`test_ward_a_change_queued_over_its_own_unconfirmed_change_is_no_conflict`** — Queued over this device's OWN change while that one was still unconfirmed:
  `ward_device_test "tests/device_tests/misc/test_ward.py::test_ward_a_change_queued_over_its_own_unconfirmed_change_is_no_conflict"`

#### `tests/device_tests/misc/test_display_address.py` (7) — connect build (T3T1)

Run the file: `ward_device_test tests/device_tests/misc/test_display_address.py`

- **`test_display_address_shows_the_label_wards_holds`** — The motivating case: an address the wallet has a name for is shown by that name.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_shows_the_label_wards_holds"`
- **`test_display_address_says_so_when_there_is_no_label`** — An address with no entry is the ordinary case, and it is STATED.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_says_so_when_there_is_no_label"`
- **`test_display_address_label_is_domain_separated`** — A label written by one app does not surface under another's domain.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_label_is_domain_separated"`
- **`test_display_address_offline_serves_the_kept_label`** — A host that never syncs is still served -- from the device's own store, and said so.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_offline_serves_the_kept_label"`
- **`test_display_address_offline_without_a_kept_label_still_shows_the_address`** — The failure that must not become an address failure.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_offline_without_a_kept_label_still_shows_the_address"`
- **`test_display_address_rejects_an_empty_address`** — The one refusal.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_rejects_an_empty_address"`
- **`test_display_address_has_no_field_for_a_label`** — The host cannot name the recipient on the screen the recipient is checked against.
  `ward_device_test "tests/device_tests/misc/test_display_address.py::test_display_address_has_no_field_for_a_label"`

#### `tests/device_tests/ward/test_ward_app_role_v1.py` (4) — connect build (T3T1, protocol v1)

Run the file: `ward_device_test tests/device_tests/ward/test_ward_app_role_v1.py`

- **`test_a_read_asks_before_it_reveals`** — The reveal screen comes FIRST, and the operation's own screen follows it.
  `ward_device_test "tests/device_tests/ward/test_ward_app_role_v1.py::test_a_read_asks_before_it_reveals"`
- **`test_it_asks_every_time`** — UNLIKE THE THP ROLE SCREEN, which is asked once and then never again.
  `ward_device_test "tests/device_tests/ward/test_ward_app_role_v1.py::test_it_asks_every_time"`
- **`test_refusing_it_stops_the_operation`** — A refusal has to fail the request, not fall through to the operation's own screen.
  `ward_device_test "tests/device_tests/ward/test_ward_app_role_v1.py::test_refusing_it_stops_the_operation"`
- **`test_a_second_connection_is_not_refused`** — No pin means no lock-out, which is a consequence to state rather than a feature to claim.
  `ward_device_test "tests/device_tests/ward/test_ward_app_role_v1.py::test_a_second_connection_is_not_refused"`

#### `tests/device_tests/ward/test_ward_service_bind.py` (7) — service build

Run the file: `ward_device_test tests/device_tests/ward/test_ward_service_bind.py`

- **`test_a_daemon_binds_itself_as_the_service`** — WardServiceOpen with no ThpCreateNewSession before it, and no pre-existing service slot.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_a_daemon_binds_itself_as_the_service"`
- **`test_it_is_refused_on_the_wire_interface`** — The interface IS the authorisation boundary.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_it_is_refused_on_the_wire_interface"`
- **`test_an_unsupported_protocol_version_is_refused_by_name`** — Refused rather than negotiated down.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_an_unsupported_protocol_version_is_refused_by_name"`
- **`test_the_pinned_daemon_rebinds_after_a_restart`** — The case that actually happens: wardd restarts and comes back on a new channel.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_the_pinned_daemon_rebinds_after_a_restart"`
- **`test_a_different_daemon_is_refused_once_pinned`** — Pairing is not enough.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_a_different_daemon_is_refused_once_pinned"`
- **`test_a_bound_channel_is_not_listening`** — Not "refused" -- NOT EVEN ACKNOWLEDGED.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_a_bound_channel_is_not_listening"`
- **`test_an_unbound_channel_accepts_nothing_else_either`** — The interface serves ONE message before binding, not a general THP surface.
  `ward_device_test "tests/device_tests/ward/test_ward_service_bind.py::test_an_unbound_channel_accepts_nothing_else_either"`

#### `tests/device_tests/ward/test_ward_service_codec.py` (7) — service build, codec service channel

Run the file: `ward_device_test tests/device_tests/ward/test_ward_service_codec.py`

- **`test_a_daemon_that_restarts_while_idle_simply_rebinds`** — No lock-out is possible here, and that is structural rather than fixed.
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_a_daemon_that_restarts_while_idle_simply_rebinds"`
- **`test_rebinding_the_same_daemon_is_idempotent`** — Repeated announcements are answered, not refused.
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_rebinding_the_same_daemon_is_idempotent"`
- **`test_an_unbound_endpoint_refuses_everything_but_the_bootstrap`** — The receive boundary, and where it is enforced.
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_an_unbound_endpoint_refuses_everything_but_the_bootstrap"`
- **`test_a_refusal_does_not_stop_the_endpoint_serving`** — The reader must survive what it refuses.
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_a_refusal_does_not_stop_the_endpoint_serving"`
- **`test_a_half_sent_message_does_not_take_the_endpoint_with_it`** — A header is a promise of more, and a peer that breaks it must not cost the interface.
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_a_half_sent_message_does_not_take_the_endpoint_with_it"`
- **`test_the_existing_interfaces_keep_their_ports`** — Wire and debuglink must be where every existing host already expects them.
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_the_existing_interfaces_keep_their_ports"`
- **`test_service_catches_up_across_multiple_chain_pages`**
  `ward_device_test "tests/device_tests/ward/test_ward_service_codec.py::test_service_catches_up_across_multiple_chain_pages"`

#### `tests/device_tests/ward/test_ward_service_publish.py` (6) — service build

Run the file: `ward_device_test tests/device_tests/ward/test_ward_service_publish.py`

- **`test_a_write_is_published_and_adopted`** — The whole point, in one exchange: the device writes, the daemon's replica advances, the WM attests the head the device computed, and the device adopts it before answering the host.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_a_write_is_published_and_adopted"`
- **`test_an_attestation_for_another_head_is_refused`** — The check that makes this route stronger than reconcile.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_an_attestation_for_another_head_is_refused"`
- **`test_a_conflict_is_definitive_and_keeps_the_channel`** — Somebody else wrote first: known not to have landed, so the channel stays up.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_a_conflict_is_definitive_and_keeps_the_channel"`
- **`test_a_dropped_publish_ack_is_settled_by_the_next_sync`** — The ambiguous failure, end to end -- and the one where reporting the ack would lie.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_a_dropped_publish_ack_is_settled_by_the_next_sync"`
- **`test_a_flush_drains_and_settles_each_change`** — `remaining` is the host's loop condition, so it has to survive the split.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_a_flush_drains_and_settles_each_change"`
- **`test_an_idempotent_delete_publishes_nothing`** — No transition, so nothing to publish and nothing to put at risk.
  `ward_device_test "tests/device_tests/ward/test_ward_service_publish.py::test_an_idempotent_delete_publishes_nothing"`

#### `tests/device_tests/ward/test_ward_service_sync.py` (9) — service build

Run the file: `ward_device_test tests/device_tests/ward/test_ward_service_sync.py`

- **`test_a_genesis_read_syncs_itself`** — An empty tree, a WM that has never seen this wallet, and a read that still works.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_a_genesis_read_syncs_itself"`
- **`test_the_read_is_served_by_the_daemon`** — A leaf the wallet channel never sees.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_the_read_is_served_by_the_daemon"`
- **`test_without_a_daemon_a_read_fails_closed`** — No binding, so no sync, so no read.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_without_a_daemon_a_read_fails_closed"`
- **`test_a_genesis_write_syncs_itself_too`** — The other kind of first operation.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_a_genesis_write_syncs_itself_too"`
- **`test_a_second_session_syncs_again`** — Readiness is per session, and has to be: a session begins knowing nothing current.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_a_second_session_syncs_again"`
- **`test_another_wallet_is_not_served_from_this_replica`** — A hidden wallet against a daemon that holds a different wallet's replica: refused.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_another_wallet_is_not_served_from_this_replica"`
- **`test_a_sync_requirement_buys_exactly_one_retry`** — One sync, one retry, then an error -- counted, not timed.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_a_sync_requirement_buys_exactly_one_retry"`
- **`test_a_silent_daemon_fails_closed`** — Bound, but not answering.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_a_silent_daemon_fails_closed"`
- **`test_a_torn_down_service_can_come_back`** — What the timeout leaves behind, checked from the far side.
  `ward_device_test "tests/device_tests/ward/test_ward_service_sync.py::test_a_torn_down_service_can_come_back"`

#### `tests/device_tests/thp/test_ward_app_role.py` (6) — THP wallet protocol (T3W1)

Run the file: `ward_device_test tests/device_tests/thp/test_ward_app_role.py`

- **`test_the_first_app_to_ask_is_pinned_after_a_held_confirmation`** — One screen, then silence.
  `ward_device_test "tests/device_tests/thp/test_ward_app_role.py::test_the_first_app_to_ask_is_pinned_after_a_held_confirmation"`
- **`test_another_app_is_refused`** — A second host, with a key of its own, gets a failure rather than a screen.
  `ward_device_test "tests/device_tests/thp/test_ward_app_role.py::test_another_app_is_refused"`
- **`test_every_host_facing_ward_message_is_covered`** — The check is installed once, for a LIST of messages, and this is that list's test.
  `ward_device_test "tests/device_tests/thp/test_ward_app_role.py::test_every_host_facing_ward_message_is_covered"`
- **`test_reset_hands_the_role_to_whoever_asks_next`** — The way back, and it is available to a host that holds nothing.
  `ward_device_test "tests/device_tests/thp/test_ward_app_role.py::test_reset_hands_the_role_to_whoever_asks_next"`
- **`test_resetting_an_unclaimed_device_says_so`** — It succeeds and reports `was_bound=False` rather than failing.
  `ward_device_test "tests/device_tests/thp/test_ward_app_role.py::test_resetting_an_unclaimed_device_says_so"`
- **`test_a_refused_confirmation_grants_nothing`** — Declining the screen must leave the role unclaimed, not pin the asker anyway.
  `ward_device_test "tests/device_tests/thp/test_ward_app_role.py::test_a_refused_confirmation_grants_nothing"`

#### `tests/device_tests/thp/test_ward_channel_switching.py` (10) — THP wallet protocol (T3W1), service build

Run the file: `ward_device_test tests/device_tests/thp/test_ward_channel_switching.py`

- **`test_repeated_wallet_ward_wallet_switching`** — Wallet, WARD, wallet, WARD -- a dozen times over, alternating reads and writes.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_repeated_wallet_ward_wallet_switching"`
- **`test_wallet_session_restart_reattaches_service_channel`** — The daemon binds ONCE and stays bound across every session restart the wallet causes.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_wallet_session_restart_reattaches_service_channel"`
- **`test_wallet_preemption_does_not_kill_ward_service`** — A second wallet host preempts the first.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_wallet_preemption_does_not_kill_ward_service"`
- **`test_service_reconnect_does_not_kill_wallet_channel`** — A daemon goes away and comes back.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_service_reconnect_does_not_kill_wallet_channel"`
- **`test_service_timeout_does_not_damage_wallet_channel`** — A silent daemon costs the WARD operation and nothing else.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_service_timeout_does_not_damage_wallet_channel"`
- **`test_malformed_service_reply_does_not_damage_wallet_channel`** — A daemon that answers something else entirely.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_malformed_service_reply_does_not_damage_wallet_channel"`
- **`test_unsolicited_service_message_cannot_enter_wallet_dispatch`** — A bound daemon speaks out of turn.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_unsolicited_service_message_cannot_enter_wallet_dispatch"`
- **`test_service_reset_does_not_restart_or_break_wallet`** — Retiring the binding is a WARD operation, not a device event.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_service_reset_does_not_restart_or_break_wallet"`
- **`test_large_messages_cross_the_seam_in_both_directions`** — A value too big for a channel's own buffer, written and read back, repeatedly.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_large_messages_cross_the_seam_in_both_directions"`
- **`test_the_interfaces_never_borrow_each_others_buffers`** — Daemons come and go; both interfaces can still allocate a channel afterwards.
  `ward_device_test "tests/device_tests/thp/test_ward_channel_switching.py::test_the_interfaces_never_borrow_each_others_buffers"`

#### `tests/device_tests/thp/test_ward_interface.py` (4) — THP (T3W1); service-thp build for most

Run the file: `ward_device_test tests/device_tests/thp/test_ward_interface.py`

- **`test_the_ward_interface_carries_its_own_channel`** — A channel on the WARD interface, allocated while the wire interface holds one of its own.
  `ward_device_test "tests/device_tests/thp/test_ward_interface.py::test_the_ward_interface_carries_its_own_channel"`
- **`test_the_ward_interface_completes_a_handshake`** — It is a full THP interface, not merely a socket that answers.
  `ward_device_test "tests/device_tests/thp/test_ward_interface.py::test_the_ward_interface_completes_a_handshake"`
- **`test_it_answers_while_the_wire_interface_holds_a_channel`** — A message arriving here is HANDLED, not merely reassembled.
  `ward_device_test "tests/device_tests/thp/test_ward_interface.py::test_it_answers_while_the_wire_interface_holds_a_channel"`
- **`test_the_existing_interfaces_keep_their_ports`** — Wire and debuglink must be where every existing host already expects them.
  `ward_device_test "tests/device_tests/thp/test_ward_interface.py::test_the_existing_interfaces_keep_their_ports"`

#### `tests/device_tests/thp/test_ward_service_reset.py` (6) — THP (T3W1), service-thp build

Run the file: `ward_device_test tests/device_tests/thp/test_ward_service_reset.py`

- **`test_a_reset_hands_the_role_to_the_next_daemon`** — The whole point: after a reset, a daemon with a DIFFERENT key binds and serves.
  `ward_device_test "tests/device_tests/thp/test_ward_service_reset.py::test_a_reset_hands_the_role_to_the_next_daemon"`
- **`test_a_reset_with_no_binding_is_refused`** — Reported rather than treated as success.
  `ward_device_test "tests/device_tests/thp/test_ward_service_reset.py::test_a_reset_with_no_binding_is_refused"`
- **`test_an_unresolved_claim_refuses_the_reset`** — Refused, and the refusal is ACTIONABLE: it names how many, so the host knows the fix is to reconnect the current service and drain them rather than to retry.
  `ward_device_test "tests/device_tests/thp/test_ward_service_reset.py::test_an_unresolved_claim_refuses_the_reset"`
- **`test_force_resets_and_reports_what_it_abandoned`** — `force` is for the case the refusal cannot help with: the daemon is gone for good.
  `ward_device_test "tests/device_tests/thp/test_ward_service_reset.py::test_force_resets_and_reports_what_it_abandoned"`
- **`test_a_reset_is_refused_on_the_service_interface`** — The receive boundary, checked from the far side.
  `ward_device_test "tests/device_tests/thp/test_ward_service_reset.py::test_a_reset_is_refused_on_the_service_interface"`
- **`test_a_live_service_is_displaced_by_the_reset`** — Resetting while the bound daemon is STILL THERE -- the branch the other tests never reach.
  `ward_device_test "tests/device_tests/thp/test_ward_service_reset.py::test_a_live_service_is_displaced_by_the_reset"`

### trezorlib and launcher tests

Plain pytest, no emulator.


#### `python/tests/test_ward_trie.py` (19)

Run the file: `pytest python/tests/test_ward_trie.py`

- **`test_empty_root_is_sha256_of_0x02`**
  `pytest "python/tests/test_ward_trie.py::test_empty_root_is_sha256_of_0x02"`
- **`test_the_shared_vectors_rebuild_byte_for_byte`**
  `pytest "python/tests/test_ward_trie.py::test_the_shared_vectors_rebuild_byte_for_byte"`
- **`test_frozen_membership_and_absence`**
  `pytest "python/tests/test_ward_trie.py::test_frozen_membership_and_absence"`
- **`test_bit_order_is_msb_first`**
  `pytest "python/tests/test_ward_trie.py::test_bit_order_is_msb_first"`
- **`test_a_relabelled_split_bit_is_refused`**
  `pytest "python/tests/test_ward_trie.py::test_a_relabelled_split_bit_is_refused"`
- **`test_malformed_proofs_are_refused_before_hashing`**
  `pytest "python/tests/test_ward_trie.py::test_malformed_proofs_are_refused_before_hashing"`
- **`test_widths_are_enforced`**
  `pytest "python/tests/test_ward_trie.py::test_widths_are_enforced"`
- **`test_an_unsettled_root_is_refused`**
  `pytest "python/tests/test_ward_trie.py::test_an_unsettled_root_is_refused"`
- **`test_a_non_empty_tree_needs_a_witness`**
  `pytest "python/tests/test_ward_trie.py::test_a_non_empty_tree_needs_a_witness"`
- **`test_derived_roots_match_the_canonical_rebuild`** — Every insert/update/delete root the verifier derives equals the store's rebuilt root.
  `pytest "python/tests/test_ward_trie.py::test_derived_roots_match_the_canonical_rebuild"`
- **`test_membership_proof_refuses_an_absent_key`**
  `pytest "python/tests/test_ward_trie.py::test_membership_proof_refuses_an_absent_key"`
- **`test_a_one_leaf_tree_has_the_leaf_as_its_root`**
  `pytest "python/tests/test_ward_trie.py::test_a_one_leaf_tree_has_the_leaf_as_its_root"`
- **`test_children_are_positional`**
  `pytest "python/tests/test_ward_trie.py::test_children_are_positional"`
- **`test_links_are_named_and_still_tuples`**
  `pytest "python/tests/test_ward_trie.py::test_links_are_named_and_still_tuples"`
- **`test_the_newest_link_into_a_state_wins`** — A counter reached twice -- a write, then a REVERT -- serves the later edge.
  `pytest "python/tests/test_ward_trie.py::test_the_newest_link_into_a_state_wins"`
- **`test_fork_point`**
  `pytest "python/tests/test_ward_trie.py::test_fork_point"`
- **`test_scratch_serves_each_batched_change_against_the_running_root`** — Play the device: prove each change against the root built so far, from `scratch(staged)`.
  `pytest "python/tests/test_ward_trie.py::test_scratch_serves_each_batched_change_against_the_running_root"`
- **`test_apply_records_one_link_for_a_batch`**
  `pytest "python/tests/test_ward_trie.py::test_apply_records_one_link_for_a_batch"`
- **`test_only_the_sealed_content_is_committed`** — value_digest = sha256(0x03 \|\| sealed_content): the identity is stored beside the leaf and changes nothing in the tree; an empty content is a delete.
  `pytest "python/tests/test_ward_trie.py::test_only_the_sealed_content_is_committed"`

#### `python/tests/test_ward_relay.py` (13)

Run the file: `pytest python/tests/test_ward_relay.py`

- **`test_hello_sends_the_token_and_no_origin`**
  `pytest "python/tests/test_ward_relay.py::test_hello_sends_the_token_and_no_origin"`
- **`test_a_wrong_token_is_refused_with_its_code`**
  `pytest "python/tests/test_ward_relay.py::test_a_wrong_token_is_refused_with_its_code"`
- **`test_open_store_sends_only_the_ward_owner_secret`**
  `pytest "python/tests/test_ward_relay.py::test_open_store_sends_only_the_ward_owner_secret"`
- **`test_wardd_not_running_is_said_plainly`**
  `pytest "python/tests/test_ward_relay.py::test_wardd_not_running_is_said_plainly"`
- **`test_a_conversation_answers_each_device_call_in_order`**
  `pytest "python/tests/test_ward_relay.py::test_a_conversation_answers_each_device_call_in_order"`
- **`test_a_device_that_raises_is_answered_as_a_failure`**
  `pytest "python/tests/test_ward_relay.py::test_a_device_that_raises_is_answered_as_a_failure"`
- **`test_a_message_outside_the_sync_conversation_never_reaches_the_device`**
  `pytest "python/tests/test_ward_relay.py::test_a_message_outside_the_sync_conversation_never_reaches_the_device"`
- **`test_an_oversized_or_masked_frame_is_refused`**
  `pytest "python/tests/test_ward_relay.py::test_an_oversized_or_masked_frame_is_refused"`
- **`test_large_frames_and_error_codes`**
  `pytest "python/tests/test_ward_relay.py::test_large_frames_and_error_codes"`
- **`test_session_device_maps_names_to_messages_and_back`**
  `pytest "python/tests/test_ward_relay.py::test_session_device_maps_names_to_messages_and_back"`
- **`test_the_provider_converts_wardds_answer_and_sends_the_staged_set`**
  `pytest "python/tests/test_ward_relay.py::test_the_provider_converts_wardds_answer_and_sends_the_staged_set"`
- **`test_websocket_refuses_a_non_ws_url`**
  `pytest "python/tests/test_ward_relay.py::test_websocket_refuses_a_non_ws_url"`
- **`test_against_wardd_sync_flush_status`**
  `pytest "python/tests/test_ward_relay.py::test_against_wardd_sync_flush_status"`

#### `tests/test_ward_stack.py` (17)

Run the file: `pytest tests/test_ward_stack.py`

- **`test_propagates_ports_to_every_nix_shell`**
  `pytest "tests/test_ward_stack.py::test_propagates_ports_to_every_nix_shell"`
- **`test_command_line_port_overrides_environment`**
  `pytest "tests/test_ward_stack.py::test_command_line_port_overrides_environment"`
- **`test_wardd_replicates_through_the_relay_and_logs_verbosely`**
  `pytest "tests/test_ward_stack.py::test_wardd_replicates_through_the_relay_and_logs_verbosely"`
- **`test_wardd_asks_the_separate_wm_which_keeps_its_own_state`**
  `pytest "tests/test_ward_stack.py::test_wardd_asks_the_separate_wm_which_keeps_its_own_state"`
- **`test_the_second_device_has_its_own_wardd_and_emulator_and_waits_for_the_adapter`**
  `pytest "tests/test_ward_stack.py::test_the_second_device_has_its_own_wardd_and_emulator_and_waits_for_the_adapter"`
- **`test_emulator_log_keeps_only_ward_lines`**
  `pytest "tests/test_ward_stack.py::test_emulator_log_keeps_only_ward_lines"`
- **`test_wm_down_is_requested_by_a_file_in_the_run_directory`**
  `pytest "tests/test_ward_stack.py::test_wm_down_is_requested_by_a_file_in_the_run_directory"`
- **`test_rejects_one_port_for_the_wm_and_wardd`**
  `pytest "tests/test_ward_stack.py::test_rejects_one_port_for_the_wm_and_wardd"`
- **`test_relay_debug_reaches_only_the_relay`**
  `pytest "tests/test_ward_stack.py::test_relay_debug_reaches_only_the_relay"`
- **`test_full_log_is_enabled_and_announced`**
  `pytest "tests/test_ward_stack.py::test_full_log_is_enabled_and_announced"`
- **`test_combined_log_preserves_concurrent_records`**
  `pytest "tests/test_ward_stack.py::test_combined_log_preserves_concurrent_records"`
- **`test_copy_log_merges_stdout_stderr_and_final_partial_line`**
  `pytest "tests/test_ward_stack.py::test_copy_log_merges_stdout_stderr_and_final_partial_line"`
- **`test_rejects_occupied_ports_before_launching`**
  `pytest "tests/test_ward_stack.py::test_rejects_occupied_ports_before_launching"`
- **`test_rejects_the_default_device_port`**
  `pytest "tests/test_ward_stack.py::test_rejects_the_default_device_port"`
- **`test_rejects_one_port_for_relay_and_wardd`**
  `pytest "tests/test_ward_stack.py::test_rejects_one_port_for_relay_and_wardd"`
- **`test_stop_releases_the_emulator_wait_command`**
  `pytest "tests/test_ward_stack.py::test_stop_releases_the_emulator_wait_command"`
- **`test_display_is_visible_by_default_and_hidden_only_explicitly`**
  `pytest "tests/test_ward_stack.py::test_display_is_visible_by_default_and_hidden_only_explicitly"`

#### `tests/test_ward_wm.py` (29)

The mock WARD Manager (`tests/ward_wm.py`): enrolment, compare-and-swap, sessions, acceptance records, and a register that goes back. Run the file: `pytest tests/test_ward_wm.py`

- **`test_an_unenrolled_wallet_cannot_be_advanced_at_all`** — ENROLMENT IS NOT AN ADVANCE, and cannot be folded into one.
  `pytest "tests/test_ward_wm.py::test_an_unenrolled_wallet_cannot_be_advanced_at_all"`
- **`test_head_init_must_be_authorised`**
  `pytest "tests/test_ward_wm.py::test_head_init_must_be_authorised"`
- **`test_head_init_names_the_head_it_opens`** — A signature over one opening head must not open a different one.
  `pytest "tests/test_ward_wm.py::test_head_init_names_the_head_it_opens"`
- **`test_a_first_head_starts_at_zero`** — SIGNED FOR COUNTER 7, so the rule under test is the one that actually fires.
  `pytest "tests/test_ward_wm.py::test_a_first_head_starts_at_zero"`
- **`test_an_advance_attests_the_head_it_created`** — Not "the head now", which a concurrent winner could have moved -- the whole reason CAS and attestation are one call.
  `pytest "tests/test_ward_wm.py::test_an_advance_attests_the_head_it_created"`
- **`test_a_stale_predecessor_is_a_conflict_not_an_overwrite`** — The device must be told it lost, so it can sync and retry, rather than have its transition silently replace the winner's.
  `pytest "tests/test_ward_wm.py::test_a_stale_predecessor_is_a_conflict_not_an_overwrite"`
- **`test_the_predecessor_root_is_compared_too`** — Two forks can share a counter, so the counter alone does not identify a head.
  `pytest "tests/test_ward_wm.py::test_the_predecessor_root_is_compared_too"`
- **`test_a_head_advances_by_one_to_max_batch`** — A batch is one transition carrying several changes; anything longer is refused.
  `pytest "tests/test_ward_wm.py::test_a_head_advances_by_one_to_max_batch"`
- **`test_an_unauthorised_transition_is_refused`** — The WM verifies with `ward_id` alone -- no enrolment, and no second per-wallet secret.
  `pytest "tests/test_ward_wm.py::test_an_unauthorised_transition_is_refused"`
- **`test_a_signature_for_another_transition_is_refused`**
  `pytest "tests/test_ward_wm.py::test_a_signature_for_another_transition_is_refused"`
- **`test_a_read_only_first_use_can_attest_without_publishing`** — A read may be a wallet's first WARD operation, so the WM has to be able to bootstrap from an attestation request rather than only from a write.
  `pytest "tests/test_ward_wm.py::test_a_read_only_first_use_can_attest_without_publishing"`
- **`test_enrolment_is_genesis_only`** — A WM MAY BE ENROLLED AT COUNTER 0 AND NOWHERE ELSE.
  `pytest "tests/test_ward_wm.py::test_enrolment_is_genesis_only"`
- **`test_a_read_only_bootstrap_is_authorised_too`**
  `pytest "tests/test_ward_wm.py::test_a_read_only_bootstrap_is_authorised_too"`
- **`test_a_revert_is_authorised_but_distinguishable`** — The WM accepts a demotion and can TELL it was one.
  `pytest "tests/test_ward_wm.py::test_a_revert_is_authorised_but_distinguishable"`
- **`test_a_revert_signature_is_not_accepted_as_an_ordinary_advance`** — The two tags are not interchangeable in either direction.
  `pytest "tests/test_ward_wm.py::test_a_revert_signature_is_not_accepted_as_an_ordinary_advance"`
- **`test_an_authorisation_moves_the_head_at_most_once`** — THE COMPARE-AND-SWAP, stated as the attack it closes.
  `pytest "tests/test_ward_wm.py::test_an_authorisation_moves_the_head_at_most_once"`
- **`test_one_session_carries_several_transitions`** — The session is the device's sync, not the head:
  `pytest "tests/test_ward_wm.py::test_one_session_carries_several_transitions"`
- **`test_a_new_sync_ends_the_session`** — An authorisation minted in one sync is refused once any device of the wallet syncs again:
  `pytest "tests/test_ward_wm.py::test_a_new_sync_ends_the_session"`
- **`test_known_gap_a_host_can_reopen_an_old_session`** — KNOWN GAP, pinned so it is noticed when closed.
  `pytest "tests/test_ward_wm.py::test_known_gap_a_host_can_reopen_an_old_session"`
- **`test_an_advance_returns_the_wm_signed_acceptance`** — The WM's own record of the transition, under the session nonce:
  `pytest "tests/test_ward_wm.py::test_an_advance_returns_the_wm_signed_acceptance"`
- **`test_a_restored_wm_is_rolled_forward_by_steps_signed_again`**
  `pytest "tests/test_ward_wm.py::test_a_restored_wm_is_rolled_forward_by_steps_signed_again"`
- **`test_a_restored_wm_refuses_the_devices_authorisations`** — The session nonce is volatile, so a restore ends every session:
  `pytest "tests/test_ward_wm.py::test_a_restored_wm_refuses_the_devices_authorisations"`
- **`test_a_lost_race_has_no_record_to_be_signed_again_from`** — Two devices mint from the same head; one lands.
  `pytest "tests/test_ward_wm.py::test_a_lost_race_has_no_record_to_be_signed_again_from"`
- **`test_a_stale_session_named_for_diagnostics_explains_the_refusal`** — The host may say which session it believes is current.
  `pytest "tests/test_ward_wm.py::test_a_stale_session_named_for_diagnostics_explains_the_refusal"`
- **`test_a_restored_wm_can_be_stopped_at_any_prefix`** — THE COST that remains:
  `pytest "tests/test_ward_wm.py::test_a_restored_wm_can_be_stopped_at_any_prefix"`
- **`test_a_re_enrolled_wm_refuses_a_kept_first_write`** — `head_init_sig` is not secret, so a WM that lost everything can be enrolled again at genesis.
  `pytest "tests/test_ward_wm.py::test_a_re_enrolled_wm_refuses_a_kept_first_write"`
- **`test_a_failover_takes_the_record_as_it_stands`**
  `pytest "tests/test_ward_wm.py::test_a_failover_takes_the_record_as_it_stands"`
- **`test_a_restore_onto_the_current_head_changes_nothing_visible`**
  `pytest "tests/test_ward_wm.py::test_a_restore_onto_the_current_head_changes_nothing_visible"`
- **`test_a_lost_wallet_can_only_come_back_at_genesis`**
  `pytest "tests/test_ward_wm.py::test_a_lost_wallet_can_only_come_back_at_genesis"`

### Suite: ward-core and wardd (jest)

From the Suite worktree. `-t` selects one test by its title.


#### `packages/ward-core/src/__tests__/conformance.test.ts` (8)

Run the file: `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts`

- **`agrees on the empty root`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'agrees on the empty root'`
- **`verifies the firmware frozen vectors`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'verifies the firmware frozen vectors'`
- **`computes every commit the reference does`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'computes every commit the reference does'`
- **`serves a batch from the staged scratch tree exactly as the reference does`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'serves a batch from the staged scratch tree exactly as the reference does'`
- **`agrees on the transition log: newest link wins, and the fork point`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'agrees on the transition log: newest link wins, and the fork point'`
- **`refuses malformed proofs before hashing`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'refuses malformed proofs before hashing'`
- **`refuses an unsettled root and a witness-less insert on a non-empty tree`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'refuses an unsettled root and a witness-less insert on a non-empty tree'`
- **`ignores the identity and reads an empty content as a delete`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/conformance.test.ts -t 'ignores the identity and reads an empty content as a delete'`

#### `packages/ward-core/src/__tests__/serve.test.ts` (5)

Run the file: `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts`

- **`proves each batched change against the running root, via the staged leaves`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts -t 'proves each batched change against the running root, via the staged leaves'`
- **`answers a present key with its leaf and a membership proof`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts -t 'answers a present key with its leaf and a membership proof'`
- **`records ONE link per write, and serves them back newest first`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts -t 'records ONE link per write, and serves them back newest first'`
- **`refuses a batch that does not start at the store counter`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts -t 'refuses a batch that does not start at the store counter'`
- **`treats a result with no authorisation as no transition`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/serve.test.ts -t 'treats a result with no authorisation as no transition'`

#### `packages/ward-core/src/__tests__/wm.test.ts` (10)

Run the file: `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts`

- **`uses the debug key the emulator trusts`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'uses the debug key the emulator trusts'`
- **`signs %s exactly as MockWM does`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'signs .* exactly as MockWM does'`
- **`verifies the wm_sig ward_keys mints, under the right tag only`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'verifies the wm_sig ward_keys mints, under the right tag only'`
- **`accepts the head_init_sig ward_keys mints`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'accepts the head_init_sig ward_keys mints'`
- **`enrols at genesis, and attests against the round nonce`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'enrols at genesis, and attests against the round nonce'`
- **`advances on a genuine wm_sig, and refuses a replay`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'advances on a genuine wm_sig, and refuses a replay'`
- **`carries several transitions in one session, and a new sync ends it`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'carries several transitions in one session, and a new sync ends it'`
- **`after a restore, refuses a stored wm_sig and takes the step signed again in a new session`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'after a restore, refuses a stored wm_sig and takes the step signed again in a new session'`
- **`says when a refused advance names a session that has ended (diagnostics only)`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'says when a refused advance names a session that has ended (diagnostics only)'`
- **`accepts a batch of up to MAX_BATCH and a revert, and refuses a forged step`**
  `yarn workspace @trezor/ward-core test:unit --coverage=0 src/__tests__/wm.test.ts -t 'accepts a batch of up to MAX_BATCH and a revert, and refuses a forged step'`

#### `packages/wardd/src/__tests__/connect.test.ts` (7)

Run the file: `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts`

- **`syncs a fresh wallet, asking the device for its ward_id`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'syncs a fresh wallet, asking the device for its ward_id'`
- **`flushes a batch in one session, pulls carried back to wardd`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'flushes a batch in one session, pulls carried back to wardd'`
- **`brings a second device up along the chain, then reports both heads`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'brings a second device up along the chain, then reports both heads'`
- **`keeps wardd's refusal code in Connect's error`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'keeps wardd'"'"'s refusal code in Connect'"'"'s error'`
- **`carries a device Failure back to wardd, which ends the call as device_failure`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'carries a device Failure back to wardd, which ends the call as device_failure'`
- **`answers a device's pulls from wardd's replica`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'answers a device'"'"'s pulls from wardd'"'"'s replica'`
- **`walks a second device up the chain with catchUp, persisting nothing`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/connect.test.ts -t 'walks a second device up the chain with catchUp, persisting nothing'`

#### `packages/wardd/src/__tests__/evoluBackend.test.ts` (9)

Run the file: `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts`

- **`stores a link whole, once`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'stores a link whole, once'`
- **`resolves when the write completes, and stops listening`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'resolves when the write completes, and stops listening'`
- **`rejects when Evolu reports an error while the write is pending`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'rejects when Evolu reports an error while the write is pending'`
- **`ignores an error that was already there before the write began`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'ignores an error that was already there before the write began'`
- **`rejects a write that never settles, after the timeout`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'rejects a write that never settles, after the timeout'`
- **`rejects when starting the write throws, and a late completion changes nothing`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'rejects when starting the write throws, and a late completion changes nothing'`
- **`rejects instead of hanging`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'rejects instead of hanging'`
- **`keeps one WM attestation per step, the latest, apart from the links`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'keeps one WM attestation per step, the latest, apart from the links'`
- **`opens the same Evolu owner for the same WARD secret`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/evoluBackend.test.ts -t 'opens the same Evolu owner for the same WARD secret'`

#### `packages/wardd/src/__tests__/host.test.ts` (38)

Run the file: `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts`

- **`characterizes replica work for queued catch-up after its caller disconnects`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'characterizes replica work for queued catch-up after its caller disconnects'`
- **`enrols the wallet at genesis and brings the device online`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'enrols the wallet at genesis and brings the device online'`
- **`flushes one change per transition, and the device ends where the replica does`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'flushes one change per transition, and the device ends where the replica does'`
- **`serves each link's kept WM attestation when the device asks (WardRollback)`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'serves each link's kept WM attestation when the device asks (WardRollback)'`
- **`reconciles a device already at the head above genesis, whose root it is not told`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'reconciles a device already at the head above genesis, whose root it is not told'`
- **`updates and deletes through the same path`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'updates and deletes through the same path'`
- **`adding and then deleting an entry leaves the root from before the add`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'adding and then deleting an entry leaves the root from before the add'`
- **`folds a batch into ONE transition, stored as one link`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'folds a batch into ONE transition, stored as one link'`
- **`brings a second device several steps behind up along the chain`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'brings a second device several steps behind up along the chain'`
- **`refuses to rejoin a forked device unless asked, then discards its branch`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses to rejoin a forked device unless asked, then discards its branch'`
- **`decides reconcile, chain walk or rejoin correctly across a batched transition`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'decides reconcile, chain walk or rejoin correctly across a batched transition'`
- **`refuses a result minted on a head that has since moved, and stores nothing of it`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result minted on a head that has since moved, and stores nothing of it'`
- **`refuses a result at the right counter but minted over a different root`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result at the right counter but minted over a different root'`
- **`refuses a sync from a device on another wallet`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a sync from a device on another wallet'`
- **`turns a device refusal into device_failure`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'turns a device refusal into device_failure'`
- **`refuses a result minted before the same device synced again`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result minted before the same device synced again'`
- **`refuses a result once another device of the wallet has synced`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses a result once another device of the wallet has synced'`
- **`is refused by the WM itself when a host skips its own check`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is refused by the WM itself when a host skips its own check'`
- **`is rolled forward through the device, which signs the accepted transitions again`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is rolled forward through the device, which signs the accepted transitions again'`
- **`is not rolled forward by a device that is not ahead of the restored WM`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is not rolled forward by a device that is not ahead of the restored WM'`
- **`fails a device ahead of the WM with wm_behind when roll-forward is off`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'fails a device ahead of the WM with wm_behind when roll-forward is off'`
- **`is not rolled forward on the deprecated service path`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is not rolled forward on the deprecated service path'`
- **`is not rolled forward onto a branch it is not on`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is not rolled forward onto a branch it is not on'`
- **`stops at the first step without a kept WM record`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'stops at the first step without a kept WM record'`
- **`is not signed again by a device whose own head is off the replayed chain`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'is not signed again by a device whose own head is off the replayed chain'`
- **`the device refuses a forged or misplaced WM record, and signs nothing`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'the device refuses a forged or misplaced WM record, and signs nothing'`
- **`never replays a device signature: a restore ends the session`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'never replays a device signature: a restore ends the session'`
- **`publishes nothing and releases the wallet`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'publishes nothing and releases the wallet'`
- **`leaves out a stored link that does not reproduce its own root, and says so`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'leaves out a stored link that does not reproduce its own root, and says so'`
- **`falls back to the highest head that still builds, past a corrupt row`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'falls back to the highest head that still builds, past a corrupt row'`
- **`narrates a rebuild: the walk back to genesis, each step's entries, each root`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'narrates a rebuild: the walk back to genesis, each step's entries, each root'`
- **`says when the head asked for cannot be built`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'says when the head asked for cannot be built'`
- **`keeps the dev WM across a restart`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'keeps the dev WM across a restart'`
- **`flushes by storing each change and catching the device up to it, persisted`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'flushes by storing each change and catching the device up to it, persisted'`
- **`syncs another device of the wallet by a catch-up it persists`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'syncs another device of the wallet by a catch-up it persists'`
- **`refuses to store a step this wallet's device did not sign`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses to store a step this wallet's device did not sign'`
- **`refuses the service channel, which needs a WM`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'refuses the service channel, which needs a WM'`
- **`cannot be given a WM as well`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/host.test.ts -t 'cannot be given a WM as well'`

#### `packages/wardd/src/__tests__/replica.test.ts` (8)

The replica leaves out a stored row that does not reproduce its own root, and rebuilds without it. The adversarial four are also listed in [Adversarial testing](ward_adversarial_testing.md).

- **`keeps serving the valid head, and taking writes, after a corrupt row lands above it`** — Without a WM: the corrupt row is left out, another device still catches up, and a write lands at the very counter the corrupt row claims.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "keeps serving the valid head, and taking writes, after a corrupt row lands above it"`
- **`never replays, or counts, a corrupt row that no head is built through`** — With a WM: a corrupt dead sibling beside the WM's head is never replayed.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "never replays, or counts, a corrupt row that no head is built through"`
- **`says it is behind when the WM's head builds only through a corrupt row, and recovers once the row is restored`** — A sync is refused as `internal` rather than crashing, and re-storing the genuine row under its id heals the replica.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "says it is behind when the WM's head builds only through a corrupt row, and recovers once the row is restored"`
- **`rewriting a stored row under its id costs that head, and never walks a device back`** — A peer overwrites a genuine row's changes: the replica falls back one head, and the device holding the newer head refuses the older one.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "rewriting a stored row under its id costs that head, and never walks a device back"`
- **`a tower of corrupt rows stacked above the head does not hide it`** — Thirty chained corrupt rows: only the first is replayed and left out; nothing above it reaches genesis.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "a tower of corrupt rows stacked above the head does not hide it"`
- **`a corrupt second path into the real head is passed over for the genuine one`** — A newer corrupt row ending at the real head is tried first, left out, and the device walks the genuine chain.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "a corrupt second path into the real head is passed over for the genuine one"`
- **`with a WM, corrupt rows above its head do not move the head the replica serves`** — The replica is built at the WM's head, so corrupt rows above it are never replayed.
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t "with a WM, corrupt rows above its head do not move the head the replica serves"`
- **`characterizes predecessor lookup work during a linear replica rebuild`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/replica.test.ts -t 'characterizes predecessor lookup work during a linear replica rebuild'`

#### `packages/wardd/src/__tests__/server.test.ts` (10)

Run the file: `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts`

- **`refuses a page from an origin not on the allow-list`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'refuses a page from an origin not on the allow-list'`
- **`admits an allowed origin, and a client that sends none`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'admits an allowed origin, and a client that sends none'`
- **`refuses everything before hello, and closes on a wrong token`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'refuses everything before hello, and closes on a wrong token'`
- **`refuses another major version`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'refuses another major version'`
- **`wants a store before a wallet call`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'wants a store before a wallet call'`
- **`relays a whole flush, pulls included, through the client`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'relays a whole flush, pulls included, through the client'`
- **`refuses the ADVERSARIAL TEST methods unless started with --adversarial-tests`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'refuses the ADVERSARIAL TEST methods unless started with --adversarial-tests'`
- **`serves an older state on request, and the device refuses it`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'serves an older state on request, and the device refuses it'`
- **`accepts a WARD owner credential and rejects the legacy parent field`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'accepts a WARD owner credential and rejects the legacy parent field'`
- **`releases the wallet after a device reply deadline and lets another client finish`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/server.test.ts -t 'releases the wallet after a device reply deadline and lets another client finish'`

#### `packages/wardd/src/__tests__/service.test.ts` (10)

Run the file: `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts`

- **`enrols at genesis, then publishes, with the device adopting each attested step`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'enrols at genesis, then publishes, with the device adopting each attested step'`
- **`answers a fetch from a head it does not hold with WardSyncRequired`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'answers a fetch from a head it does not hold with WardSyncRequired'`
- **`refuses a publish built on a head the WM has moved past, as a definitive conflict`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'refuses a publish built on a head the WM has moved past, as a definitive conflict'`
- **`ADVERSARIAL: refuses a publish whose session a later sync ended`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'ADVERSARIAL: refuses a publish whose session a later sync ended'`
- **`pages history larger than the wire buffer against a single attestation`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'pages history larger than the wire buffer against a single attestation'`
- **`resumes from its state file: the same replica, the same WM head`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'resumes from its state file: the same replica, the same WM head'`
- **`chunks and reassembles a message spanning several packets`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'chunks and reassembles a message spanning several packets'`
- **`reads a probe's Failure code, and refuses what is not one`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'reads a probe's Failure code, and refuses what is not one'`
- **`round-trips a sealed publish`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'round-trips a sealed publish'`
- **`binds, serves sync / fetch / publish, logs every exchange, and stops`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/service.test.ts -t 'binds, serves sync / fetch / publish, logs every exchange, and stops'`

#### `packages/wardd/src/__tests__/wmServer.test.ts` (10)

Run the file: `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts`

- **`enrols, attests and advances for wardd as the in-process WM does`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'enrols, attests and advances for wardd as the in-process WM does'`
- **`refuses a stale advance as a conflict`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'refuses a stale advance as a conflict'`
- **`keeps its heads across a restart`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'keeps its heads across a restart'`
- **`rejects malformed requests without touching the state`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'rejects malformed requests without touching the state'`
- **`reports it, fails a sync as wm_unavailable, and still serves its last head`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'reports it, fails a sync as wm_unavailable, and still serves its last head'`
- **`walks a device that never synced up to its head, without the WM`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'walks a device that never synced up to its head, without the WM'`
- **`stops at the newest head a kept WM attestation names, below the replica head`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'stops at the newest head a kept WM attestation names, below the replica head'`
- **`with no kept attestation, offers the head bare, which a WM device refuses`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'with no kept attestation, offers the head bare, which a WM device refuses'`
- **`with no kept attestation, moves a device built without a WM, which persists`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'with no kept attestation, moves a device built without a WM, which persists'`
- **`keeps one proof per WM head across sync rounds and can use it offline`**
  `yarn workspace @trezor/wardd test:unit --coverage=0 src/__tests__/wmServer.test.ts -t 'keeps one proof per WM head across sync rounds and can use it offline'`
