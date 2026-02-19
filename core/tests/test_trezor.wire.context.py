# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import protobuf
from trezor.wire import context
from trezor.wire.context import NoWireContext, UnexpectedMessageException
from trezor.wire.protocol_common import Context, Message
from storage.cache_common import SESSIONLESS_FLAG
from mock_wire_interface import MockHID


class MockContext(Context):
    """Mock context for testing."""

    def __init__(self):
        super().__init__(MockHID())
        self._cache = {}

    async def read(self, expected_types, expected_type=None):
        return None

    async def write(self, msg):
        pass

    @property
    def cache(self):
        return self._cache


class TestWireContext(unittest.TestCase):
    def setUp(self):
        # Clear the global context before each test
        context.CURRENT_CONTEXT = None

    def tearDown(self):
        # Clean up after tests
        context.CURRENT_CONTEXT = None

    def test_current_context_initially_none(self):
        """Test that CURRENT_CONTEXT starts as None."""
        self.assertIsNone(context.CURRENT_CONTEXT)

    def test_get_context_without_context_raises(self):
        """Test that get_context raises when no context is set."""
        with self.assertRaises(NoWireContext):
            context.get_context()

    def test_get_context_with_context(self):
        """Test that get_context returns the current context."""
        ctx = MockContext()
        context.CURRENT_CONTEXT = ctx
        self.assertIs(context.get_context(), ctx)

    def test_with_context_sets_and_clears_context(self):
        """Test that with_context properly manages CURRENT_CONTEXT."""
        ctx = MockContext()

        async def dummy_workflow():
            # Inside the workflow, context should be set
            self.assertIs(context.CURRENT_CONTEXT, ctx)
            return 42

        # Before running, context should be None
        self.assertIsNone(context.CURRENT_CONTEXT)

        # Run the workflow with context
        workflow_task = dummy_workflow()
        wrapped = context.with_context(ctx, workflow_task)
        result = await_result(wrapped)

        # After running, context should be None again
        self.assertIsNone(context.CURRENT_CONTEXT)
        self.assertEqual(result, 42)

    def test_with_context_exception_clears_context(self):
        """Test that with_context clears context even on exception."""
        ctx = MockContext()

        async def failing_workflow():
            self.assertIs(context.CURRENT_CONTEXT, ctx)
            raise ValueError("test error")

        workflow_task = failing_workflow()
        wrapped = context.with_context(ctx, workflow_task)

        with self.assertRaises(ValueError):
            await_result(wrapped)

        # Context should be cleared even after exception
        self.assertIsNone(context.CURRENT_CONTEXT)


class TestUnexpectedMessageException(unittest.TestCase):
    def test_unexpected_message_with_message(self):
        """Test UnexpectedMessageException with a message."""
        msg = Message(42, b"data")
        exc = UnexpectedMessageException(msg)
        self.assertIs(exc.msg, msg)

    def test_unexpected_message_without_message(self):
        """Test UnexpectedMessageException with None."""
        exc = UnexpectedMessageException(None)
        self.assertIsNone(exc.msg)


class TestCacheAccess(unittest.TestCase):
    def setUp(self):
        context.CURRENT_CONTEXT = None

    def tearDown(self):
        context.CURRENT_CONTEXT = None

    def test_cache_get_without_context_raises(self):
        """Test that cache operations raise without context."""
        with self.assertRaises(NoWireContext):
            context.cache_get(0x01)

    def test_cache_set_without_context_raises(self):
        """Test that cache_set raises without context."""
        with self.assertRaises(NoWireContext):
            context.cache_set(0x01, b"value")

    def test_cache_delete_without_context_raises(self):
        """Test that cache_delete raises without context."""
        with self.assertRaises(NoWireContext):
            context.cache_delete(0x01)

    def test_cache_is_set_without_context_raises(self):
        """Test that cache_is_set raises without context."""
        with self.assertRaises(NoWireContext):
            context.cache_is_set(0x01)


class TestNoWireContext(unittest.TestCase):
    def test_no_wire_context_is_runtime_error(self):
        """Test that NoWireContext is a RuntimeError."""
        exc = NoWireContext()
        self.assertIsInstance(exc, RuntimeError)


class TestTryGetCtxIds(unittest.TestCase):
    def setUp(self):
        context.CURRENT_CONTEXT = None

    def tearDown(self):
        context.CURRENT_CONTEXT = None

    def test_try_get_ctx_ids_without_context(self):
        """Test try_get_ctx_ids returns None without context."""
        result = context.try_get_ctx_ids()
        self.assertIsNone(result)

    def test_try_get_ctx_ids_with_non_thp_context(self):
        """Test try_get_ctx_ids with non-THP context."""
        ctx = MockContext()
        context.CURRENT_CONTEXT = ctx
        result = context.try_get_ctx_ids()
        # Should return None for non-THP contexts
        self.assertIsNone(result)


class TestWithContextEdgeCases(unittest.TestCase):
    def setUp(self):
        context.CURRENT_CONTEXT = None

    def tearDown(self):
        context.CURRENT_CONTEXT = None

    def test_with_context_nested_yields(self):
        """Test with_context handles multiple yields correctly."""
        ctx = MockContext()

        async def multi_yield_workflow():
            self.assertIs(context.CURRENT_CONTEXT, ctx)
            await loop.sleep(0)  # yield once
            self.assertIs(context.CURRENT_CONTEXT, ctx)
            await loop.sleep(0)  # yield again
            return "done"

        workflow_task = multi_yield_workflow()
        wrapped = context.with_context(ctx, workflow_task)
        result = await_result(wrapped)

        self.assertEqual(result, "done")
        self.assertIsNone(context.CURRENT_CONTEXT)

    def test_cache_operations_with_sessionless_flag(self):
        """Test that sessionless cache operations are handled differently."""
        # Sessionless flag should bypass CURRENT_CONTEXT check
        # This is just verifying the flag exists
        self.assertIsInstance(SESSIONLESS_FLAG, int)
        self.assertGreater(SESSIONLESS_FLAG, 0)


if __name__ == "__main__":
    unittest.main()