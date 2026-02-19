# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock, MockAsync, patch
from storage.cache_common import InvalidSessionError
from trezor import protobuf
from trezor.wire.protocol_common import Message
from trezor.wire.thp import SessionState
from trezor.wire.thp.session_context import (
    GenericSessionContext,
    SeedlessSessionContext,
    SessionContext,
)


class MockChannel:
    """Mock THP channel for testing."""

    def __init__(self, channel_id=b"\x01\x02\x03\x04"):
        self.iface = Mock()
        self.channel_id = channel_id
        self.messages = []

    async def decrypt_message(self):
        """Mock decrypt_message that returns canned data."""
        if self.messages:
            return self.messages.pop(0)
        # Return a mock message
        return (0, Message(1, b"test_data"))

    async def write(self, msg, session_id=None):
        """Mock write method."""
        pass

    def _log(self, message, logger=None):
        """Mock logging method."""
        pass


class MockSessionCache:
    """Mock session cache for testing."""

    def __init__(self, channel_id=b"\x01\x02\x03\x04", session_id=b"\x01"):
        self.channel_id = channel_id
        self.session_id = session_id
        self._data = {}

    def get_int(self, key, default=None):
        return self._data.get(key, default)

    def set_int(self, key, value):
        self._data[key] = value

    def get(self, key, default=None):
        return self._data.get(key, default)

    def set(self, key, value):
        self._data[key] = value


class TestGenericSessionContext(unittest.TestCase):
    def test_initialization(self):
        """Test GenericSessionContext initialization."""
        channel = MockChannel()
        session_id = 5
        ctx = GenericSessionContext(channel, session_id)

        self.assertEqual(ctx.channel, channel)
        self.assertEqual(ctx.session_id, session_id)
        self.assertEqual(ctx.channel_id, channel.channel_id)

    def test_write_delegates_to_channel(self):
        """Test that write() delegates to channel.write()."""
        channel = MockChannel()
        channel.write = MockAsync()
        ctx = GenericSessionContext(channel, 1)

        msg = Mock()
        msg.MESSAGE_NAME = "TestMsg"

        async def test():
            await ctx.write(msg)

        from trezor import loop

        loop.run(test())

        self.assertEqual(len(channel.write.calls), 1)
        self.assertEqual(channel.write.calls[0][0][0], msg)
        self.assertEqual(channel.write.calls[0][0][1], 1)


class TestSeedlessSessionContext(unittest.TestCase):
    def test_initialization(self):
        """Test SeedlessSessionContext initialization."""
        channel = MockChannel()
        session_id = 3
        ctx = SeedlessSessionContext(channel, session_id)

        self.assertEqual(ctx.channel, channel)
        self.assertEqual(ctx.session_id, session_id)

    def test_get_session_state_returns_seedless(self):
        """Test that get_session_state returns SEEDLESS."""
        channel = MockChannel()
        ctx = SeedlessSessionContext(channel, 1)

        state = ctx.get_session_state()
        self.assertEqual(state, SessionState.SEEDLESS)

    def test_cache_property_raises_invalid_session(self):
        """Test that accessing cache property raises InvalidSessionError."""
        channel = MockChannel()
        ctx = SeedlessSessionContext(channel, 1)

        with self.assertRaises(InvalidSessionError):
            _ = ctx.cache


