# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils

if utils.USE_THP:
    from mock_wire_interface import MockHID
    from trezor import wire
    from trezor.wire import Provider, buffers_provider_for
    from trezor.wire.thp.interface_context import ThpContext
    from trezor.wire.thp.memory_manager import BufferSource, SharedBuffer, ThpBuffer


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestThpBufferPools(unittest.TestCase):
    """Which interface draws channel buffers from which pool.

    A provider hands out its pair ONCE and answers None afterwards, so two interfaces sharing one
    can never hold a channel at the same time -- the second is refused buffers and answers
    TRANSPORT_BUSY. That is how a second host is turned away today, and it is deliberate.

    It is also the single thing standing between the current firmware and an interface that can
    hold a service channel while a wallet channel is live elsewhere, which is why the pool an
    interface uses is now chosen per interface instead of being reached for globally.
    """

    def test_usb_and_ble_share_one_pool(self):
        """Two ordinary interfaces must keep sharing, so a second host is still refused.

        Pinned because the tempting shortcut -- give the SECOND interface to ask its own pool --
        would hand a private pool to whichever of USB or BLE happened to be second and silently
        change that refusal into two concurrent channels.
        """
        self.assertIs(
            buffers_provider_for(MockHID(1)),
            buffers_provider_for(MockHID(2)),
        )
        self.assertIs(buffers_provider_for(MockHID(1)), wire.THP_BUFFERS_PROVIDER)

    def test_an_interface_uses_the_pool_it_was_given(self):
        """The context passes a provider in; the interface must not reach for a global one."""
        iface = MockHID(3)
        thp_ctx = ThpContext(iface)
        (iface_ctx,) = thp_ctx._iface_ctxs
        self.assertIs(iface_ctx._buffers_provider, buffers_provider_for(iface))

    def test_one_pool_serves_one_channel(self):
        shared = Provider((ThpBuffer(64), ThpBuffer(64)))
        self.assertIsNotNone(shared.take())
        # ...and the interface that asks second gets nothing, which is what it reports as busy
        self.assertIsNone(shared.take())

    def test_separate_pools_serve_a_channel_each(self):
        first = Provider((ThpBuffer(64), ThpBuffer(64)))
        second = Provider((ThpBuffer(64), ThpBuffer(64)))
        self.assertIsNotNone(first.take())
        self.assertIsNotNone(second.take())


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestThpBufferSize(unittest.TestCase):
    """A buffer's size is a protocol bound, not just a memory figure.

    `get()` refuses a length it cannot serve, so whatever a buffer was created with caps the
    largest message that can pass through the interface holding it. Worth stating in a test,
    because a buffer sized to save RAM silently caps the protocol.
    """

    def test_a_buffer_serves_up_to_its_size(self):
        buf = ThpBuffer(128)
        self.assertEqual(len(buf.get(0)), 0)
        self.assertEqual(len(buf.get(128)), 128)

    def test_a_buffer_refuses_more_than_its_size(self):
        buf = ThpBuffer(128)
        with self.assertRaises(wire.FirmwareError):
            buf.get(129)

    def test_the_default_size_is_unchanged(self):
        """The default pool must not shrink by accident: every ordinary message rides on it."""
        self.assertEqual(len(ThpBuffer().buf), 8704)


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestSharedLargeBuffer(unittest.TestCase):
    """One large buffer, leased for the length of a message rather than of a channel.

    Two live channels used to mean two large buffer pairs -- 17 kB of memory that is idle almost
    all of the time, because a channel needs a large buffer only while a large message is actually
    in flight. What each channel keeps for itself is small; the large one is borrowed.
    """

    def _pair(self, small=64, large=256):
        shared = SharedBuffer(large)
        return (
            BufferSource(ThpBuffer(small), shared),
            BufferSource(ThpBuffer(small), shared),
            shared,
        )

    def test_a_small_message_never_touches_the_shared_buffer(self):
        """The common case must not contend, or the sharing costs more than it saves."""
        a, b, shared = self._pair()
        self.assertIsNotNone(a.try_get(64))
        self.assertFalse(a.holds_shared())
        self.assertIsNone(shared.holder)
        # ...and the other channel is entirely unaffected
        self.assertIsNotNone(b.try_get(64))
        self.assertFalse(b.holds_shared())

    def test_a_large_message_borrows_and_gives_back(self):
        a, _b, shared = self._pair()
        self.assertEqual(len(a.try_get(200)), 200)
        self.assertTrue(a.holds_shared())
        self.assertIs(shared.holder, a)
        a.release()
        self.assertFalse(a.holds_shared())
        self.assertIsNone(shared.holder)

    def test_the_second_claimant_is_refused_not_given_the_same_memory(self):
        """The refusal is the point. Handing both of them the buffer would corrupt both messages."""
        a, b, _shared = self._pair()
        self.assertIsNotNone(a.try_get(200))
        self.assertIsNone(b.try_get(200))
        # ...and once the holder is done, the loser gets it
        a.release()
        self.assertIsNotNone(b.try_get(200))

    def test_the_holder_may_grow_its_own_lease(self):
        """A message that grows twice must not refuse itself the buffer it already holds."""
        a, _b, _shared = self._pair()
        self.assertEqual(len(a.try_get(100)), 100)
        self.assertEqual(len(a.try_get(200)), 200)

    def test_growing_carries_the_prefix_across_the_move(self):
        """The reassembler re-verifies the CRC over the whole buffer, so the prefix must survive.

        Free when both tiers were slices of one bytearray; not free across two backing stores, and
        the failure would be a CRC mismatch far from its cause.
        """
        a, _b, _shared = self._pair()
        small = a.try_get(64)
        for i in range(64):
            small[i] = i
        grown = a.try_get(200)
        self.assertEqual(bytes(grown[:64]), bytes(range(64)))

    def test_release_is_idempotent_and_safe_without_a_lease(self):
        """Called from teardown paths that cannot know whether a message was in flight."""
        a, b, shared = self._pair()
        a.release()  # never borrowed
        self.assertIsNotNone(b.try_get(200))
        a.release()  # does not steal b's lease
        self.assertIs(shared.holder, b)

    def test_a_message_too_large_for_the_shared_buffer_leaves_no_lease(self):
        """Refusing on size must not strand the buffer for everyone else."""
        a, b, shared = self._pair()
        with self.assertRaises(wire.FirmwareError):
            a.try_get(1000)
        self.assertIsNone(shared.holder)
        self.assertIsNotNone(b.try_get(200))


if __name__ == "__main__":
    unittest.main()
