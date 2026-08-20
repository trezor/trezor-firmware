# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils

if utils.USE_THP:
    from storage import cache_thp
    from trezor.wire.thp import SessionState

_CID_A = b"\x01\x02"
_CID_B = b"\x03\x04"
_SID = b"\x01"


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestWardServiceSession(unittest.TestCase):
    """The session slot that holds the WARD service's state.

    Two properties, and both exist because the slot is reached by a POINTER kept elsewhere rather
    than by the channel that happens to be talking: it has to still be there later, and it has to
    still be recognisable as the service's.
    """

    def setUp(self):
        cache_thp.clear_all()

    def test_it_is_recognisable_and_not_a_wallet_session(self):
        session = cache_thp.create_ward_service_session(_CID_A, _SID)
        self.assertTrue(cache_thp.is_ward_service_session(session))
        # NOT seedless either: that state means "no seed derived yet" and is one an ordinary
        # wallet session passes through, so sharing it would make the two indistinguishable.
        self.assertFalse(cache_thp.is_seedless_session(session))

    def test_an_ordinary_session_is_not_mistaken_for_it(self):
        ordinary = cache_thp.create_or_replace_session(_CID_A, _SID)
        self.assertFalse(cache_thp.is_ward_service_session(ordinary))

    def test_it_is_reachable_by_pointer_after_the_fact(self):
        """How the service is found: by (channel, session) recovered from a stored pointer, not by
        whichever channel is currently being served."""
        cache_thp.create_ward_service_session(_CID_A, _SID)
        found = cache_thp.get_allocated_session(_CID_A, _SID)
        self.assertIsNotNone(found)
        self.assertTrue(cache_thp.is_ward_service_session(found))

    def test_only_one_service_session_exists_at_a_time(self):
        """A second open replaces the first rather than accumulating.

        These slots are exempt from eviction, so letting them pile up would let a host consume
        every session slot on the device and leave the allocator with nothing it may reuse.
        """
        cache_thp.create_ward_service_session(_CID_A, _SID)
        cache_thp.create_ward_service_session(_CID_B, _SID)

        self.assertIsNone(cache_thp.get_allocated_session(_CID_A, _SID))
        self.assertIsNotNone(cache_thp.get_allocated_session(_CID_B, _SID))

        n = sum(
            1
            for i in range(20)
            if cache_thp.is_ward_service_session(cache_thp._SESSIONS[i])
        )
        self.assertEqual(n, 1)

    def test_it_survives_pressure_that_evicts_wallet_sessions(self):
        """THE POINT OF THE EXEMPTION. The service is idle by nature -- it is spoken to only when a
        workflow needs it -- so "least recently used" is exactly what it looks like. Evicting it
        would leave the stored pointer aimed at a slot that now belongs to somebody else.
        """
        cache_thp.create_ward_service_session(_CID_A, _SID)

        # fill and overfill the table with ordinary sessions
        for i in range(cache_thp._MAX_SESSIONS_COUNT + 5):
            cache_thp.create_or_replace_session(
                bytes([0x10 + (i >> 8), i & 0xFF]), b"\x02"
            )

        survived = cache_thp.get_allocated_session(_CID_A, _SID)
        self.assertIsNotNone(survived)
        self.assertTrue(cache_thp.is_ward_service_session(survived))


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestWardServiceSessionState(unittest.TestCase):
    def test_the_state_is_distinct(self):
        self.assertNotEqual(SessionState.WARD_SERVICE, SessionState.SEEDLESS)
        self.assertNotEqual(SessionState.WARD_SERVICE, SessionState.ALLOCATED)
        self.assertNotEqual(SessionState.WARD_SERVICE, SessionState.UNALLOCATED)


if __name__ == "__main__":
    unittest.main()
