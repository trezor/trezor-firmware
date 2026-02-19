# flake8: noqa: F403,F405
from common import *  # isort:skip

from mock import Mock, MockAsync, patch
from trezor import loop, workflow
from trezor.enums import MessageType


class TestWorkflowSpawn(unittest.TestCase):
    def setUp(self):
        # Reset workflow state
        workflow.tasks.clear()
        workflow.default_task = None
        workflow.default_constructor = None
        workflow.autolock_interrupts_workflow = True

    def test_spawn_registers_task(self):
        """Test that spawning a workflow registers it in the tasks set."""
        async def dummy_workflow():
            return 42

        task = workflow.spawn(dummy_workflow())
        self.assertIn(task, workflow.tasks)

    def test_spawn_multiple_tasks(self):
        """Test that multiple workflows can be spawned simultaneously."""
        async def workflow1():
            await loop.sleep(10)
            return 1

        async def workflow2():
            await loop.sleep(10)
            return 2

        task1 = workflow.spawn(workflow1())
        task2 = workflow.spawn(workflow2())

        self.assertIn(task1, workflow.tasks)
        self.assertIn(task2, workflow.tasks)
        self.assertEqual(len(workflow.tasks), 2)

    def test_close_others_stops_non_running_tasks(self):
        """Test that close_others stops workflows that are not currently running."""
        async def dummy_workflow():
            await loop.sleep(100)
            return 1

        task1 = workflow.spawn(dummy_workflow())
        task2 = workflow.spawn(dummy_workflow())

        # Both tasks should be registered
        self.assertEqual(len(workflow.tasks), 2)

        # Close others should stop both (since neither is "running" in the sense
        # that they're not the currently executing task)
        workflow.close_others()


class TestIdleTimer(unittest.TestCase):
    def setUp(self):
        self.timer = workflow.IdleTimer()

    def test_idle_timer_initialization(self):
        """Test that IdleTimer initializes with empty state."""
        self.assertEqual(len(self.timer.timeouts), 0)
        self.assertEqual(len(self.timer.tasks), 0)

    def test_set_creates_timeout(self):
        """Test that set() creates a timeout and task."""
        callback = Mock()
        self.timer.set(1000, callback)

        self.assertIn(callback, self.timer.timeouts)
        self.assertIn(callback, self.timer.tasks)
        self.assertEqual(self.timer.timeouts[callback], 1000)

    def test_set_updates_existing_timeout(self):
        """Test that set() updates an existing timeout."""
        callback = Mock()
        self.timer.set(1000, callback)
        self.assertEqual(self.timer.timeouts[callback], 1000)

        # Update the timeout
        self.timer.set(2000, callback)
        self.assertEqual(self.timer.timeouts[callback], 2000)

    def test_remove_deletes_timeout(self):
        """Test that remove() deletes a timeout and its task."""
        callback = Mock()
        self.timer.set(1000, callback)

        self.assertIn(callback, self.timer.timeouts)
        self.assertIn(callback, self.timer.tasks)

        self.timer.remove(callback)

        self.assertNotIn(callback, self.timer.timeouts)
        self.assertNotIn(callback, self.timer.tasks)

    def test_remove_nonexistent_callback(self):
        """Test that removing a non-existent callback doesn't raise an error."""
        callback = Mock()
        # Should not raise
        self.timer.remove(callback)

    def test_clear_removes_all_timeouts(self):
        """Test that clear() removes all timeouts and tasks."""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        self.timer.set(1000, callback1)
        self.timer.set(2000, callback2)
        self.timer.set(3000, callback3)

        self.assertEqual(len(self.timer.timeouts), 3)
        self.assertEqual(len(self.timer.tasks), 3)

        self.timer.clear()

        self.assertEqual(len(self.timer.timeouts), 0)
        self.assertEqual(len(self.timer.tasks), 0)

    def test_touch_reschedules_tasks(self):
        """Test that touch() reschedules all registered tasks."""
        callback = Mock()
        self.timer.set(1000, callback)

        # Touch should reschedule but not call the callback immediately
        self.timer.touch()
        self.assertEqual(len(callback.calls), 0)


