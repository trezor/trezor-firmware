# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import utils

if utils.USE_THP:
    from mock import patch
    from mock_wire_interface import MockHID
    from trezor.wire.errors import FirmwareError
    from trezor.wire.thp import channel as channel_mod
    from trezor.wire.thp.channel import Channel
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

        def __init__(self, iface_num: int) -> None:
            self._iface_num = iface_num

        def channel_info(self, _channel_id: int) -> "_Info":
            return _Info(self._iface_num)


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


if __name__ == "__main__":
    unittest.main()
