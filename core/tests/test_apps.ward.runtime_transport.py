# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils
from trezor.messages import (
    WardEntryAck,
    WardEntryRequest,
    WardLeafAck,
    WardMutationApplied,
)
from trezor.wire import DataError, context

from apps.ward import cas, common, root, round, service, trie
from apps.ward.attest import EMPTY_ROOT
from apps.ward.keys import ENTRY_TYPE_ADDRESS


@unittest.skipUnless(utils.USE_WARD_SERVICE_CHANNEL, "requires a service-enabled build")
class TestWardRuntimeTransport(TestCaseWithContext):
    def setUp(self):
        self.calls = []
        self.originals = []
        if utils.USE_THP:
            from storage import cache_thp

            cache_thp.clear_trezor_cache()
        else:
            from storage import cache_codec

            cache_codec.start_session()
        service.clear_binding()
        round.mark_offline()

        async def counter():
            return 0

        async def head():
            return EMPTY_ROOT

        async def wallet(request, expected_type):
            self.calls.append("wallet")
            self.assertEqual(
                request.MESSAGE_WIRE_TYPE, WardEntryRequest.MESSAGE_WIRE_TYPE
            )
            self.assertEqual(
                expected_type.MESSAGE_WIRE_TYPE, WardEntryAck.MESSAGE_WIRE_TYPE
            )
            return WardEntryAck()

        async def fetch(entry_key):
            self.calls.append("fetch")
            return WardEntryAck()

        async def publish(*args):
            self.calls.append("publish")

        async def authorise(*args):
            return b"a" * 32, b"s" * 64

        self.patch(root, "get_counter", counter)
        self.patch(root, "get_root", head)
        self.patch(context, "call", wallet)
        self.patch(service, "fetch", fetch)
        self.patch(service, "publish", publish)
        self.patch(cas, "authorise", authorise)
        self.patch(trie, "compute_new_root", lambda *args, **kwargs: EMPTY_ROOT)

    def patch(self, module, name, value):
        self.originals.append((module, name, getattr(module, name)))
        setattr(module, name, value)

    def tearDown(self):
        for module, name, value in reversed(self.originals):
            setattr(module, name, value)
        service.clear_binding()
        round.mark_offline()

    def bind(self):
        service.set_binding(7, 1, 0)

    def pull(self, use_service=None):
        return await_result(
            common.pull_leaf(b"k" * 32, ENTRY_TYPE_ADDRESS, use_service=use_service)
        )

    def commit(self, use_service=None):
        return await_result(
            common.commit_change(
                b"k" * 32,
                ENTRY_TYPE_ADDRESS,
                "test",
                b"id",
                None,
                None,
                ([], None, None),
                use_service=use_service,
            )
        )

    def test_unbound_service_uses_wallet_and_requires_host_sync(self):
        self.assertFalse(common.service_available())
        self.assertFalse(await_result(common.online()))
        round.mark_online()
        self.assertTrue(await_result(common.online()))
        self.pull()
        self.assertEqual(self.commit().MESSAGE_WIRE_TYPE, WardLeafAck.MESSAGE_WIRE_TYPE)
        self.assertEqual(self.calls, ["wallet"])

    def test_bound_service_fetches_and_publishes(self):
        self.bind()
        self.assertTrue(common.service_available())
        self.pull()
        self.assertEqual(
            self.commit().MESSAGE_WIRE_TYPE, WardMutationApplied.MESSAGE_WIRE_TYPE
        )
        self.assertEqual(self.calls, ["fetch", "publish"])

    def test_binding_mid_operation_does_not_change_wallet_routing(self):
        selected = common.service_available()
        self.pull(selected)
        self.bind()  # e.g. while the wallet operation waits for confirmation
        self.assertEqual(
            self.commit(selected).MESSAGE_WIRE_TYPE, WardLeafAck.MESSAGE_WIRE_TYPE
        )
        self.assertEqual(self.calls, ["wallet"])

    def test_lost_selected_service_does_not_fall_back_mid_operation(self):
        self.bind()
        selected = common.service_available()
        self.pull(selected)
        service.clear_binding()

        async def disconnected(*args):
            raise DataError("no WARD service is bound")

        self.patch(service, "publish", disconnected)
        with self.assertRaises(DataError):
            self.commit(selected)
        self.assertEqual(self.calls, ["fetch"])


if __name__ == "__main__":
    unittest.main()
