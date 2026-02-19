# flake8: noqa: F403,F405
from common import *  # isort:skip

if not utils.USE_THP:
    raise unittest.SkipTest("THP not enabled")

from trezor.wire.thp.session_context import (
    GenericSessionContext,
    SeedlessSessionContext,
    SessionContext,
)
from trezor.wire.thp import SessionState
from trezor.wire.protocol_common import Message
from trezor.wire.context import UnexpectedMessageException
from storage.cache_common import InvalidSessionError
from mock_wire_interface import MockHID


class MockChannel:
    """Mock channel for testing session contexts."""

    def __init__(self):
        self.iface = MockHID()
        self.channel_id = b"\x01\x02\x03\x04"
        self.messages = []
        self.written = []

    async def decrypt_message(self):
        if self.messages:
            msg = self.messages.pop(0)
            return (msg[0], msg[1])  # (session_id, message)
        return (0, Message(0, b""))

    async def write(self, msg, session_id=None):
        self.written.append((msg, session_id))

    def _log(self, *args, **kwargs):
        pass


class MockSessionCache:
    """Mock session cache for testing."""

    def __init__(self, channel_id, session_id):
        self.channel_id = channel_id
        self.session_id = session_id
        self.data = {}

    def get_int(self, key, default=None):
        return self.data.get(key, default)

    def set_int(self, key, value):
        self.data[key] = value


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestGenericSessionContext(unittest.TestCase):
    def test_generic_session_context_creation(self):
        """Test creating a GenericSessionContext."""
        channel = MockChannel()
        session_id = 1
        ctx = GenericSessionContext(channel, session_id)

        self.assertIs(ctx.channel, channel)
        self.assertEqual(ctx.session_id, session_id)
        self.assertEqual(ctx.channel_id, channel.channel_id)
        self.assertEqual(ctx.iface, channel.iface)

    def test_generic_session_context_write(self):
        """Test write forwards to channel with session_id."""
        channel = MockChannel()
        session_id = 1
        ctx = GenericSessionContext(channel, session_id)

        # Write is async, so we create a mock message
        class MockMessage:
            MESSAGE_WIRE_TYPE = 42

        msg = MockMessage()
        # We can't await here, but we verify write returns an awaitable
        result = ctx.write(msg)
        self.assertTrue(hasattr(result, '__await__'))


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestSeedlessSessionContext(unittest.TestCase):
    def test_seedless_session_context_creation(self):
        """Test creating a SeedlessSessionContext."""
        channel = MockChannel()
        session_id = 2
        ctx = SeedlessSessionContext(channel, session_id)

        self.assertIs(ctx.channel, channel)
        self.assertEqual(ctx.session_id, session_id)

    def test_seedless_get_session_state(self):
        """Test that seedless context returns SEEDLESS state."""
        channel = MockChannel()
        session_id = 2
        ctx = SeedlessSessionContext(channel, session_id)

        state = ctx.get_session_state()
        self.assertEqual(state, SessionState.SEEDLESS)

    def test_seedless_cache_access_raises(self):
        """Test that accessing cache raises InvalidSessionError."""
        channel = MockChannel()
        session_id = 2
        ctx = SeedlessSessionContext(channel, session_id)

        with self.assertRaises(InvalidSessionError):
            _ = ctx.cache


@unittest.skipUnless(utils.USE_THP, "only needed for THP")
class TestSessionContext(unittest.TestCase):
    def test_session_context_creation(self):
        """Test creating a SessionContext."""
        channel = MockChannel()
        session_cache = MockSessionCache(channel.channel_id, b"\x01")
        ctx = SessionContext(channel, session_cache)

        self.assertIs(ctx.channel, channel)
        self.assertIs(ctx.session_cache, session_cache)
        self.assertEqual(ctx.session_id, 1)  # from bytes

    def test_session_context_mismatched_channel_id_raises(self):
        """Test that mismatched channel_id raises exception."""
        channel = MockChannel()
        session_cache = MockSessionCache(b"\xff\xff\xff\xff", b"\x01")

        with self.assertRaises(Exception) as cm:
            SessionContext(channel, session_cache)

        self.assertIn("channel id", str(cm.exception).lower())

    def test_session_context_get_session_state(self):
        """Test getting session state from cache."""
        from storage.cache_common import SESSION_STATE

        channel = MockChannel()
        session_cache = MockSessionCache(channel.channel_id, b"\x01")
        session_cache.set_int(SESSION_STATE, SessionState.ALLOCATED)

        ctx = SessionContext(channel, session_cache)
        state = ctx.get_session_state()
        self.assertEqual(state, SessionState.ALLOCATED)

    def test_session_context_set_session_state(self):
        """Test setting session state to cache."""
        from storage.cache_common import SESSION_STATE

        channel = MockChannel()
        session_cache = MockSessionCache(channel.channel_id, b"\x01")
        ctx = SessionContext(channel, session_cache)

        ctx.set_session_state(SessionState.AUTHENTICATED)
        self.assertEqual(
            session_cache.get_int(SESSION_STATE), SessionState.AUTHENTICATED
        )

    def test_session_context_cache_property(self):
        """Test that cache property returns session_cache."""
        channel = MockChannel()
        session_cache = MockSessionCache(channel.channel_id, b"\x01")
        ctx = SessionContext(channel, session_cache)

        self.assertIs(ctx.cache, session_cache)

    def test_session_context_release(self):
        """Test that release is callable."""
        channel = MockChannel()
        session_cache = MockSessionCache(channel.channel_id, b"\x01")
        ctx = SessionContext(channel, session_cache)

        # Should not raise
        ctx.release()


if __name__ == "__main__":
    unittest.main()