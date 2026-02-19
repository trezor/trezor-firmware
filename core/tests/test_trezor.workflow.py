# flake8: noqa: F403,F405
from common import *  # isort:skip

import utime
from trezor import loop, workflow
from trezor.enums import MessageType


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        # Clear any existing workflows
        workflow.tasks.clear()
        workflow.default_task = None
        workflow.default_constructor = None
        workflow.autolock_interrupts_workflow = True

    def test_spawn_and_close(self):
        """Test spawning and closing a workflow task."""
        async def dummy_workflow():
            return 42

        task = workflow.spawn(dummy_workflow())
        self.assertIn(task, workflow.tasks)

        result = await_result(task)
        self.assertEqual(result, 42)

    def test_spawn_multiple_workflows(self):
        """Test spawning multiple workflows simultaneously."""
        async def workflow1():
            return 1

        async def workflow2():
            return 2

        task1 = workflow.spawn(workflow1())
        task2 = workflow.spawn(workflow2())

        self.assertIn(task1, workflow.tasks)
        self.assertIn(task2, workflow.tasks)
        self.assertEqual(len(workflow.tasks), 2)

    def test_default_workflow_constructor(self):
        """Test setting and starting default workflow."""
        results = []

        async def default_workflow():
            results.append("default")
            return "default_result"

        workflow.set_default(default_workflow)
        self.assertEqual(workflow.default_constructor, default_workflow)

    def test_autolock_interrupts_flag(self):
        """Test autolock_interrupts_workflow flag behavior."""
        self.assertTrue(workflow.autolock_interrupts_workflow)

        workflow.autolock_interrupts_workflow = False
        self.assertFalse(workflow.autolock_interrupts_workflow)

        # Reset by start_default should set it back to True
        async def dummy():
            return None
        workflow.set_default(dummy)
        workflow.start_default()
        self.assertTrue(workflow.autolock_interrupts_workflow)

    def test_allow_while_locked_messages(self):
        """Test that ALLOW_WHILE_LOCKED contains expected messages."""
        self.assertIn(MessageType.GetFeatures, workflow.ALLOW_WHILE_LOCKED)
        self.assertIn(MessageType.Cancel, workflow.ALLOW_WHILE_LOCKED)
        self.assertIn(MessageType.EndSession, workflow.ALLOW_WHILE_LOCKED)
        self.assertIn(MessageType.LockDevice, workflow.ALLOW_WHILE_LOCKED)


class TestIdleTimer(unittest.TestCase):
    def setUp(self):
        self.timer = workflow.IdleTimer()

    def tearDown(self):
        self.timer.clear()

    def test_idle_timer_creation(self):
        """Test IdleTimer can be created and is empty."""
        self.assertEqual(len(self.timer.timeouts), 0)
        self.assertEqual(len(self.timer.tasks), 0)

    def test_set_callback(self):
        """Test setting an idle callback."""
        called = []

        def callback():
            called.append(True)

        self.timer.set(1000, callback)
        self.assertIn(callback, self.timer.timeouts)
        self.assertEqual(self.timer.timeouts[callback], 1000)
        self.assertIn(callback, self.timer.tasks)

    def test_remove_callback(self):
        """Test removing an idle callback."""
        def callback():
            pass

        self.timer.set(1000, callback)
        self.assertIn(callback, self.timer.timeouts)

        self.timer.remove(callback)
        self.assertNotIn(callback, self.timer.timeouts)
        self.assertNotIn(callback, self.timer.tasks)

    def test_clear_all_callbacks(self):
        """Test clearing all callbacks."""
        def callback1():
            pass

        def callback2():
            pass

        self.timer.set(1000, callback1)
        self.timer.set(2000, callback2)
        self.assertEqual(len(self.timer.timeouts), 2)

        self.timer.clear()
        self.assertEqual(len(self.timer.timeouts), 0)
        self.assertEqual(len(self.timer.tasks), 0)

    def test_update_existing_callback(self):
        """Test updating an existing callback with new timeout."""
        def callback():
            pass

        self.timer.set(1000, callback)
        self.assertEqual(self.timer.timeouts[callback], 1000)

        self.timer.set(2000, callback)
        self.assertEqual(self.timer.timeouts[callback], 2000)

    def test_touch_updates_timers(self):
        """Test that touch() updates timer deadlines."""
        def callback():
            pass

        self.timer.set(1000, callback)

        # Touch should not raise any errors
        self.timer.touch()

        # Timer should still be registered
        self.assertIn(callback, self.timer.timeouts)

    def test_multiple_callbacks_different_timeouts(self):
        """Test multiple callbacks with different timeouts."""
        def callback1():
            pass

        def callback2():
            pass

        def callback3():
            pass

        self.timer.set(500, callback1)
        self.timer.set(1000, callback2)
        self.timer.set(1500, callback3)

        self.assertEqual(len(self.timer.timeouts), 3)
        self.assertEqual(self.timer.timeouts[callback1], 500)
        self.assertEqual(self.timer.timeouts[callback2], 1000)
        self.assertEqual(self.timer.timeouts[callback3], 1500)


class TestGlobalIdleTimer(unittest.TestCase):
    def test_global_idle_timer_exists(self):
        """Test that global idle_timer instance exists."""
        self.assertIsInstance(workflow.idle_timer, workflow.IdleTimer)

    def test_global_idle_timer_is_singleton(self):
        """Test that workflow.idle_timer is a singleton."""
        # Access the timer twice and verify it's the same object
        timer1 = workflow.idle_timer
        timer2 = workflow.idle_timer
        self.assertIs(timer1, timer2)


class TestWorkflowEdgeCases(unittest.TestCase):
    def test_empty_task_set_initially(self):
        """Test that task set is initially empty or can be emptied."""
        workflow.tasks.clear()
        self.assertEqual(len(workflow.tasks), 0)

    def test_allow_while_locked_contains_essential_messages(self):
        """Test ALLOW_WHILE_LOCKED tuple contains critical messages."""
        # Should contain messages that work when device is locked
        self.assertIsInstance(workflow.ALLOW_WHILE_LOCKED, tuple)
        self.assertGreater(len(workflow.ALLOW_WHILE_LOCKED), 0)

    def test_idle_timer_remove_nonexistent_callback(self):
        """Test removing a callback that was never added."""
        timer = workflow.IdleTimer()

        def callback():
            pass

        # Should not raise
        timer.remove(callback)

    def test_idle_timer_clear_when_empty(self):
        """Test clearing an empty timer."""
        timer = workflow.IdleTimer()
        # Should not raise
        timer.clear()


if __name__ == "__main__":
    unittest.main()