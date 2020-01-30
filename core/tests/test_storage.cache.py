from common import *
from mock import patch
from mock_storage import mock_storage

import storage
from storage import cache
from trezor.messages.Initialize import Initialize
from trezor.messages.ClearSession import ClearSession
from trezor.wire import DUMMY_CONTEXT

from apps.homescreen import handle_Initialize, handle_ClearSession

KEY = 99


class TestStorageCache(unittest.TestCase):
    def test_session_id(self):
        session_id_a = cache.get_session_id()
        self.assertIsNotNone(session_id_a)
        session_id_b = cache.get_session_id()
        self.assertEqual(session_id_a, session_id_b)

        cache.clear()
        session_id_c = cache.get_session_id()
        self.assertIsNotNone(session_id_c)
        self.assertNotEqual(session_id_a, session_id_c)

    def test_get_set(self):
        value = cache.get(KEY)
        self.assertIsNone(value)

        cache.set(KEY, "hello")
        value = cache.get(KEY)
        self.assertEqual(value, "hello")

        cache.clear()
        value = cache.get(KEY)
        self.assertIsNone(value)

    @mock_storage
    def test_Initialize(self):
        def call_Initialize(**kwargs):
            msg = Initialize(**kwargs)
            return await_result(handle_Initialize(DUMMY_CONTEXT, msg))

        # calling Initialize without an ID allocates a new one
        session_id = cache.get_session_id()
        features = call_Initialize()
        new_session_id = cache.get_session_id()
        self.assertNotEqual(session_id, new_session_id)
        self.assertEqual(new_session_id, features.session_id)

        # calling Initialize with the current ID does not allocate a new one
        features = call_Initialize(session_id=new_session_id)
        same_session_id = cache.get_session_id()
        self.assertEqual(new_session_id, same_session_id)
        self.assertEqual(same_session_id, features.session_id)

        call_Initialize()
        # calling Initialize with a non-current ID returns a different one
        features = call_Initialize(session_id=new_session_id)
        self.assertNotEqual(new_session_id, features.session_id)

        # allocating a new session ID clears the cache
        cache.set(KEY, "hello")
        features = call_Initialize()
        self.assertIsNone(cache.get(KEY))

        # resuming a session does not clear the cache
        cache.set(KEY, "hello")
        call_Initialize(session_id=features.session_id)
        self.assertEqual(cache.get(KEY), "hello")

        # supplying a different session ID clears the cache
        self.assertNotEqual(new_session_id, features.session_id)
        call_Initialize(session_id=new_session_id)
        self.assertIsNone(cache.get(KEY))

    @mock_storage
    def test_ClearSession(self):
        def call_Initialize(**kwargs):
            msg = Initialize(**kwargs)
            return await_result(handle_Initialize(DUMMY_CONTEXT, msg))

        def call_ClearSession():
            return await_result(handle_ClearSession(DUMMY_CONTEXT, ClearSession()))

        session_id = call_Initialize().session_id
        cache.set(KEY, "hello")
        self.assertEqual(cache.get(KEY), "hello")

        call_ClearSession()
        self.assertIsNone(cache.get(KEY))
        new_session_id = cache.get_session_id()
        self.assertNotEqual(session_id, new_session_id)


if __name__ == "__main__":
    unittest.main()
