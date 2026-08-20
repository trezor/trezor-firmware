# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils

if utils.USE_THP:
    from mock_wire_interface import MockHID
    from trezor import wire
    from trezor.wire import Provider, buffers_provider_for
    from trezor.wire.thp.interface_context import ThpContext
    from trezor.wire.thp.memory_manager import ThpBuffer


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


if __name__ == "__main__":
    unittest.main()
