# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import ward as ward_store
from trezor import config

_WALLET_A = b"\xa0" * 16
_WALLET_B = b"\xb0" * 16

def _identity(identifier, key_type=b"address", app_id=b"btc"):
    """The bytes a record is FOUND by, framed the way `offline_store.identity_block` frames them.

    Deliberately assembled HERE rather than imported, as with `_record`: this file is about the
    storage layer's slot behaviour, and it treats an identity as opaque bytes -- which is exactly
    the contract `store_find` documents.
    """
    return (
        bytes([len(key_type)])
        + key_type
        + bytes([len(app_id)])
        + app_id
        + len(identifier).to_bytes(2, "big")
        + identifier
    )


_ID_1 = _identity(b"addr1")
_ID_2 = _identity(b"addr2")


def _full(identity):
    """A candidate list naming the FULL form only -- what most of these tests store."""
    return [(ward_store.STORE_VERSION, identity)]


def _record(wallet_id, identity, payload=b"value", pending=False):
    """A minimal well-formed record, built the way `offline_store.encode_record` builds one.

    Deliberately assembled HERE rather than imported: this file is about the storage layer's
    slot behaviour, and importing the encoder would make a change to the record format able to
    break these tests for reasons that have nothing to do with what they assert.
    """
    return (
        ward_store.store_prefix(wallet_id)
        + identity
        + bytes([0x01 if pending else 0x00])
        + len(payload).to_bytes(2, "big")
        + payload
    )


