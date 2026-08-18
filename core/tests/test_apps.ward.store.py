# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import ward as ward_store
from trezor import config

_WALLET_A = b"\xa0" * 16
_WALLET_B = b"\xb0" * 16

_KEY_1 = b"\x11" * 32
_KEY_2 = b"\x22" * 32


def _record(wallet_id, entry_key, payload=b"value", counter=7, pending=False):
    """A minimal well-formed record, built the way `offline_store.encode_record` builds one.

    Deliberately assembled HERE rather than imported: this file is about the storage layer's
    slot behaviour, and importing the encoder would make a change to the record format able to
    break these tests for reasons that have nothing to do with what they assert.
    """
    return (
        ward_store.store_prefix(wallet_id, entry_key)
        + bytes([0x01 if pending else 0x00])
        + counter.to_bytes(4, "big")
        + b"\x00"  # device_id
        + bytes([7])
        + b"address"
        + bytes([3])
        + b"btc"
        + len(b"id").to_bytes(2, "big")
        + b"id"
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
        rec = _record(_WALLET_A, _KEY_1, b"bc1qexampleaddress")
        self.assertTrue(ward_store.store_put(_WALLET_A, _KEY_1, rec))

        self.reboot()

        self.assertEqual(ward_store.store_get(_WALLET_A, _KEY_1), rec)

    def test_wallets_cannot_see_each_others_records(self):
        """A passphrase switch must not surface another wallet's entry at the same path.

        The same entry_key under two wallet_ids is two unrelated records. Looking up by
        entry_key alone would find whichever was written last, and the user would be shown one
        hidden wallet's data while believing they were in another.
        """
        rec_a = _record(_WALLET_A, _KEY_1, b"wallet-a-value")
        self.assertTrue(ward_store.store_put(_WALLET_A, _KEY_1, rec_a))

        self.assertIsNone(ward_store.store_get(_WALLET_B, _KEY_1))

        rec_b = _record(_WALLET_B, _KEY_1, b"wallet-b-value")
        self.assertTrue(ward_store.store_put(_WALLET_B, _KEY_1, rec_b))

        self.assertEqual(ward_store.store_get(_WALLET_A, _KEY_1), rec_a)
        self.assertEqual(ward_store.store_get(_WALLET_B, _KEY_1), rec_b)

    def test_both_wallets_survive_switching_across_reboots(self):
        """Write A, cycle, write B, cycle, and both are still there.

        Separate from the isolation test above because it catches a different bug: slot reuse.
        A `_find` that matched too loosely, or an allocator that handed out an occupied slot,
        would pass isolation within one session and still lose a wallet across a switch.
        """
        rec_a = _record(_WALLET_A, _KEY_1, b"a")
        self.assertTrue(ward_store.store_put(_WALLET_A, _KEY_1, rec_a))
        self.reboot()

        rec_b = _record(_WALLET_B, _KEY_2, b"b")
        self.assertTrue(ward_store.store_put(_WALLET_B, _KEY_2, rec_b))
        self.reboot()

        self.assertEqual(ward_store.store_get(_WALLET_A, _KEY_1), rec_a)
        self.assertEqual(ward_store.store_get(_WALLET_B, _KEY_2), rec_b)

    def test_a_full_store_refuses_and_keeps_everything(self):
        """Full means full: the write fails and not one existing record moves.

        The assertion that matters is the second loop, not the refusal. A store that reported
        failure while having already evicted something would pass a test that only checked the
        return value, and the user would discover the loss later with nothing to explain it.
        """
        keys = [bytes([i]) * 32 for i in range(ward_store.MAX_STORE_ENTRIES)]
        records = {}
        for k in keys:
            rec = _record(_WALLET_A, k, b"payload-" + k[:1])
            records[k] = rec
            self.assertTrue(ward_store.store_put(_WALLET_A, k, rec))

        overflow_key = b"\xff" * 32
        self.assertFalse(
            ward_store.store_put(
                _WALLET_A, overflow_key, _record(_WALLET_A, overflow_key)
            )
        )
        self.assertIsNone(ward_store.store_get(_WALLET_A, overflow_key))

        for k in keys:
            self.assertEqual(ward_store.store_get(_WALLET_A, k), records[k])

    def test_a_full_store_still_accepts_a_replacement(self):
        """Being full blocks NEW records, not updates to ones already held.

        Otherwise a full store would freeze every entry in it: a user could neither refresh a
        pinned value nor let a queued write advance its counter without first erasing something
        unrelated.
        """
        keys = [bytes([i]) * 32 for i in range(ward_store.MAX_STORE_ENTRIES)]
        for k in keys:
            self.assertTrue(ward_store.store_put(_WALLET_A, k, _record(_WALLET_A, k)))

        replacement = _record(_WALLET_A, keys[0], b"new-payload")
        self.assertTrue(ward_store.store_put(_WALLET_A, keys[0], replacement))
        self.assertEqual(ward_store.store_get(_WALLET_A, keys[0]), replacement)

    def test_an_unknown_version_is_still_findable_and_erasable(self):
        """The frozen-prefix contract, which is what makes "report, do not wipe" possible.

        A record written by a newer firmware cannot be parsed here, and the erase rule forbids
        deleting what the user has not agreed to lose. So this build must still be able to FIND
        it -- to name it on a confirmation screen -- and to remove it once they do. If the
        prefix were not frozen, the only options left would be to strand the record forever or
        to wipe blind.
        """
        rec = bytearray(_record(_WALLET_A, _KEY_1))
        rec[0] = 0x7F  # a version this build knows nothing about
        rec = bytes(rec)

        # store_put checks the header names the right wallet and key, so write it directly.
        from storage import common

        common.set(common.APP_WARD, 0x40, rec)

        self.assertEqual(ward_store.store_find(_WALLET_A, _KEY_1), 0)
        self.assertEqual(ward_store.store_get(_WALLET_A, _KEY_1), rec)

        ward_store.store_delete(_WALLET_A, _KEY_1)
        self.assertIsNone(ward_store.store_get(_WALLET_A, _KEY_1))

    def test_deleting_frees_the_slot_and_leaves_neighbours_alone(self):
        rec1 = _record(_WALLET_A, _KEY_1, b"one")
        rec2 = _record(_WALLET_A, _KEY_2, b"two")
        self.assertTrue(ward_store.store_put(_WALLET_A, _KEY_1, rec1))
        self.assertTrue(ward_store.store_put(_WALLET_A, _KEY_2, rec2))

        ward_store.store_delete(_WALLET_A, _KEY_1)

        self.assertIsNone(ward_store.store_get(_WALLET_A, _KEY_1))
        self.assertEqual(ward_store.store_get(_WALLET_A, _KEY_2), rec2)

        key3 = b"\x33" * 32
        rec3 = _record(_WALLET_A, key3, b"three")
        self.assertTrue(ward_store.store_put(_WALLET_A, key3, rec3))
        self.assertEqual(ward_store.store_get(_WALLET_A, key3), rec3)

    def test_deleting_something_that_is_not_there_is_a_no_op(self):
        ward_store.store_delete(_WALLET_A, _KEY_1)
        self.assertIsNone(ward_store.store_get(_WALLET_A, _KEY_1))

    def test_listing_is_scoped_to_one_wallet(self):
        """Enumeration is where a missing filter leaks another hidden wallet's existence."""
        rec_a = _record(_WALLET_A, _KEY_1, b"a")
        rec_b = _record(_WALLET_B, _KEY_2, b"b")
        ward_store.store_put(_WALLET_A, _KEY_1, rec_a)
        ward_store.store_put(_WALLET_B, _KEY_2, rec_b)

        self.assertEqual(ward_store.store_list(_WALLET_A), [rec_a])
        self.assertEqual(ward_store.store_list(_WALLET_B), [rec_b])

    def test_records_never_collide_with_root_slots(self):
        """The two key ranges are disjoint, and a root write must not disturb a record.

        Both records and roots begin with a 16-byte wallet_id, so an overlapping range would
        let one be read as the other -- a wallet_id match at the same offset, which is the kind
        of confusion that looks like ordinary operation rather than an error.
        """
        ward_store.set_root(_WALLET_A, b"\x01" * 32, 5)
        rec = _record(_WALLET_A, _KEY_1, b"kept")
        self.assertTrue(ward_store.store_put(_WALLET_A, _KEY_1, rec))

        ward_store.set_root(_WALLET_A, b"\x02" * 32, 6)

        self.assertEqual(ward_store.store_get(_WALLET_A, _KEY_1), rec)
        self.assertEqual(ward_store.get_root(_WALLET_A), b"\x02" * 32)
        self.assertEqual(ward_store.get_counter(_WALLET_A), 6)

    def test_a_record_header_must_name_its_own_wallet_and_key(self):
        """A mismatched header is a programming error, not a recoverable state.

        `store_find` trusts the header, so a record stored under a key its header does not name
        would be unfindable -- present in flash, invisible to every lookup, and occupying a slot
        the user cannot free.
        """
        rec = _record(_WALLET_A, _KEY_1)
        with self.assertRaises(ValueError):
            ward_store.store_put(_WALLET_B, _KEY_1, rec)
        with self.assertRaises(ValueError):
            ward_store.store_put(_WALLET_A, _KEY_2, rec)

    def test_fixed_width_operands_only(self):
        for bad in (b"", b"\x00" * 15, b"\x00" * 17):
            with self.assertRaises(ValueError):
                ward_store.store_find(bad, _KEY_1)
        for bad in (b"", b"\x00" * 31, b"\x00" * 33):
            with self.assertRaises(ValueError):
                ward_store.store_find(_WALLET_A, bad)


if __name__ == "__main__":
    unittest.main()
