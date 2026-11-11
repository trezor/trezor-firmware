# flake8: noqa: F403,F405
from common import *  # isort:skip

from storage import cache, cache_common


@unittest.skipUnless(utils.USE_WARD_SERVICE_CHANNEL, "requires the WARD interface")
class TestWardServiceCache(unittest.TestCase):
    def tearDown(self):
        cache.get_sessionless_cache().delete(cache_common.APP_WARD_SERVICE_BINDING)

    def test_session_reset_keeps_only_the_transport_binding(self):
        stored = cache.get_sessionless_cache()
        binding = b"\x01\x00\x00\x00\x07"
        stored.set(cache_common.APP_WARD_SERVICE_BINDING, binding)
        stored.set(cache_common.APP_WARD_SYNC_RECORD, bytes(129))
        stored.set(cache_common.APP_WARD_ROOT_RECORD, bytes(92))
        cache.clear_all()
        self.assertEqual(stored.get(cache_common.APP_WARD_SERVICE_BINDING), binding)
        self.assertIsNone(stored.get(cache_common.APP_WARD_SYNC_RECORD))
        self.assertIsNone(stored.get(cache_common.APP_WARD_ROOT_RECORD))

    def test_listener_recreation_reuses_the_binding_without_a_large_buffer(self):
        from trezor.wire.ward_channel import Endpoint

        class Interface:
            RX_PACKET_LEN = 64
            TX_PACKET_LEN = 64

        stored = cache.get_sessionless_cache()
        stored.set(cache_common.APP_WARD_SERVICE_BINDING, b"\x01\x00\x00\x00\x07")
        endpoint = Endpoint(Interface())
        self.assertTrue(endpoint.bound)
        self.assertEqual(endpoint.generation, 7)
        self.assertEqual(len(endpoint.codec.report), 64)


if __name__ == "__main__":
    unittest.main()