class TestWardStore(unittest.TestCase):
    """The offline store's slot layer: persistence, wallet scoping, and refusal to evict."""

    def setUp(self):
        config.init()
        config.wipe()
        config.unlock("", None)

    def reboot(self):
        """As close to a power cycle as a unit test gets.

        `config.init()` alone is not enough: it re-reads flash but leaves storage LOCKED, and
        every record here is protected -- so a reader would see None and a writer would fail,
        for reasons that have nothing to do with persistence. Unlocking is what a real boot
        does too, when the user enters their PIN.
        """
        config.init()
        self.assertTrue(config.unlock("", None))

    def test_a_record_survives_a_reboot_byte_for_byte(self):
        """The whole point of flash over the session cache.

        `reboot()` re-reads the emulated flash and unlocks it, which is as close to a power
        cycle as a unit test gets. A store that lost entries here would be a store that only
        ever served the session that wrote them -- which is exactly the state this feature
        exists to leave.
        """
        rec = _record(_WALLET_A, _ID_1, b"bc1qexampleaddress")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec))

        self.reboot()

        self.assertEqual(ward_store.store_get(_WALLET_A, _full(_ID_1)), rec)

    def test_wallets_cannot_see_each_others_records(self):
        """A passphrase switch must not surface another wallet's entry at the same path.

        The same entry_key under two wallet_ids is two unrelated records. Looking up by
        entry_key alone would find whichever was written last, and the user would be shown one
        hidden wallet's data while believing they were in another.
        """
        rec_a = _record(_WALLET_A, _ID_1, b"wallet-a-value")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec_a))

        self.assertIsNone(ward_store.store_get(_WALLET_B, _full(_ID_1)))

        rec_b = _record(_WALLET_B, _ID_1, b"wallet-b-value")
        self.assertTrue(ward_store.store_put(_WALLET_B, ward_store.STORE_VERSION, _ID_1, rec_b))

        self.assertEqual(ward_store.store_get(_WALLET_A, _full(_ID_1)), rec_a)
        self.assertEqual(ward_store.store_get(_WALLET_B, _full(_ID_1)), rec_b)

    def test_both_wallets_survive_switching_across_reboots(self):
        """Write A, cycle, write B, cycle, and both are still there.

        Separate from the isolation test above because it catches a different bug: slot reuse.
        A `_find` that matched too loosely, or an allocator that handed out an occupied slot,
        would pass isolation within one session and still lose a wallet across a switch.
        """
        rec_a = _record(_WALLET_A, _ID_1, b"a")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec_a))
        self.reboot()

        rec_b = _record(_WALLET_B, _ID_2, b"b")
        self.assertTrue(ward_store.store_put(_WALLET_B, ward_store.STORE_VERSION, _ID_2, rec_b))
        self.reboot()

        self.assertEqual(ward_store.store_get(_WALLET_A, _full(_ID_1)), rec_a)
        self.assertEqual(ward_store.store_get(_WALLET_B, _full(_ID_2)), rec_b)

    def test_a_full_store_refuses_and_keeps_everything(self):
        """Full means full: the write fails and not one existing record moves.

        The assertion that matters is the second loop, not the refusal. A store that reported
        failure while having already evicted something would pass a test that only checked the
        return value, and the user would discover the loss later with nothing to explain it.
        """
        keys = [_identity(bytes([i]) * 4) for i in range(ward_store.MAX_STORE_ENTRIES)]
        records = {}
        for k in keys:
            rec = _record(_WALLET_A, k, b"payload")
            records[k] = rec
            self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, k, rec))

        overflow_key = _identity(b"\xff" * 4)
        self.assertFalse(
            ward_store.store_put(
                _WALLET_A,
                ward_store.STORE_VERSION,
                overflow_key,
                _record(_WALLET_A, overflow_key),
            )
        )
        self.assertIsNone(ward_store.store_get(_WALLET_A, _full(overflow_key)))

        for k in keys:
            self.assertEqual(ward_store.store_get(_WALLET_A, _full(k)), records[k])

    def test_a_full_store_still_accepts_a_replacement(self):
        """Being full blocks NEW records, not updates to ones already held.

        Otherwise a full store would freeze every entry in it: a user could neither replace a
        pinned value nor let a queued write be marked as handed over without first erasing
        something unrelated.
        """
        keys = [_identity(bytes([i]) * 4) for i in range(ward_store.MAX_STORE_ENTRIES)]
        for k in keys:
            self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, k, _record(_WALLET_A, k)))

        replacement = _record(_WALLET_A, keys[0], b"new-payload")
        self.assertTrue(
            ward_store.store_put(
                _WALLET_A, ward_store.STORE_VERSION, keys[0], replacement
            )
        )
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(keys[0])), replacement)

    def test_an_unknown_version_is_still_findable_and_erasable(self):
        """The frozen-prefix contract, which is what makes "report, do not wipe" possible.

        A record written by a newer firmware cannot be parsed here, and the erase rule forbids
        deleting what the user has not agreed to lose. So this build must still be able to FIND
        it -- to name it on a confirmation screen -- and to remove it once they do. If the
        prefix were not frozen, the only options left would be to strand the record forever or
        to wipe blind.
        """
        rec = bytearray(_record(_WALLET_A, _ID_1))
        rec[0] = 0x7F  # a version this build knows nothing about
        rec = bytes(rec)

        # store_put checks the header names the right wallet and key, so write it directly.
        from storage import common

        common.set(common.APP_WARD, 0x40, rec)

        self.assertEqual(ward_store.store_find(_WALLET_A, _full(_ID_1)), 0)
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(_ID_1)), rec)

        ward_store.store_delete(_WALLET_A, _full(_ID_1))
        self.assertIsNone(ward_store.store_get(_WALLET_A, _full(_ID_1)))

    def test_deleting_frees_the_slot_and_leaves_neighbours_alone(self):
        rec1 = _record(_WALLET_A, _ID_1, b"one")
        rec2 = _record(_WALLET_A, _ID_2, b"two")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec1))
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_2, rec2))

        ward_store.store_delete(_WALLET_A, _full(_ID_1))

        self.assertIsNone(ward_store.store_get(_WALLET_A, _full(_ID_1)))
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(_ID_2)), rec2)

        key3 = _identity(b"addr3")
        rec3 = _record(_WALLET_A, key3, b"three")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, key3, rec3))
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(key3)), rec3)

    def test_deleting_something_that_is_not_there_is_a_no_op(self):
        ward_store.store_delete(_WALLET_A, _full(_ID_1))
        self.assertIsNone(ward_store.store_get(_WALLET_A, _full(_ID_1)))

    def test_listing_is_scoped_to_one_wallet(self):
        """Enumeration is where a missing filter leaks another hidden wallet's existence."""
        rec_a = _record(_WALLET_A, _ID_1, b"a")
        rec_b = _record(_WALLET_B, _ID_2, b"b")
        ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec_a)
        ward_store.store_put(_WALLET_B, ward_store.STORE_VERSION, _ID_2, rec_b)

        # (slot, record) pairs: a caller that wants to change a record's flags needs the handle
        self.assertEqual(ward_store.store_list(_WALLET_A), [(0, rec_a)])
        self.assertEqual(ward_store.store_list(_WALLET_B), [(1, rec_b)])

    def test_a_replacement_keeps_the_slot_it_had(self):
        """A record is addressed by its slot, and a rewrite must not move it.

        Below us norcow appends the new bytes and marks the old entry deleted -- a longer value cannot
        be patched over a shorter one -- so the record's PHYSICAL position does change. None of that
        may reach the store: `store_list` walks slots in order and `next_unsent` follows it, so a
        record that moved would change the order queued changes are published in.
        """
        for i, ident in enumerate((_ID_1, _ID_2, _identity(b"addr3"))):
            self.assertTrue(
                ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, ident, _record(_WALLET_A, ident, b"v"))
            )
            self.assertEqual(ward_store.store_find(_WALLET_A, _full(ident)), i)

        # the middle one, twice: longer, then shorter again
        longer = _record(_WALLET_A, _ID_2, b"v" * 400)
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_2, longer))
        self.assertEqual(ward_store.store_find(_WALLET_A, _full(_ID_2)), 1)

        shorter = _record(_WALLET_A, _ID_2, b"v")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_2, shorter))
        self.assertEqual(ward_store.store_find(_WALLET_A, _full(_ID_2)), 1)

        # and enumeration order is unchanged
        self.assertEqual(
            ward_store.store_list(_WALLET_A),
            [
                (0, _record(_WALLET_A, _ID_1, b"v")),
                (1, shorter),
                (2, _record(_WALLET_A, _identity(b"addr3"), b"v")),
            ],
        )

    def test_both_forms_live_in_one_pool_and_are_found_by_their_own_name(self):
        """A compact record is a different VERSION with a different key, in the same slot pool.

        The lookup takes candidates rather than one key, so a caller that knows an entry's identity
        finds it whichever form it was stored in -- and a record stored under one name is not found
        under the other, which is what keeps two forms of the same entry from ever coexisting.
        """
        entry_hash = b"\xab" * 16  # stands in for keys.wallet_entry, opaque to this layer
        compact = (
            ward_store.store_prefix(_WALLET_A, ward_store.STORE_VERSION_COMPACT)
            + entry_hash  # no wallet tag: the hash already commits to wallet_id
            + b"\x01"
            + len(b"v").to_bytes(2, "big")
            + b"v"
        )
        full = _record(_WALLET_A, _ID_1, b"w")

        self.assertTrue(
            ward_store.store_put(
                _WALLET_A, ward_store.STORE_VERSION_COMPACT, entry_hash, compact
            )
        )
        self.assertTrue(
            ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, full)
        )

        both = [
            (ward_store.STORE_VERSION, _ID_1),
            (ward_store.STORE_VERSION_COMPACT, entry_hash),
        ]
        self.assertEqual(ward_store.store_get(_WALLET_A, both), compact)  # slot order
        self.assertEqual(
            ward_store.store_get(_WALLET_A, [(ward_store.STORE_VERSION, _ID_1)]), full
        )
        self.assertIsNone(
            ward_store.store_get(
                _WALLET_A, [(ward_store.STORE_VERSION, entry_hash)]
            )  # right bytes, wrong form
        )

        # ENUMERATION SEES ONLY THE FULL FORM: a compact record carries nothing that says whose it
        # is, which is exactly the seven bytes it saves. Neither is mistaken for unreadable.
        self.assertEqual(len(ward_store.store_list(_WALLET_A)), 1)
        self.assertIsNone(ward_store.store_find_unreadable(_WALLET_A))

    def test_a_record_may_change_form_in_place(self):
        """Rewriting an entry compactly must TAKE OVER its slot, not leave the old form behind.

        Two records for one entry under different names would both be findable, and which one a
        lookup returned would depend on slot order -- so a value the user replaced could come back.
        """
        entry_hash = b"\xcd" * 16
        full = _record(_WALLET_A, _ID_1, b"first")
        self.assertTrue(
            ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, full)
        )

        compact = (
            ward_store.store_prefix(_WALLET_A, ward_store.STORE_VERSION_COMPACT)
            + entry_hash
            + b"\x01"
            + len(b"second").to_bytes(2, "big")
            + b"second"
        )
        self.assertTrue(
            ward_store.store_put(
                _WALLET_A,
                ward_store.STORE_VERSION_COMPACT,
                entry_hash,
                compact,
                replaces=_ID_1,
            )
        )

        self.assertEqual(len(ward_store.store_list(_WALLET_A)), 0)  # compact: not enumerable
        self.assertIsNone(
            ward_store.store_get(_WALLET_A, [(ward_store.STORE_VERSION, _ID_1)])
        )
        self.assertEqual(
            ward_store.store_get(
                _WALLET_A, [(ward_store.STORE_VERSION_COMPACT, entry_hash)]
            ),
            compact,
        )

    def test_records_never_collide_with_root_slots(self):
        """The two key ranges are disjoint, and a root write must not disturb a record.

        Both records and roots begin with a 16-byte wallet_id, so an overlapping range would
        let one be read as the other -- a wallet_id match at the same offset, which is the kind
        of confusion that looks like ordinary operation rather than an error.
        """
        ward_store.set_root(_WALLET_A, b"\x01" * 32, 5)
        rec = _record(_WALLET_A, _ID_1, b"kept")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec))

        ward_store.set_root(_WALLET_A, b"\x02" * 32, 6)

        self.assertEqual(ward_store.store_get(_WALLET_A, _full(_ID_1)), rec)
        self.assertEqual(ward_store.get_root(_WALLET_A), b"\x02" * 32)
        self.assertEqual(ward_store.get_counter(_WALLET_A), 6)

    def test_a_record_header_must_name_its_own_wallet_and_key(self):
        """A mismatched header is a programming error, not a recoverable state.

        `store_find` trusts the header, so a record stored under a key its header does not name
        would be unfindable -- present in flash, invisible to every lookup, and occupying a slot
        the user cannot free.
        """
        rec = _record(_WALLET_A, _ID_1)
        with self.assertRaises(ValueError):
            ward_store.store_put(_WALLET_B, ward_store.STORE_VERSION, _ID_1, rec)
        with self.assertRaises(ValueError):
            ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_2, rec)

    def test_a_compact_record_is_scoped_by_its_name_alone(self):
        """No wallet tag, so the NAME has to do the scoping -- and it does, being a hash over
        wallet_id.

        Two wallets asking about the same entry compute different names, so neither can reach the
        other's record. Asserted with the hashes standing in for `keys.wallet_entry`, since this layer
        only ever sees them as opaque bytes.
        """
        mine, theirs = b"\x11" * 16, b"\x22" * 16
        rec = (
            ward_store.store_prefix(_WALLET_A, ward_store.STORE_VERSION_COMPACT)
            + mine
            + b"\x01"
            + (1).to_bytes(2, "big")
            + b"v"
        )
        self.assertTrue(
            ward_store.store_put(
                _WALLET_A, ward_store.STORE_VERSION_COMPACT, mine, rec
            )
        )

        # the other wallet's name for its own entry finds nothing...
        self.assertIsNone(
            ward_store.store_get(
                _WALLET_B, [(ward_store.STORE_VERSION_COMPACT, theirs)]
            )
        )
        # ...and the record is only 25 bytes: version, name, flags, len16, value
        self.assertEqual(len(rec), 1 + 16 + 1 + 2 + 1)

    def test_the_stored_wallet_tag_is_truncated_and_that_is_deliberate(self):
        """Records key on the FIRST 7 BYTES of wallet_id; root slots keep all 16.

        So two wallets whose ids agree on those 7 bytes would share records -- which is the trade the
        truncation makes, at ~4e-16 across 8 wallets, for a tag that only has to tell one wallet's
        records from another's on this device. Asserted rather than left implicit: a reader who finds
        this surprising should find it DOCUMENTED, not discover it from a mixed-up label.
        """
        twin = _WALLET_A[:7] + b"\xff" * 9  # differs from _WALLET_A only past the truncation
        self.assertNotEqual(twin, _WALLET_A)

        rec = _record(_WALLET_A, _ID_1, b"shared")
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, _ID_1, rec))

        # ...and the twin finds it, because the store never saw the bytes that differ
        self.assertEqual(ward_store.store_get(twin, _full(_ID_1)), rec)

        # The ROOT table is not truncated, so the same pair is two different wallets there.
        ward_store.set_root(_WALLET_A, b"\x01" * 32, 1)
        ward_store.set_root(twin, b"\x02" * 32, 2)
        self.assertEqual(ward_store.get_root(_WALLET_A), b"\x01" * 32)
        self.assertEqual(ward_store.get_root(twin), b"\x02" * 32)

    def test_the_byte_budget_binds_before_the_slots_do(self):
        """Big records run out of BYTES long before they run out of slots, and that is the point.

        20 x MAX_RECORD_LEN is 23 kB against a 32 kB norcow sector shared with everything else, so the
        store bounds what it holds rather than promising flash it does not have. The assertion that
        matters is the second half: a refusal must leave every existing record untouched.
        """
        big = b"p" * (ward_store.MAX_VALUE_LEN - 1)
        stored = {}
        for i in range(ward_store.MAX_STORE_ENTRIES):
            ident = _identity(bytes([i]) * 4)
            rec = _record(_WALLET_A, ident, big)
            if not ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, ident, rec):
                break
            stored[ident] = rec

        # it stopped on BYTES, with slots to spare
        self.assertLess(len(stored), ward_store.MAX_STORE_ENTRIES)
        self.assertLessEqual(ward_store.store_bytes_used(), ward_store.MAX_STORE_BYTES)

        for ident, rec in stored.items():
            self.assertEqual(ward_store.store_get(_WALLET_A, _full(ident)), rec)

    def test_a_replacement_pays_only_the_difference(self):
        """Otherwise a store near its budget could not shrink a record -- the write would be refused
        for space the record it replaces was already using."""
        big = b"p" * (ward_store.MAX_VALUE_LEN - 1)
        idents = []
        for i in range(ward_store.MAX_STORE_ENTRIES):
            ident = _identity(bytes([i]) * 4)
            if not ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, ident, _record(_WALLET_A, ident, big)):
                break
            idents.append(ident)

        # replacing one of them with the same size, at a budget that is already full
        again = _record(_WALLET_A, idents[0], b"q" * (ward_store.MAX_VALUE_LEN - 1))
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, idents[0], again))
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(idents[0])), again)

    def test_a_longer_replacement_is_refused_when_it_no_longer_fits(self):
        """The same identity again with a BIGGER record, at a budget that cannot take the difference.

        This is the write that can fail after having succeeded before: the slot is already the
        record's own, so nothing about slots refuses it -- only the bytes do. What must not happen is
        the store keeping the difference and losing the record: a refusal leaves the OLD value there,
        whole, because a caller that reports "full" while having already destroyed the entry is worse
        than one that never wrote.
        """
        big = b"p" * (ward_store.MAX_VALUE_LEN - 1)
        idents = []
        for i in range(ward_store.MAX_STORE_ENTRIES):
            ident = _identity(bytes([i]) * 4)
            if not ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, ident, _record(_WALLET_A, ident, big)):
                break
            idents.append(ident)

        # Fill the SLACK first. Five 1 kB records leave ~900 bytes free, and a 100-byte growth fits
        # into that quite legitimately -- the refusal being tested only happens at the brim.
        free = ward_store.MAX_STORE_BYTES - ward_store.store_bytes_used()
        filler = _identity(b"fill")
        overhead = len(_record(_WALLET_A, filler, b""))
        self.assertTrue(
            ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, filler, _record(_WALLET_A, filler, b"f" * (free - overhead - 10))
            )
        )
        self.assertLess(ward_store.MAX_STORE_BYTES - ward_store.store_bytes_used(), 100)

        first = idents[0]
        before = ward_store.store_get(_WALLET_A, _full(first))
        longer = _record(_WALLET_A, first, big + b"q" * 100)
        self.assertGreater(len(longer), len(before))

        self.assertFalse(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, first, longer))
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(first)), before)
        self.assertLessEqual(ward_store.store_bytes_used(), ward_store.MAX_STORE_BYTES)

        # ...and it succeeds once something else makes room
        ward_store.store_delete(_WALLET_A, _full(filler))
        self.assertTrue(ward_store.store_put(_WALLET_A, ward_store.STORE_VERSION, first, longer))
        self.assertEqual(ward_store.store_get(_WALLET_A, _full(first)), longer)

    def test_a_record_past_the_cap_is_refused(self):
        """The capacity guarantee is per RECORD, not per value.

        app_id and identifier have their own framing, so a long enough pair would blow the budget
        while every individual field looked legal -- and "20 records fit" would stop being true.
        """
        huge = _record(_WALLET_A, _identity(b"x" * 200), b"v")
        self.assertGreater(len(huge), ward_store.MAX_RECORD_LEN)
        with self.assertRaises(ValueError):
            ward_store.store_put(
                _WALLET_A, ward_store.STORE_VERSION, _identity(b"x" * 200), huge
            )

    def test_operands_are_checked(self):
        """The wallet_id is fixed-width; the identity is variable but never empty.

        An empty identity would match every record's header prefix-wise, so the first slot of the
        wallet would answer for any lookup -- which is the failure mode that matters here.
        """
        for bad in (b"", b"\x00" * 15, b"\x00" * 17):
            with self.assertRaises(ValueError):
                ward_store.store_find(bad, _ID_1)
        with self.assertRaises(ValueError):
            ward_store.store_find(_WALLET_A, b"")

    def test_an_unreadable_record_is_findable_by_slot_and_removable(self):
        """The other half of the frozen header: a record whose IDENTITY cannot be parsed.

        Version 2 moved the identity into the header, so a record written by a build that framed it
        differently cannot be matched by identity at all -- only the version byte and the wallet_id
        are dependable. Without a by-slot handle such a record would hold its slot forever, which is
        the state the erase rule forbids.
        """
        rec = bytearray(_record(_WALLET_A, _ID_1))
        rec[0] = 0x7F  # a version this build knows nothing about
        from storage import common

        common.set(common.APP_WARD, 0x40, bytes(rec))

        self.assertEqual(ward_store.store_find_unreadable(_WALLET_A), 0)
        # ...and not another wallet's problem
        self.assertIsNone(ward_store.store_find_unreadable(_WALLET_B))

        ward_store.store_delete_slot(0)
        self.assertIsNone(ward_store.store_find_unreadable(_WALLET_A))

    def test_a_root_write_reports_whether_it_landed(self):
        """A full root store REFUSES, and says so, rather than silently doing nothing.

        Refusing is the intended behaviour -- evicting would strip rollback protection from a
        wallet the user still has, with no way to notice. But the refusal has to be REPORTABLE,
        because the caller's next act is to mark the session online: a wallet that adopted a head
        it never stored is left at counter 0 with no root, and `verify_leaf_against_root` reads
        that as "nothing was ever written" and stops checking proofs. Silent refusal turned
        "protected by fewer slots" into "verified by nothing" for the ninth wallet.
        """
        for i in range(ward_store.MAX_WALLETS):
            wallet = bytes([i]) * 16
            self.assertTrue(ward_store.set_root(wallet, bytes([i + 1]) * 32, i + 1))

        # the ninth is refused...
        ninth = b"\xee" * 16
        self.assertFalse(ward_store.set_root(ninth, b"\x99" * 32, 99))
        self.assertIsNone(ward_store.get_root(ninth))
        self.assertEqual(ward_store.get_counter(ninth), 0)

        # ...and no occupant was disturbed by the attempt
        for i in range(ward_store.MAX_WALLETS):
            wallet = bytes([i]) * 16
            self.assertEqual(ward_store.get_root(wallet), bytes([i + 1]) * 32)
            self.assertEqual(ward_store.get_counter(wallet), i + 1)

        # a wallet that already holds a slot keeps being updatable while the store is full
        first = bytes([0]) * 16
        self.assertTrue(ward_store.set_root(first, b"\x77" * 32, 77))
        self.assertEqual(ward_store.get_root(first), b"\x77" * 32)

    def test_a_claim_round_trips_and_is_scoped_to_its_wallet(self):
        """The journal's slot layer: persistence, wallet scoping, and refusal to overflow."""
        auth_a, commit_a = b"\xa1" * 32, b"\xa2" * 32
        rec = ward_store.claim_encode(_WALLET_A, 3, 42, auth_a, commit_a)
        self.assertTrue(ward_store.claim_put(rec))

        i = ward_store.claim_find(_WALLET_A, 3)
        self.assertIsNotNone(i)
        self.assertEqual(
            ward_store.claim_parse(ward_store.claim_read(i)),
            (_WALLET_A, 3, 42, auth_a, commit_a),
        )

        # ANOTHER WALLET'S CLAIM IS NOT THIS WALLET'S, even at the same record slot. This is the
        # scoping that stops one wallet's reconciliation rewriting another's queued records.
        self.assertIsNone(ward_store.claim_find(_WALLET_B, 3))
        self.assertEqual([r for _i, r in ward_store.claim_list(_WALLET_B)], [])
        self.assertEqual([r for _i, r in ward_store.claim_list(_WALLET_A)], [rec])

        # re-filing the same (wallet, slot) REPLACES rather than accumulating: a wallet has at
        # most one outstanding claim per record, which is what makes MAX_CLAIMS enough
        again = ward_store.claim_encode(_WALLET_A, 3, 43, auth_a, commit_a)
        self.assertTrue(ward_store.claim_put(again))
        self.assertEqual(len(ward_store.claim_list(_WALLET_A)), 1)
        self.assertEqual(ward_store.claim_parse(ward_store.claim_read(i))[2], 43)

        ward_store.claim_delete(i)
        self.assertIsNone(ward_store.claim_find(_WALLET_A, 3))
        self.assertIsNone(ward_store.claim_read(i))

    def test_claims_survive_a_reboot_and_cover_every_record_slot(self):
        """Claims are in flash BECAUSE the session is where they used to be lost.

        A claim outlives the channel closing, the cache being evicted and the device losing
        power -- the three events a lost publication recovery has to survive.

        And there is one slot per RECORD, so a host that drains the queue by flushing repeatedly
        and reconciling once at the end never runs out. The cache field this replaces held eight
        and silently dropped the rest, stranding every record past the eighth.
        """
        self.assertEqual(ward_store.MAX_CLAIMS, ward_store.MAX_STORE_ENTRIES)

        for i in range(ward_store.MAX_CLAIMS):
            self.assertTrue(
                ward_store.claim_put(
                    ward_store.claim_encode(
                        _WALLET_A, i, i, bytes([i]) * 32, bytes([i]) * 32
                    )
                )
            )
        self.assertEqual(len(ward_store.claim_list(_WALLET_A)), ward_store.MAX_CLAIMS)

        # ...and once genuinely full, a further claim is REPORTED rather than dropped: the
        # caller's next act is to mark a record offered, and a change offered with no claim to
        # settle it is stranded, invisible to `next_unsent` and `count_unsent`.
        self.assertFalse(
            ward_store.claim_put(
                ward_store.claim_encode(_WALLET_B, 0, 1, b"\x01" * 32, b"\x02" * 32)
            )
        )
        self.assertIsNone(ward_store.claim_find(_WALLET_B, 0))

        self.reboot()

        for i in range(ward_store.MAX_CLAIMS):
            j = ward_store.claim_find(_WALLET_A, i)
            self.assertIsNotNone(j)
            self.assertEqual(ward_store.claim_parse(ward_store.claim_read(j))[2], i)

    def test_a_claim_rejects_operands_of_the_wrong_width(self):
        """A short claim would parse into plausible-looking garbage, so it never gets written."""
        with self.assertRaises(ValueError):
            ward_store.claim_encode(b"\x00" * 15, 0, 0, b"\x01" * 32, b"\x02" * 32)
        with self.assertRaises(ValueError):
            ward_store.claim_encode(_WALLET_A, 0, 0, b"\x01" * 31, b"\x02" * 32)
        with self.assertRaises(ValueError):
            ward_store.claim_encode(_WALLET_A, 0, 0, b"\x01" * 32, b"\x02" * 33)
        # ...and a slot that no record could occupy is refused too
        with self.assertRaises(ValueError):
            ward_store.claim_encode(
                _WALLET_A, ward_store.MAX_STORE_ENTRIES, 0, b"\x01" * 32, b"\x02" * 32
            )
        with self.assertRaises(ValueError):
            ward_store.claim_parse(b"\x00" * (ward_store.CLAIM_LEN - 1))


if __name__ == "__main__":
    unittest.main()