class TestSessionContext(unittest.TestCase):
    def test_initialization(self):
        """Test SessionContext initialization."""
        channel = MockChannel(b"\x01\x02\x03\x04")
        session_cache = MockSessionCache(b"\x01\x02\x03\x04", b"\x05")
        ctx = SessionContext(channel, session_cache)

        self.assertEqual(ctx.channel, channel)
        self.assertEqual(ctx.session_id, 5)  # 0x05 as int
        self.assertEqual(ctx.session_cache, session_cache)

    def test_initialization_channel_id_mismatch(self):
        """Test that initialization fails if channel IDs don't match."""
        channel = MockChannel(b"\x01\x02\x03\x04")
        session_cache = MockSessionCache(b"\xFF\xFF\xFF\xFF", b"\x01")

        with self.assertRaises(Exception) as e:
            SessionContext(channel, session_cache)

        self.assertIn("different channel id", str(e.value))

    def test_get_session_state_default(self):
        """Test get_session_state returns default UNALLOCATED."""
        from storage.cache_common import SESSION_STATE

        channel = MockChannel()
        session_cache = MockSessionCache()
        ctx = SessionContext(channel, session_cache)

        state = ctx.get_session_state()
        self.assertEqual(state, SessionState.UNALLOCATED)

    def test_get_session_state_custom_value(self):
        """Test get_session_state returns stored value."""
        from storage.cache_common import SESSION_STATE

        channel = MockChannel()
        session_cache = MockSessionCache()
        session_cache.set_int(SESSION_STATE, SessionState.ALLOCATED)
        ctx = SessionContext(channel, session_cache)

        state = ctx.get_session_state()
        self.assertEqual(state, SessionState.ALLOCATED)

    def test_set_session_state(self):
        """Test set_session_state updates the cache."""
        from storage.cache_common import SESSION_STATE

        channel = MockChannel()
        session_cache = MockSessionCache()
        ctx = SessionContext(channel, session_cache)

        ctx.set_session_state(SessionState.ALLOCATED)

        stored_value = session_cache.get_int(SESSION_STATE)
        self.assertEqual(stored_value, SessionState.ALLOCATED)

    def test_cache_property_returns_session_cache(self):
        """Test that cache property returns the session cache."""
        channel = MockChannel()
        session_cache = MockSessionCache()
        ctx = SessionContext(channel, session_cache)

        cache = ctx.cache
        self.assertEqual(cache, session_cache)

    def test_release_clears_session(self):
        """Test that release() clears the session cache."""
        from storage import cache_thp

        channel = MockChannel()
        session_cache = MockSessionCache()
        ctx = SessionContext(channel, session_cache)

        # Mock the clear_session function
        with patch(cache_thp, "clear_session", Mock()) as mock_clear:
            ctx.release()
            # clear_session should be called
            self.assertEqual(len(mock_clear.calls), 1)
            self.assertEqual(mock_clear.calls[0][0][0], session_cache)


class TestSessionContextEdgeCases(unittest.TestCase):
    def test_session_id_conversion(self):
        """Test that session_id is correctly converted from bytes to int."""
        channel = MockChannel()
        session_cache = MockSessionCache(b"\x01\x02\x03\x04", b"\xFF")
        ctx = SessionContext(channel, session_cache)

        self.assertEqual(ctx.session_id, 255)

    def test_session_id_multi_byte(self):
        """Test session_id conversion with single byte."""
        channel = MockChannel()
        session_cache = MockSessionCache(b"\x01\x02\x03\x04", b"\x00")
        ctx = SessionContext(channel, session_cache)

        self.assertEqual(ctx.session_id, 0)

    def test_generic_session_channel_id_attribute(self):
        """Test that GenericSessionContext has channel_id attribute."""
        channel = MockChannel(b"\xAA\xBB\xCC\xDD")
        ctx = GenericSessionContext(channel, 10)

        self.assertEqual(ctx.channel_id, b"\xAA\xBB\xCC\xDD")

    def test_write_preserves_session_id(self):
        """Test that write uses the correct session_id."""
        channel = MockChannel()
        writes = []

        async def mock_write(msg, session_id):
            writes.append((msg, session_id))

        channel.write = mock_write

        session_cache = MockSessionCache(b"\x01\x02\x03\x04", b"\x07")
        ctx = SessionContext(channel, session_cache)

        msg = Mock()
        msg.MESSAGE_NAME = "TestMessage"

        from trezor import loop

        async def test():
            await ctx.write(msg)

        loop.run(test())

        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][0], msg)
        self.assertEqual(writes[0][1], 7)  # session_id as int


class TestSessionStateTransitions(unittest.TestCase):
    def test_state_transition_unallocated_to_allocated(self):
        """Test transitioning from UNALLOCATED to ALLOCATED."""
        channel = MockChannel()
        session_cache = MockSessionCache()
        ctx = SessionContext(channel, session_cache)

        initial_state = ctx.get_session_state()
        self.assertEqual(initial_state, SessionState.UNALLOCATED)

        ctx.set_session_state(SessionState.ALLOCATED)

        new_state = ctx.get_session_state()
        self.assertEqual(new_state, SessionState.ALLOCATED)

    def test_multiple_state_changes(self):
        """Test multiple state transitions."""
        channel = MockChannel()
        session_cache = MockSessionCache()
        ctx = SessionContext(channel, session_cache)

        ctx.set_session_state(SessionState.ALLOCATED)
        self.assertEqual(ctx.get_session_state(), SessionState.ALLOCATED)

        ctx.set_session_state(SessionState.UNALLOCATED)
        self.assertEqual(ctx.get_session_state(), SessionState.UNALLOCATED)


if __name__ == "__main__":
    unittest.main()