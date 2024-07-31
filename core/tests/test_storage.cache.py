from common import *  # isort:skip # noqa: F403

from mock_storage import mock_storage

from storage import cache, cache_codec, cache_thp
from trezor.messages import Initialize
from trezor.messages import EndSession

from apps.base import handle_EndSession, handle_Initialize

KEY = 0

if utils.USE_THP:
    _PROTOCOL_CACHE = cache_thp
else:
    _PROTOCOL_CACHE = cache_codec

    def is_session_started() -> bool:
        return cache_codec.get_active_session() is not None

    def get_active_session():
        return cache_codec.get_active_session()


class TestStorageCache(
    unittest.TestCase
):  # noqa: F405 # pyright: ignore[reportUndefinedVariable]
    def setUp(self):
        cache.clear_all()

    if not utils.USE_THP:

        def __init__(self):
            # Context is needed to test decorators and handleInitialize
            # It allows access to codec cache from different parts of the code
            from trezor.wire import context

            context.CURRENT_CONTEXT = context.CodecContext(None, bytearray(64))
            super().__init__()

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
            for i in range(_PROTOCOL_CACHE._MAX_SESSIONS_COUNT):
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

            cache_codec.clear_all()
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

            cache_codec.clear_all()
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
