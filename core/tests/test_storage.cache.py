# flake8: noqa: F403,F405
from common import *  # isort:skip


KEY = 0

if utils.USE_THP:
    import thp_common
    from mock_wire_interface import MockHID
    from storage import cache, cache_thp
    from trezor.wire.thp import ChannelState
    from trezor.wire.thp.session_context import SessionContext

    _PROTOCOL_CACHE = cache_thp

else:
    from mock_storage import mock_storage
    from storage import cache, cache_codec
    from trezor.messages import EndSession, Initialize

    from apps.base import handle_EndSession

    _PROTOCOL_CACHE = cache_codec

    def is_session_started() -> bool:
        return cache_codec.get_active_session() is not None

    def get_active_session():
        return cache_codec.get_active_session()


class TestStorageCache(unittest.TestCase):

    if utils.USE_THP:

        def setUpClass(self):
            if __debug__:
                thp_common.suppres_debug_log()
            super().__init__()

        def setUp(self):
            self.interface = MockHID(0xDEADBEEF)
            cache.clear_all()

        def test_new_channel_and_session(self):
            channel = thp_common.get_new_channel(self.interface)

            # Assert that channel is created without any sessions
            self.assertEqual(len(channel.sessions), 0)

            cid_1 = channel.channel_id
            session_cache_1 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x01"
            )
            session_1 = SessionContext(channel, session_cache_1)
            self.assertEqual(session_1.channel_id, cid_1)

            session_cache_2 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x02"
            )
            session_2 = SessionContext(channel, session_cache_2)
            self.assertEqual(session_2.channel_id, cid_1)
            self.assertEqual(session_1.channel_id, session_2.channel_id)
            self.assertNotEqual(session_1.session_id, session_2.session_id)

            channel_2 = thp_common.get_new_channel(self.interface)
            cid_2 = channel_2.channel_id
            self.assertNotEqual(cid_1, cid_2)

            session_cache_3 = cache_thp.create_or_replace_session(
                channel_2.channel_cache, b"\x01"
            )
            session_3 = SessionContext(channel_2, session_cache_3)
            self.assertEqual(session_3.channel_id, cid_2)

            # Sessions 1 and 3 should have different channel_id, but the same session_id
            self.assertNotEqual(session_1.channel_id, session_3.channel_id)
            self.assertEqual(session_1.session_id, session_3.session_id)

            self.assertEqual(cache_thp._SESSIONS[0], session_cache_1)
            self.assertNotEqual(cache_thp._SESSIONS[0], session_cache_2)
            self.assertEqual(cache_thp._SESSIONS[0].channel_id, session_1.channel_id)

            # Check that session data IS in cache for created sessions ONLY
            for i in range(3):
                self.assertNotEqual(cache_thp._SESSIONS[i].channel_id, b"")
                self.assertNotEqual(cache_thp._SESSIONS[i].session_id, b"")
                self.assertNotEqual(cache_thp._SESSIONS[i].last_usage, 0)
            for i in range(3, cache_thp._MAX_SESSIONS_COUNT):
                self.assertEqual(cache_thp._SESSIONS[i].channel_id, b"")
                self.assertEqual(cache_thp._SESSIONS[i].session_id, b"")
                self.assertEqual(cache_thp._SESSIONS[i].last_usage, 0)

            # Check that session data IS NOT in cache after cache.clear_all()
            cache.clear_all()
            for session in cache_thp._SESSIONS:
                self.assertEqual(session.channel_id, b"")
                self.assertEqual(session.session_id, b"")
                self.assertEqual(session.last_usage, 0)
                self.assertEqual(session.state, b"\x00")

        def test_channel_capacity_in_cache(self):
            self.assertTrue(cache_thp._MAX_CHANNELS_COUNT >= 3)
            channels = []
            for i in range(cache_thp._MAX_CHANNELS_COUNT):
                channels.append(thp_common.get_new_channel(self.interface))
            channel_ids = [channel.channel_cache.channel_id for channel in channels]

            # Assert that each channel_id is unique and that cache and list of channels
            # have the same "channels" on the same indexes
            for i in range(len(channel_ids)):
                self.assertEqual(cache_thp._CHANNELS[i].channel_id, channel_ids[i])
                for j in range(i + 1, len(channel_ids)):
                    self.assertNotEqual(channel_ids[i], channel_ids[j])

            # Create a new channel that is over the capacity
            new_channel = thp_common.get_new_channel(self.interface)
            for c in channels:
                self.assertNotEqual(c.channel_id, new_channel.channel_id)

            # Test that the oldest (least used) channel was replaced (_CHANNELS[0])
            self.assertNotEqual(cache_thp._CHANNELS[0].channel_id, channel_ids[0])
            self.assertEqual(cache_thp._CHANNELS[0].channel_id, new_channel.channel_id)

            # Update the "last used" value of the second channel in cache (_CHANNELS[1]) and
            # assert that it is not replaced when creating a new channel
            cache_thp.update_channel_last_used(channel_ids[1])
            new_new_channel = thp_common.get_new_channel(self.interface)
            self.assertEqual(cache_thp._CHANNELS[1].channel_id, channel_ids[1])

            # Assert that it was in fact the _CHANNEL[2] that was replaced
            self.assertNotEqual(cache_thp._CHANNELS[2].channel_id, channel_ids[2])
            self.assertEqual(
                cache_thp._CHANNELS[2].channel_id, new_new_channel.channel_id
            )

        def test_session_capacity_in_cache(self):
            self.assertTrue(cache_thp._MAX_SESSIONS_COUNT >= 4)
            channel_cache_A = thp_common.get_new_channel(self.interface).channel_cache
            channel_cache_B = thp_common.get_new_channel(self.interface).channel_cache

            sesions_A = []
            cid = []
            sid = []
            for i in range(3):
                sesions_A.append(
                    cache_thp.create_or_replace_session(
                        channel_cache_A, (i + 1).to_bytes(1, "big")
                    )
                )
                cid.append(sesions_A[i].channel_id)
                sid.append(sesions_A[i].session_id)

            sessions_B = []
            for i in range(cache_thp._MAX_SESSIONS_COUNT - 3):
                sessions_B.append(
                    cache_thp.create_or_replace_session(
                        channel_cache_B, (i + 10).to_bytes(1, "big")
                    )
                )

            for i in range(3):
                self.assertEqual(sesions_A[i], cache_thp._SESSIONS[i])
                self.assertEqual(cid[i], cache_thp._SESSIONS[i].channel_id)
                self.assertEqual(sid[i], cache_thp._SESSIONS[i].session_id)
            for i in range(3, cache_thp._MAX_SESSIONS_COUNT):
                self.assertEqual(sessions_B[i - 3], cache_thp._SESSIONS[i])

            # Assert that new session replaces the oldest (least used) one (_SESSOIONS[0])
            new_session = cache_thp.create_or_replace_session(channel_cache_B, b"\xab")
            self.assertEqual(new_session, cache_thp._SESSIONS[0])
            self.assertNotEqual(new_session.channel_id, cid[0])
            self.assertNotEqual(new_session.session_id, sid[0])

            # Assert that updating "last used" for session on channel A increases also
            # the "last usage" of channel A.
            self.assertTrue(channel_cache_A.last_usage < channel_cache_B.last_usage)
            cache_thp.update_session_last_used(
                channel_cache_A.channel_id, sesions_A[1].session_id
            )
            self.assertTrue(channel_cache_A.last_usage > channel_cache_B.last_usage)

            new_new_session = cache_thp.create_or_replace_session(
                channel_cache_B, b"\xaa"
            )

            # Assert that creating a new session on channel B shifts the "last usage" again
            # and that _SESSIONS[1] was not replaced, but that _SESSIONS[2] was replaced
            self.assertTrue(channel_cache_A.last_usage < channel_cache_B.last_usage)
            self.assertEqual(sesions_A[1], cache_thp._SESSIONS[1])
            self.assertNotEqual(sesions_A[2], cache_thp._SESSIONS[2])
            self.assertEqual(new_new_session, cache_thp._SESSIONS[2])

        def test_clear(self):
            channel_A = thp_common.get_new_channel(self.interface)
            channel_B = thp_common.get_new_channel(self.interface)
            cid_A = channel_A.channel_id
            cid_B = channel_B.channel_id
            sessions = []

            for i in range(3):
                sessions.append(
                    cache_thp.create_or_replace_session(
                        channel_A.channel_cache, (i + 1).to_bytes(1, "big")
                    )
                )
                sessions.append(
                    cache_thp.create_or_replace_session(
                        channel_B.channel_cache, (i + 10).to_bytes(1, "big")
                    )
                )

                self.assertEqual(cache_thp._SESSIONS[2 * i].channel_id, cid_A)
                self.assertNotEqual(cache_thp._SESSIONS[2 * i].last_usage, 0)

                self.assertEqual(cache_thp._SESSIONS[2 * i + 1].channel_id, cid_B)
                self.assertNotEqual(cache_thp._SESSIONS[2 * i + 1].last_usage, 0)

            # Assert that clearing of channel A works
            self.assertNotEqual(channel_A.channel_cache.channel_id, b"")
            self.assertNotEqual(channel_A.channel_cache.last_usage, 0)
            self.assertEqual(channel_A.get_channel_state(), ChannelState.TH1)

            channel_A.clear()

            self.assertEqual(channel_A.channel_cache.channel_id, b"")
            self.assertEqual(channel_A.channel_cache.last_usage, 0)
            self.assertEqual(channel_A.get_channel_state(), ChannelState.UNALLOCATED)

            # Assert that clearing channel A also cleared all its sessions
            for i in range(3):
                self.assertEqual(cache_thp._SESSIONS[2 * i].last_usage, 0)
                self.assertEqual(cache_thp._SESSIONS[2 * i].channel_id, b"")

                self.assertNotEqual(cache_thp._SESSIONS[2 * i + 1].last_usage, 0)
                self.assertEqual(cache_thp._SESSIONS[2 * i + 1].channel_id, cid_B)

            cache.clear_all()
            for session in cache_thp._SESSIONS:
                self.assertEqual(session.last_usage, 0)
                self.assertEqual(session.channel_id, b"")
            for channel in cache_thp._CHANNELS:
                self.assertEqual(channel.channel_id, b"")
                self.assertEqual(channel.last_usage, 0)
                self.assertEqual(
                    cache_thp._get_channel_state(channel), ChannelState.UNALLOCATED
                )

        def test_get_set(self):
            channel = thp_common.get_new_channel(self.interface)

            session_1 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x01"
            )
            session_1.set(KEY, b"hello")
            self.assertEqual(session_1.get(KEY), b"hello")

            session_2 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x02"
            )
            session_2.set(KEY, b"world")
            self.assertEqual(session_2.get(KEY), b"world")

            self.assertEqual(session_1.get(KEY), b"hello")

            cache.clear_all()
            self.assertIsNone(session_1.get(KEY))
            self.assertIsNone(session_2.get(KEY))

        def test_get_set_int(self):
            channel = thp_common.get_new_channel(self.interface)

            session_1 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x01"
            )
            session_1.set_int(KEY, 1234)

            self.assertEqual(session_1.get_int(KEY), 1234)

            session_2 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x02"
            )
            session_2.set_int(KEY, 5678)
            self.assertEqual(session_2.get_int(KEY), 5678)

            self.assertEqual(session_1.get_int(KEY), 1234)

            cache.clear_all()
            self.assertIsNone(session_1.get_int(KEY))
            self.assertIsNone(session_2.get_int(KEY))

        def test_get_set_bool(self):
            channel = thp_common.get_new_channel(self.interface)

            session_1 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x01"
            )
            with self.assertRaises(AssertionError):
                session_1.set_bool(KEY, True)

            # Change length of first session field to 0 so that the length check passes
            session_1.fields = (0,) + session_1.fields[1:]

            # with self.assertRaises(AssertionError) as e:
            session_1.set_bool(KEY, True)
            self.assertEqual(session_1.get_bool(KEY), True)

            session_2 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x02"
            )
            session_2.fields = session_2.fields = (0,) + session_2.fields[1:]
            session_2.set_bool(KEY, False)
            self.assertEqual(session_2.get_bool(KEY), False)

            self.assertEqual(session_1.get_bool(KEY), True)

            cache.clear_all()

            # Default value is False
            self.assertFalse(session_1.get_bool(KEY))
            self.assertFalse(session_2.get_bool(KEY))

        def test_delete(self):
            channel = thp_common.get_new_channel(self.interface)
            session_1 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x01"
            )

            self.assertIsNone(session_1.get(KEY))
            session_1.set(KEY, b"hello")
            self.assertEqual(session_1.get(KEY), b"hello")
            session_1.delete(KEY)
            self.assertIsNone(session_1.get(KEY))

            session_1.set(KEY, b"hello")
            session_2 = cache_thp.create_or_replace_session(
                channel.channel_cache, b"\x02"
            )

            self.assertIsNone(session_2.get(KEY))
            session_2.set(KEY, b"hello")
            self.assertEqual(session_2.get(KEY), b"hello")
            session_2.delete(KEY)
            self.assertIsNone(session_2.get(KEY))

            self.assertEqual(session_1.get(KEY), b"hello")

    else:

        def setUpClass(self):
            from trezor.wire import context
            from trezor.wire.codec.codec_context import CodecContext

            context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

        def tearDownClass(self):
            from trezor.wire import context

            context.CURRENT_CONTEXT = None

        def setUp(self):
            cache.clear_all()

        def test_start_session(self):
            session_id_a = cache_codec.start_session()
            self.assertIsNotNone(session_id_a)
            session_id_b = cache_codec.start_session()
            self.assertNotEqual(session_id_a, session_id_b)

            cache.clear_all()
            self.assertIsNone(get_active_session())
            for session in cache_codec._SESSIONS:
                self.assertEqual(session.session_id, b"")
                self.assertEqual(session.last_usage, 0)

        def test_end_session(self):
            session_id = cache_codec.start_session()
            self.assertTrue(is_session_started())
            get_active_session().set(KEY, b"A")
            cache_codec.end_current_session()
            self.assertFalse(is_session_started())
            self.assertIsNone(get_active_session())

            # ending an ended session should be a no-op
            cache_codec.end_current_session()
            self.assertFalse(is_session_started())

            session_id_a = cache_codec.start_session(session_id)
            # original session no longer exists
            self.assertNotEqual(session_id_a, session_id)
            # original session data no longer exists
            self.assertIsNone(get_active_session().get(KEY))

            # create a new session
            session_id_b = cache_codec.start_session()
            # switch back to original session
            session_id = cache_codec.start_session(session_id_a)
            self.assertEqual(session_id, session_id_a)
            # end original session
            cache_codec.end_current_session()
            # switch back to B
            session_id = cache_codec.start_session(session_id_b)
            self.assertEqual(session_id, session_id_b)

        def test_session_queue(self):
            session_id = cache_codec.start_session()
            self.assertEqual(cache_codec.start_session(session_id), session_id)
            get_active_session().set(KEY, b"A")
            for _ in range(_PROTOCOL_CACHE._MAX_SESSIONS_COUNT):
                cache_codec.start_session()
            self.assertNotEqual(cache_codec.start_session(session_id), session_id)
            self.assertIsNone(get_active_session().get(KEY))

        def test_get_set(self):
            session_id1 = cache_codec.start_session()
            cache_codec.get_active_session().set(KEY, b"hello")
            self.assertEqual(cache_codec.get_active_session().get(KEY), b"hello")

            session_id2 = cache_codec.start_session()
            cache_codec.get_active_session().set(KEY, b"world")
            self.assertEqual(cache_codec.get_active_session().get(KEY), b"world")

            cache_codec.start_session(session_id2)
            self.assertEqual(cache_codec.get_active_session().get(KEY), b"world")
            cache_codec.start_session(session_id1)
            self.assertEqual(cache_codec.get_active_session().get(KEY), b"hello")

            cache.clear_all()
            self.assertIsNone(cache_codec.get_active_session())

        def test_get_set_int(self):
            session_id1 = cache_codec.start_session()
            get_active_session().set_int(KEY, 1234)
            self.assertEqual(get_active_session().get_int(KEY), 1234)

            session_id2 = cache_codec.start_session()
            get_active_session().set_int(KEY, 5678)
            self.assertEqual(get_active_session().get_int(KEY), 5678)

            cache_codec.start_session(session_id2)
            self.assertEqual(get_active_session().get_int(KEY), 5678)
            cache_codec.start_session(session_id1)
            self.assertEqual(get_active_session().get_int(KEY), 1234)

            cache.clear_all()
            self.assertIsNone(get_active_session())

        def test_delete(self):
            session_id1 = cache_codec.start_session()
            self.assertIsNone(get_active_session().get(KEY))
            get_active_session().set(KEY, b"hello")
            self.assertEqual(get_active_session().get(KEY), b"hello")
            get_active_session().delete(KEY)
            self.assertIsNone(get_active_session().get(KEY))

            get_active_session().set(KEY, b"hello")
            cache_codec.start_session()
            self.assertIsNone(get_active_session().get(KEY))
            get_active_session().set(KEY, b"hello")
            self.assertEqual(get_active_session().get(KEY), b"hello")
            get_active_session().delete(KEY)
            self.assertIsNone(get_active_session().get(KEY))

            cache_codec.start_session(session_id1)
            self.assertEqual(get_active_session().get(KEY), b"hello")

        def test_decorators(self):
            run_count = 0
            cache_codec.start_session()
            from apps.common.cache import stored

            @stored(KEY)
            def func():
                nonlocal run_count
                run_count += 1
                return b"foo"

            # cache is empty
            self.assertIsNone(get_active_session().get(KEY))
            self.assertEqual(run_count, 0)
            self.assertEqual(func(), b"foo")
            # function was run
            self.assertEqual(run_count, 1)
            self.assertEqual(get_active_session().get(KEY), b"foo")
            # function does not run again but returns cached value
            self.assertEqual(func(), b"foo")
            self.assertEqual(run_count, 1)

        def test_empty_value(self):
            cache_codec.start_session()

            self.assertIsNone(get_active_session().get(KEY))
            get_active_session().set(KEY, b"")
            self.assertEqual(get_active_session().get(KEY), b"")

            get_active_session().delete(KEY)
            run_count = 0

            from apps.common.cache import stored

            @stored(KEY)
            def func():
                nonlocal run_count
                run_count += 1
                return b""

            self.assertEqual(func(), b"")
            # function gets called once
            self.assertEqual(run_count, 1)
            self.assertEqual(func(), b"")
            # function is not called for a second time
            self.assertEqual(run_count, 1)

        @mock_storage
        def test_Initialize(self):
            from apps.base import handle_Initialize

            def call_Initialize(**kwargs):
                msg = Initialize(**kwargs)
                return await_result(handle_Initialize(msg))

            # calling Initialize without an ID allocates a new one
            session_id = cache_codec.start_session()
            features = call_Initialize()
            self.assertNotEqual(session_id, features.session_id)

            # calling Initialize with the current ID does not allocate a new one
            features = call_Initialize(session_id=session_id)
            self.assertEqual(session_id, features.session_id)

            # store "hello"
            get_active_session().set(KEY, b"hello")
            # check that it is cleared
            features = call_Initialize()
            session_id = features.session_id
            self.assertIsNone(get_active_session().get(KEY))
            # store "hello" again
            get_active_session().set(KEY, b"hello")
            self.assertEqual(get_active_session().get(KEY), b"hello")

            # supplying a different session ID starts a new session
            call_Initialize(session_id=b"A" * _PROTOCOL_CACHE.SESSION_ID_LENGTH)
            self.assertIsNone(get_active_session().get(KEY))

            # but resuming a session loads the previous one
            call_Initialize(session_id=session_id)
            self.assertEqual(get_active_session().get(KEY), b"hello")

        def test_EndSession(self):

            self.assertIsNone(get_active_session())
            cache_codec.start_session()
            self.assertTrue(is_session_started())
            self.assertIsNone(get_active_session().get(KEY))
            await_result(handle_EndSession(EndSession()))
            self.assertFalse(is_session_started())
            self.assertIsNone(cache_codec.get_active_session())


if __name__ == "__main__":
    unittest.main()
