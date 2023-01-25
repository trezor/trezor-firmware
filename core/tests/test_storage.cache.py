from common import *
from mock_storage import mock_storage

from storage import cache
from trezor.messages import Initialize
from trezor.messages import EndSession
from trezor.wire import DUMMY_CONTEXT

from apps.base import handle_Initialize, handle_EndSession

KEY = 0


# Function moved from cache.py, as it was not used there
def is_session_started() -> bool:
    return cache._active_session_idx is not None


class TestStorageCache(unittest.TestCase):
    def setUp(self):
        cache.clear_all()

    def test_start_session(self):
        session_id_a = cache.start_session()
        self.assertIsNotNone(session_id_a)
        session_id_b = cache.start_session()
        self.assertNotEqual(session_id_a, session_id_b)

        cache.clear_all()
        with self.assertRaises(cache.InvalidSessionError):
            cache.set(KEY, "something")
        with self.assertRaises(cache.InvalidSessionError):
            cache.get(KEY)

    def test_end_session(self):
        session_id = cache.start_session()
        self.assertTrue(is_session_started())
        cache.set(KEY, b"A")
        cache.end_current_session()
        self.assertFalse(is_session_started())
        self.assertRaises(cache.InvalidSessionError, cache.get, KEY)

        # ending an ended session should be a no-op
        cache.end_current_session()
        self.assertFalse(is_session_started())

        session_id_a = cache.start_session(session_id)
        # original session no longer exists
        self.assertNotEqual(session_id_a, session_id)
        # original session data no longer exists
        self.assertIsNone(cache.get(KEY))

        # create a new session
        session_id_b = cache.start_session()
        # switch back to original session
        session_id = cache.start_session(session_id_a)
        self.assertEqual(session_id, session_id_a)
        # end original session
        cache.end_current_session()
        # switch back to B
        session_id = cache.start_session(session_id_b)
        self.assertEqual(session_id, session_id_b)

    def test_session_queue(self):
        session_id = cache.start_session()
        self.assertEqual(cache.start_session(session_id), session_id)
        cache.set(KEY, b"A")
        for i in range(cache._MAX_SESSIONS_COUNT):
            cache.start_session()
        self.assertNotEqual(cache.start_session(session_id), session_id)
        self.assertIsNone(cache.get(KEY))

    def test_get_set(self):
        session_id1 = cache.start_session()
        cache.set(KEY, b"hello")
        self.assertEqual(cache.get(KEY), b"hello")

        session_id2 = cache.start_session()
        cache.set(KEY, b"world")
        self.assertEqual(cache.get(KEY), b"world")

        cache.start_session(session_id2)
        self.assertEqual(cache.get(KEY), b"world")
        cache.start_session(session_id1)
        self.assertEqual(cache.get(KEY), b"hello")

        cache.clear_all()
        with self.assertRaises(cache.InvalidSessionError):
            cache.get(KEY)

    def test_get_set_int(self):
        session_id1 = cache.start_session()
        cache.set_int(KEY, 1234)
        self.assertEqual(cache.get_int(KEY), 1234)

        session_id2 = cache.start_session()
        cache.set_int(KEY, 5678)
        self.assertEqual(cache.get_int(KEY), 5678)

        cache.start_session(session_id2)
        self.assertEqual(cache.get_int(KEY), 5678)
        cache.start_session(session_id1)
        self.assertEqual(cache.get_int(KEY), 1234)

        cache.clear_all()
        with self.assertRaises(cache.InvalidSessionError):
            cache.get_int(KEY)

    def test_delete(self):
        session_id1 = cache.start_session()
        self.assertIsNone(cache.get(KEY))
        cache.set(KEY, b"hello")
        self.assertEqual(cache.get(KEY), b"hello")
        cache.delete(KEY)
        self.assertIsNone(cache.get(KEY))

        cache.set(KEY, b"hello")
        session_id2 = cache.start_session()
        self.assertIsNone(cache.get(KEY))
        cache.set(KEY, b"hello")
        self.assertEqual(cache.get(KEY), b"hello")
        cache.delete(KEY)
        self.assertIsNone(cache.get(KEY))

        cache.start_session(session_id1)
        self.assertEqual(cache.get(KEY), b"hello")

    def test_decorators(self):
        run_count = 0
        cache.start_session()

        @cache.stored(KEY)
        def func():
            nonlocal run_count
            run_count += 1
            return b"foo"

        # cache is empty
        self.assertIsNone(cache.get(KEY))
        self.assertEqual(run_count, 0)
        self.assertEqual(func(), b"foo")
        # function was run
        self.assertEqual(run_count, 1)
        self.assertEqual(cache.get(KEY), b"foo")
        # function does not run again but returns cached value
        self.assertEqual(func(), b"foo")
        self.assertEqual(run_count, 1)

        @cache.stored_async(KEY)
        async def async_func():
            nonlocal run_count
            run_count += 1
            return b"bar"

        # cache is still full
        self.assertEqual(await_result(async_func()), b"foo")
        self.assertEqual(run_count, 1)

        cache.start_session()
        self.assertEqual(await_result(async_func()), b"bar")
        self.assertEqual(run_count, 2)
        # awaitable is also run only once
        self.assertEqual(await_result(async_func()), b"bar")
        self.assertEqual(run_count, 2)

    def test_empty_value(self):
        cache.start_session()

        self.assertIsNone(cache.get(KEY))
        cache.set(KEY, b"")
        self.assertEqual(cache.get(KEY), b"")

        cache.delete(KEY)
        run_count = 0

        @cache.stored(KEY)
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
            return await_result(handle_Initialize(DUMMY_CONTEXT, msg))

        # calling Initialize without an ID allocates a new one
        session_id = cache.start_session()
        features = call_Initialize()
        self.assertNotEqual(session_id, features.session_id)

        # calling Initialize with the current ID does not allocate a new one
        features = call_Initialize(session_id=session_id)
        self.assertEqual(session_id, features.session_id)

        # store "hello"
        cache.set(KEY, b"hello")
        # check that it is cleared
        features = call_Initialize()
        session_id = features.session_id
        self.assertIsNone(cache.get(KEY))
        # store "hello" again
        cache.set(KEY, b"hello")
        self.assertEqual(cache.get(KEY), b"hello")

        # supplying a different session ID starts a new cache
        call_Initialize(session_id=b"A" * cache._SESSION_ID_LENGTH)
        self.assertIsNone(cache.get(KEY))

        # but resuming a session loads the previous one
        call_Initialize(session_id=session_id)
        self.assertEqual(cache.get(KEY), b"hello")

    def test_EndSession(self):
        self.assertRaises(cache.InvalidSessionError, cache.get, KEY)
        session_id = cache.start_session()
        self.assertTrue(is_session_started())
        self.assertIsNone(cache.get(KEY))
        await_result(handle_EndSession(DUMMY_CONTEXT, EndSession()))
        self.assertFalse(is_session_started())
        self.assertRaises(cache.InvalidSessionError, cache.get, KEY)


if __name__ == "__main__":
    unittest.main()
