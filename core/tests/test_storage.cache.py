# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock_storage import mock_storage
from storage import cache, cache_codec, cache_common
from trezor.messages import EndSession, Initialize
from trezor.wire import context
from trezor.wire.codec.codec_context import CodecContext

from apps.base import handle_EndSession, handle_Initialize
from apps.common.cache import stored, stored_async

KEY = 0


# Function moved from cache.py, as it was not used there
def is_session_started() -> bool:
    return cache_codec._active_session_idx is not None


class TestStorageCache(unittest.TestCase):

    def setUpClass(self):
        context.CURRENT_CONTEXT = CodecContext(None, bytearray(64))

    def tearDownClass(self):
        context.CURRENT_CONTEXT = None

    def setUp(self):
        cache.clear_all()

    def test_start_session(self):
        session_id_a = cache_codec.start_session()
        self.assertIsNotNone(session_id_a)
        session_id_b = cache_codec.start_session()
        self.assertNotEqual(session_id_a, session_id_b)

        cache.clear_all()
        with self.assertRaises(cache_common.InvalidSessionError):
            context.cache_set(KEY, "something")
        with self.assertRaises(cache_common.InvalidSessionError):
            context.cache_get(KEY)

    def test_end_session(self):
        session_id = cache_codec.start_session()
        self.assertTrue(is_session_started())
        context.cache_set(KEY, b"A")
        cache_codec.end_current_session()
        self.assertFalse(is_session_started())
        self.assertRaises(cache_common.InvalidSessionError, context.cache_get, KEY)

        # ending an ended session should be a no-op
        cache_codec.end_current_session()
        self.assertFalse(is_session_started())

        session_id_a = cache_codec.start_session(session_id)
        # original session no longer exists
        self.assertNotEqual(session_id_a, session_id)
        # original session data no longer exists
        self.assertIsNone(context.cache_get(KEY))

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
        context.cache_set(KEY, b"A")
        for _ in range(cache_codec._MAX_SESSIONS_COUNT):
            cache_codec.start_session()
        self.assertNotEqual(cache_codec.start_session(session_id), session_id)
        self.assertIsNone(context.cache_get(KEY))

    def test_get_set(self):
        session_id1 = cache_codec.start_session()
        context.cache_set(KEY, b"hello")
        self.assertEqual(context.cache_get(KEY), b"hello")

        session_id2 = cache_codec.start_session()
        context.cache_set(KEY, b"world")
        self.assertEqual(context.cache_get(KEY), b"world")

        cache_codec.start_session(session_id2)
        self.assertEqual(context.cache_get(KEY), b"world")
        cache_codec.start_session(session_id1)
        self.assertEqual(context.cache_get(KEY), b"hello")

        cache.clear_all()
        with self.assertRaises(cache_common.InvalidSessionError):
            context.cache_get(KEY)

    def test_get_set_int(self):
        session_id1 = cache_codec.start_session()
        context.cache_set_int(KEY, 1234)
        self.assertEqual(context.cache_get_int(KEY), 1234)

        session_id2 = cache_codec.start_session()
        context.cache_set_int(KEY, 5678)
        self.assertEqual(context.cache_get_int(KEY), 5678)

        cache_codec.start_session(session_id2)
        self.assertEqual(context.cache_get_int(KEY), 5678)
        cache_codec.start_session(session_id1)
        self.assertEqual(context.cache_get_int(KEY), 1234)

        cache.clear_all()
        with self.assertRaises(cache_common.InvalidSessionError):
            context.cache_get_int(KEY)

    def test_delete(self):
        session_id1 = cache_codec.start_session()
        self.assertIsNone(context.cache_get(KEY))
        context.cache_set(KEY, b"hello")
        self.assertEqual(context.cache_get(KEY), b"hello")
        context.cache_delete(KEY)
        self.assertIsNone(context.cache_get(KEY))

        context.cache_set(KEY, b"hello")
        cache_codec.start_session()
        self.assertIsNone(context.cache_get(KEY))
        context.cache_set(KEY, b"hello")
        self.assertEqual(context.cache_get(KEY), b"hello")
        context.cache_delete(KEY)
        self.assertIsNone(context.cache_get(KEY))

        cache_codec.start_session(session_id1)
        self.assertEqual(context.cache_get(KEY), b"hello")

    def test_decorators(self):
        run_count = 0
        cache_codec.start_session()

        @stored(KEY)
        def func():
            nonlocal run_count
            run_count += 1
            return b"foo"

        # cache is empty
        self.assertIsNone(context.cache_get(KEY))
        self.assertEqual(run_count, 0)
        self.assertEqual(func(), b"foo")
        # function was run
        self.assertEqual(run_count, 1)
        self.assertEqual(context.cache_get(KEY), b"foo")
        # function does not run again but returns cached value
        self.assertEqual(func(), b"foo")
        self.assertEqual(run_count, 1)

        @stored_async(KEY)
        async def async_func():
            nonlocal run_count
            run_count += 1
            return b"bar"

        # cache is still full
        self.assertEqual(await_result(async_func()), b"foo")
        self.assertEqual(run_count, 1)

        cache_codec.start_session()
        self.assertEqual(await_result(async_func()), b"bar")
        self.assertEqual(run_count, 2)
        # awaitable is also run only once
        self.assertEqual(await_result(async_func()), b"bar")
        self.assertEqual(run_count, 2)

    def test_empty_value(self):
        cache_codec.start_session()

        self.assertIsNone(context.cache_get(KEY))
        context.cache_set(KEY, b"")
        self.assertEqual(context.cache_get(KEY), b"")

        context.cache_delete(KEY)
        run_count = 0

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
        context.cache_set(KEY, b"hello")
        # check that it is cleared
        features = call_Initialize()
        session_id = features.session_id
        self.assertIsNone(context.cache_get(KEY))
        # store "hello" again
        context.cache_set(KEY, b"hello")
        self.assertEqual(context.cache_get(KEY), b"hello")

        # supplying a different session ID starts a new cache
        call_Initialize(session_id=b"A" * cache_codec.SESSION_ID_LENGTH)
        self.assertIsNone(context.cache_get(KEY))

        # but resuming a session loads the previous one
        call_Initialize(session_id=session_id)
        self.assertEqual(context.cache_get(KEY), b"hello")

    def test_EndSession(self):
        self.assertRaises(cache_common.InvalidSessionError, context.cache_get, KEY)
        cache_codec.start_session()
        self.assertTrue(is_session_started())
        self.assertIsNone(context.cache_get(KEY))
        await_result(handle_EndSession(EndSession()))
        self.assertFalse(is_session_started())
        self.assertRaises(cache_common.InvalidSessionError, context.cache_get, KEY)


if __name__ == "__main__":
    unittest.main()