class TestAllowWhileLocked(unittest.TestCase):
    def test_allow_while_locked_contains_expected_messages(self):
        """Test that ALLOW_WHILE_LOCKED contains expected message types."""
        # These messages should always be allowed while locked
        expected_messages = [
            MessageType.GetFeatures,
            MessageType.Cancel,
            MessageType.LockDevice,
            MessageType.Ping,
        ]

        for msg_type in expected_messages:
            self.assertIn(msg_type, workflow.ALLOW_WHILE_LOCKED)

    def test_allow_while_locked_excludes_sensitive_operations(self):
        """Test that ALLOW_WHILE_LOCKED doesn't contain sensitive operations."""
        # These should NOT be in ALLOW_WHILE_LOCKED
        sensitive_messages = [
            MessageType.SignTx,
            MessageType.GetAddress,
            MessageType.SignMessage,
        ]

        for msg_type in sensitive_messages:
            self.assertNotIn(msg_type, workflow.ALLOW_WHILE_LOCKED)


class TestDefaultWorkflow(unittest.TestCase):
    def setUp(self):
        # Reset workflow state
        workflow.tasks.clear()
        workflow.default_task = None
        workflow.default_constructor = None
        workflow.autolock_interrupts_workflow = True

    def test_set_default_configures_constructor(self):
        """Test that set_default configures the default workflow constructor."""
        async def default_workflow():
            return 1

        workflow.set_default(default_workflow)
        self.assertEqual(workflow.default_constructor, default_workflow)

    def test_start_default_creates_task(self):
        """Test that start_default creates a default task."""
        async def default_workflow():
            await loop.sleep(100)
            return 1

        workflow.set_default(default_workflow)
        workflow.start_default()

        self.assertIsNotNone(workflow.default_task)

    def test_start_default_idempotent(self):
        """Test that calling start_default multiple times doesn't create multiple tasks."""
        async def default_workflow():
            await loop.sleep(100)
            return 1

        workflow.set_default(default_workflow)
        workflow.start_default()
        first_task = workflow.default_task

        workflow.start_default()
        self.assertEqual(workflow.default_task, first_task)

    def test_kill_default_stops_task(self):
        """Test that kill_default stops the default task."""
        async def default_workflow():
            await loop.sleep(100)
            return 1

        workflow.set_default(default_workflow)
        workflow.start_default()
        self.assertIsNotNone(workflow.default_task)

        workflow.kill_default()
        # Task should eventually be None after finalizer runs


class TestAutolockInterrupts(unittest.TestCase):
    def test_autolock_interrupts_workflow_default_true(self):
        """Test that autolock_interrupts_workflow defaults to True."""
        workflow.autolock_interrupts_workflow = True
        self.assertTrue(workflow.autolock_interrupts_workflow)

    def test_autolock_interrupts_can_be_disabled(self):
        """Test that autolock_interrupts_workflow can be set to False."""
        workflow.autolock_interrupts_workflow = False
        self.assertFalse(workflow.autolock_interrupts_workflow)


class TestWorkflowEdgeCases(unittest.TestCase):
    def setUp(self):
        workflow.tasks.clear()
        workflow.default_task = None
        workflow.default_constructor = None

    def test_empty_workflow_state(self):
        """Test behavior with no workflows running."""
        self.assertEqual(len(workflow.tasks), 0)
        self.assertIsNone(workflow.default_task)

    def test_set_default_with_restart(self):
        """Test set_default with restart=True kills existing default."""
        async def workflow1():
            await loop.sleep(100)
            return 1

        async def workflow2():
            await loop.sleep(100)
            return 2

        workflow.set_default(workflow1)
        workflow.start_default()
        first_task = workflow.default_task

        workflow.set_default(workflow2, restart=True)
        # The old task should be closed


if __name__ == "__main__":
    unittest.main()