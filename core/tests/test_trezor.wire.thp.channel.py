# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils

if utils.USE_THP:
    import trezorthp
    from mock import patch
    from mock_wire_interface import MockHID
    from trezor.wire.errors import DataError, FirmwareError
    from trezor.wire.thp import channel as channel_mod
    from trezor.wire.thp.channel import Channel
    from trezor.wire import Provider
    from trezor.wire.thp.interface_context import ThpContext
    from trezor.wire.thp.memory_manager import ThpBuffer

    class _Info:
        """What `trezorthp.channel_info` hands back, with only the fields the constructor reads.

        Faked rather than allocated because a real channel needs a handshake to exist, and this
        is about ONE branch in the constructor -- the interface it was built against. Patching the
        lookup is also the only way to produce the mismatch at all: the Rust side would never
        report a channel on an interface it is not on, which is precisely why the Python side
        could not previously tell whether it had been handed the right one.
        """

        def __init__(self, iface_num: int) -> None:
            self.iface_num = iface_num
            self.last_write = None
            self.pairing_state = None  # None => already in encrypted transport
            self.handshake_hash = None
            self.host_static_public_key = None
            self.credential = None

    class _FakeThp:
        """Stands in for the `trezorthp` C module as `channel.py` sees it.

        Patched on the CHANNEL MODULE rather than on `trezorthp` itself: the latter is a C
        extension and rejects attribute assignment, while `channel.py`'s module-level
        `import trezorthp` binds an ordinary attribute that can be swapped.
        """

        ThpError = trezorthp.ThpError

        def __init__(self, iface_num: int) -> None:
            self._iface_num = iface_num

        def channel_info(self, _channel_id: int) -> "_Info":
            return _Info(self._iface_num)

    class _ClosedThp:
        """A channel the Rust side no longer has: `channel_info` raises `ThpError`."""

        ThpError = trezorthp.ThpError

        def channel_info(self, _channel_id: int) -> "_Info":
            raise trezorthp.ThpError("Channel not found")


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestThpChannelInterfaceBinding(unittest.TestCase):
    """A `Channel` must refuse to exist against an interface it does not belong to.

    WHY THIS IS A REFUSAL AND NOT A COMMENT. `trezorthp.packet_out_channel` looks a channel up by
    id alone -- the lookup is global across interfaces and the binding is discarded -- and
    fragments into a buffer that the write loop then sends on whichever interface owns the
    `Channel` object. Nothing below this constructor can notice the difference, so a channel built
    against the wrong `InterfaceContext` would put one host's encrypted traffic on another host's
    wire and every layer would consider it well-formed.
    """

    _CID = 0x1234

    def _iface_ctx(self, iface_num: int):
        iface = MockHID(iface_num)
        thp_ctx = ThpContext(iface)
        (iface_ctx,) = thp_ctx._iface_ctxs
        return iface_ctx

    def _buffers(self):
        return (ThpBuffer(), ThpBuffer())

    def test_a_matching_interface_is_accepted(self):
        iface_ctx = self._iface_ctx(7)
        with patch(channel_mod, "trezorthp", _FakeThp(7)):
            channel = Channel(self._CID, iface_ctx, self._buffers())
        self.assertEqual(channel.channel_id, self._CID)
        self.assertEqual(channel.iface.iface_num(), 7)

    def test_a_foreign_interface_is_refused(self):
        iface_ctx = self._iface_ctx(7)
        # the same channel id, reported as living on a DIFFERENT interface
        with patch(channel_mod, "trezorthp", _FakeThp(8)):
            with self.assertRaises(FirmwareError):
                Channel(self._CID, iface_ctx, self._buffers())


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestThpAttachExistingChannel(unittest.TestCase):
    """Reattaching a channel the Rust side still holds but this session has no object for.

    A channel outlives the MicroPython session; the `Channel` wrapping it does not. And a channel
    that is not its interface's `active_channel` cannot be written -- `Channel.write` pokes the
    write loop, which drains `active_channel` and nothing else -- so a caller holding an id from
    persisted state must reattach before it can send.
    """

    _CID = 0x2345
    # Reused across every test here: Rust's interface table is global and capped at
    # MAX_INTERFACES, so a distinct number per test exhausts it. What is under test walks the
    # context's own `_iface_ctxs`, which is unaffected by what Rust has registered.
    _IFACE = 7

    def _ctx(self):
        thp_ctx = ThpContext(MockHID(self._IFACE))
        (iface_ctx,) = thp_ctx._iface_ctxs
        # A FRESH POOL PER TEST. The real one is a module-level singleton, so a previous test
        # would have emptied it and every later attach would fail on buffers rather than on what
        # it is meant to be checking. In production each session re-imports `wire`, so a session
        # always starts with a full pool -- the lifetime itself is covered in
        # test_trezor.wire.thp.buffers.py.
        iface_ctx._buffers_provider = Provider((ThpBuffer(64), ThpBuffer(64)))
        return thp_ctx, iface_ctx

    def test_it_attaches_and_makes_the_channel_writable(self):
        thp_ctx, iface_ctx = self._ctx()
        with patch(channel_mod, "trezorthp", _FakeThp(self._IFACE)):
            channel = thp_ctx.attach_existing_channel(self._IFACE, self._CID)
        # writable means: it is the object this interface's write loop drains
        self.assertIs(iface_ctx.active_channel, channel)
        self.assertEqual(channel.channel_id, self._CID)

    def test_reattaching_returns_the_same_object(self):
        """Two `Channel`s for one id would split its state -- one holding the mailbox being
        awaited, the other the buffers being filled."""
        thp_ctx, _iface_ctx = self._ctx()
        with patch(channel_mod, "trezorthp", _FakeThp(self._IFACE)):
            first = thp_ctx.attach_existing_channel(self._IFACE, self._CID)
            second = thp_ctx.attach_existing_channel(self._IFACE, self._CID)
        self.assertIs(first, second)

    def test_it_never_displaces_another_channel(self):
        """The displaced object is what some other task is awaiting."""
        thp_ctx, iface_ctx = self._ctx()
        with patch(channel_mod, "trezorthp", _FakeThp(self._IFACE)):
            held = thp_ctx.attach_existing_channel(self._IFACE, self._CID)
            with self.assertRaises(DataError):
                thp_ctx.attach_existing_channel(self._IFACE, self._CID + 1)
        self.assertIs(iface_ctx.active_channel, held)

    def test_it_refuses_a_channel_on_another_interface(self):
        """The safety check: `packet_out_channel` looks a channel up by id alone, so attaching to
        the wrong interface would put one host's encrypted traffic on another host's wire."""
        thp_ctx, _iface_ctx = self._ctx()
        # the interface says 14; Rust reports the channel as living on 99
        with patch(channel_mod, "trezorthp", _FakeThp(99)):
            with self.assertRaises(FirmwareError):
                thp_ctx.attach_existing_channel(self._IFACE, self._CID)

    def test_it_refuses_an_unknown_interface(self):
        thp_ctx, _iface_ctx = self._ctx()
        with patch(channel_mod, "trezorthp", _FakeThp(self._IFACE)):
            with self.assertRaises(DataError):
                thp_ctx.attach_existing_channel(self._IFACE + 1, self._CID)

    def test_it_reports_a_channel_that_is_gone(self):
        """Rust may have closed the channel since the id was recorded. That has to come back as
        unavailable, not as a Rust-level error escaping into a workflow."""
        thp_ctx, _iface_ctx = self._ctx()
        with patch(channel_mod, "trezorthp", _ClosedThp()):
            with self.assertRaises(DataError):
                thp_ctx.attach_existing_channel(self._IFACE, self._CID)


if __name__ == "__main__":
    unittest.main()
