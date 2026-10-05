# flake8: noqa: F403,F405
from common import *  # isort:skip

import apps.common.seed as seed_module
from apps.ward import cas as CAS
from apps.ward import offline_store as OS
from apps.ward import root as R
from apps.ward.keys import derive_k_auth, derive_ward_id
from trezor import config

# ---------------------------------------------------------------------------
# Settling a queued write: does the head that was adopted belong to MY change?
#
# `offline_store.reconcile_pending` is the only place a queued write stops being queued, and
# until 3a9ca2ebbf it decided on the counter alone -- `claimed <= adopted`. That is "the head
# reached N", not "MY change is what made it N", and the difference is a change the user
# approved being silently discarded whenever another device of the same wallet won the race
# for a counter.
#
# THE ONLY TESTS IN THE SUITE THAT DRIVE THIS FUNCTION. The rest of the WARD unit tests are
# pure -- hashes, preimages, proofs -- so they need no seed and no storage. This one needs
# both: real `storage.ward` slots for the records and the claim journal, and a real key
# schedule, because what settlement compares is an `auth_commit` minted under K_auth.
# ---------------------------------------------------------------------------

_SEED = b"\x5a" * 64

_AT_41 = b"\x41" * 32  # the head this device is sitting on
_MINE = b"\xaa" * 32  # the root MY candidate would produce
_THEIRS = b"\xbb" * 32  # the root another device's candidate produced


class TestWardClaimSettlement(unittest.TestCase):
    """`reconcile_pending`: a claim settles against the root its authorisation names."""

    def setUp(self):
        config.init()
        config.wipe()
        config.unlock("", None)

        # PATCHED, NOT FAKED. The seed is a fixed value so the derivations are reproducible, but
        # everything below it -- SLIP-21, K_auth, ward_id, the auth_commit preimage -- is the real
        # code. A stubbed key schedule would let a settlement bug hide behind a stubbed comparison.
        self._saved = (seed_module.get_seed, R.get_counter, R.get_root)

        async def _seed():
            return _SEED

        async def _counter():
            return 41

        async def _root():
            return _AT_41

        seed_module.get_seed = _seed
        R.get_counter = _counter
        R.get_root = _root

    # --- helpers -----------------------------------------------------------------

    def _offer(self, counter, to_root, identifier=b"addr1"):
        """Queue a change, hand it to a host, and file the claim its authorisation names.

        Mirrors what `flush_queue` does: mint the transition's `auth_commit` over
        (counter-1, our head) -> (counter, the candidate's root), then `mark_offered`.
        """
        await_result(OS.put("address", "btc", identifier, b"v1", True))
        _status, entry = await_result(OS.get("address", "btc", identifier))
        step = CAS.auth_commit(
            await_result(derive_k_auth()),
            await_result(derive_ward_id()),
            counter - 1,
            _AT_41,
            counter,
            to_root,
        )
        await_result(OS.mark_offered(entry, counter, step))
        return step

    def _state(self, identifier=b"addr1"):
        _status, entry = await_result(OS.get("address", "btc", identifier))
        return entry.pending, entry.offered

    # --- the regression ----------------------------------------------------------

    def test_a_lost_race_leaves_the_change_queued(self):
        """THE BUG 3a9ca2ebbf FIXED, stated as the scenario that produces it.

        Two devices of one wallet both sit at 41 and each build a candidate 42. The WM takes the
        other one. This device reconciles to the winner's 42 -- an ordinary forward adoption, and
        reconcile's same-counter check does not fire, because this device's persisted head is
        still 41 and it sees 41 -> 42.

        On `claimed <= adopted` the claim settled and the record stopped being queued: a change
        the user approved, never written, silently demoted to a cached copy. It must stay PENDING.
        """
        self._offer(42, _MINE)
        self.assertEqual(self._state(), (True, True))

        await_result(OS.reconcile_pending(42, _THEIRS))

        pending, offered = self._state()
        self.assertTrue(pending)  # still queued, because it never landed
        self.assertFalse(offered)  # ...and offerable again, so flush_queue retries it

    def test_a_won_race_settles_the_change(self):
        """The converse, and the reason "never settle without a chain" was not the answer.

        If the adopted head is the one this claim's authorisation names, it settled -- once. Were
        this to answer "not landed" the record would go back to PENDING, be re-offered, file a new
        claim, and the next counter-path reconcile could not settle that one either: a republish
        loop for any host that only ever calls WardReconcile.
        """
        self._offer(42, _MINE)

        await_result(OS.reconcile_pending(42, _MINE))

        self.assertEqual(self._state(), (False, False))

    def test_a_multi_step_jump_is_not_decidable_and_stays_queued(self):
        """The head moved several counters and one root cannot say where this claim sits.

        Resolving as NOT landed is the safe direction -- a redundant republish rather than silent
        loss -- and it converges, since the republish is filed from the new head and the next
        adoption is the single step this can decide.
        """
        self._offer(42, _MINE)

        await_result(OS.reconcile_pending(45, _MINE))

        self.assertEqual(self._state(), (True, False))

    def test_a_verified_chain_settles_by_its_own_authorisation(self):
        """The precise path: the caller crossed the transitions and says which.

        No root comparison is needed or wanted here -- a claim landed exactly when its own
        `auth_commit` is among the ones the chain proved.
        """
        step = self._offer(42, _MINE)

        await_result(OS.reconcile_pending(42, _THEIRS, landed_commits=[step]))

        # settled despite the adopted root differing, because the chain named this transition
        self.assertEqual(self._state(), (False, False))

    def test_another_wallets_claim_is_untouched(self):
        """Settlement is scoped by wallet_id, which is what stops one wallet's reconciliation
        from rewriting another's queued records. Here the same device, a different claim."""
        self._offer(42, _MINE, identifier=b"addr1")
        self._offer(42, _MINE, identifier=b"addr2")

        await_result(OS.reconcile_pending(42, _THEIRS))

        # both are this wallet's, so both are settled the same way -- neither is lost
        self.assertEqual(self._state(b"addr1"), (True, False))
        self.assertEqual(self._state(b"addr2"), (True, False))

    # --- unreadable records ------------------------------------------------------

    def _corrupt(self, identifier):
        """Make a stored record unparseable in place: its value length now runs off the end."""
        from storage import ward as ward_store

        _status, entry = await_result(OS.get("address", "btc", identifier))
        off = OS._flags_off(entry.raw) + 1
        raw = entry.raw[:off] + b"\xff\xff" + entry.raw[off + 2 :]
        ward_store.store_write_slot(entry.slot, raw)
        return entry.slot, raw

    def _patch_warning(self, answer=None):
        import trezor.ui.layouts as layouts

        shown = []
        saved = layouts.show_warning

        async def _warn(br_name, content, *args, **kwargs):
            shown.append(br_name)
            if answer is not None:
                raise answer

        layouts.show_warning = _warn
        self.addCleanup(lambda: setattr(layouts, "show_warning", saved))
        return shown

    def addCleanup(self, fn):
        self._cleanups = getattr(self, "_cleanups", []) + [fn]

    def tearDown(self):
        for fn in getattr(self, "_cleanups", []):
            fn()
        self._cleanups = []
        seed_module.get_seed, R.get_counter, R.get_root = self._saved

    def test_an_unreadable_record_is_warned_about_then_skipped(self):
        """One corrupt record must not block every sync, but it is skipped only after a warning."""
        from storage import ward as ward_store

        self._offer(42, _MINE, identifier=b"addr1")
        self._offer(42, _MINE, identifier=b"addr2")
        slot, raw = self._corrupt(b"addr1")
        shown = self._patch_warning()

        await_result(OS.reconcile_pending(42, _MINE))

        self.assertEqual(shown, ["ward_unreadable_claim"])
        self.assertEqual(ward_store.store_read_slot(slot), raw)  # left as it was
        self.assertEqual(self._state(b"addr2"), (False, False))  # the rest still settles
        from apps.ward.keys import derive_wallet_id

        self.assertEqual(ward_store.claim_list(await_result(derive_wallet_id())), [])

    def test_declining_the_warning_changes_nothing(self):
        from storage import ward as ward_store
        from trezor.wire import ActionCancelled

        from apps.ward.keys import derive_wallet_id

        self._offer(42, _MINE, identifier=b"addr1")
        self._offer(42, _MINE, identifier=b"addr2")
        self._corrupt(b"addr1")
        self._patch_warning(ActionCancelled())
        claims = ward_store.claim_list(await_result(derive_wallet_id()))

        with self.assertRaises(ActionCancelled):
            await_result(OS.reconcile_pending(42, _MINE))

        self.assertEqual(ward_store.claim_list(await_result(derive_wallet_id())), claims)
        self.assertEqual(self._state(b"addr2"), (True, True))

    def test_named_tells_a_corrupt_entry_from_another_unreadable_record(self):
        """`get` says CORRUPT for both; only `named` says which one an erase would remove."""
        await_result(OS.put("address", "btc", b"addr1", b"v1", True))
        self._corrupt(b"addr1")

        self.assertEqual(await_result(OS.get("address", "btc", b"addr1"))[0], OS.CORRUPT)
        self.assertTrue(await_result(OS.named("address", "btc", b"addr1")))
        self.assertFalse(await_result(OS.named("address", "btc", b"addr9")))


if __name__ == "__main__":
    unittest.main()
