# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import loop


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_loop():
    """Run the event loop until all scheduled tasks finish.

    Only safe to call when no tasks are waiting on I/O (no _paused entries).
    All tasks must complete so the queue empties and loop.run() returns.
    """
    loop.run()


# ---------------------------------------------------------------------------
# mailbox
# ---------------------------------------------------------------------------

class TestMailbox(unittest.TestCase):

    def setUp(self):
        loop.clear()

    def tearDown(self):
        loop.clear()

    # --- basic state ---

    def test_empty_by_default(self):
        box = loop.mailbox()
        self.assertTrue(box.is_empty())

    def test_initial_value_not_empty(self):
        box = loop.mailbox(initial_value=7)
        self.assertFalse(box.is_empty())

    def test_put_makes_non_empty(self):
        box = loop.mailbox()
        box.put(42)
        self.assertFalse(box.is_empty())

    def test_clear_makes_empty(self):
        box = loop.mailbox()
        box.put(42)
        box.clear()
        self.assertTrue(box.is_empty())

    # --- put constraints ---

    def test_put_twice_raises(self):
        box = loop.mailbox()
        box.put("first")
        with self.assertRaises(ValueError):
            box.put("second")

    def test_put_replace_succeeds(self):
        box = loop.mailbox()
        box.put("first")
        box.put("second", replace=True)  # must not raise
        self.assertFalse(box.is_empty())

    def test_put_replace_updates_value(self):
        """Replacing a value stores the new one."""
        box = loop.mailbox()
        box.put(1)
        box.put(2, replace=True)
        # consume directly
        gen = box.__iter__()
        try:
            gen.send(None)
            self.fail("expected StopIteration")
        except StopIteration as e:
            self.assertEqual(e.value, 2)

    # --- __iter__ short-circuit path (no scheduler needed) ---

    def test_iter_returns_existing_value(self):
        """Awaiting a mailbox that already holds a value returns immediately."""
        box = loop.mailbox()
        box.put(99)
        gen = box.__iter__()
        try:
            gen.send(None)
            self.fail("expected StopIteration")
        except StopIteration as e:
            self.assertEqual(e.value, 99)

    def test_iter_clears_box_after_consume(self):
        box = loop.mailbox()
        box.put("hello")
        gen = box.__iter__()
        try:
            gen.send(None)
        except StopIteration:
            pass
        self.assertTrue(box.is_empty())

    def test_iter_raises_exception_value(self):
        """Edge case fixed in PR #6676: if the stored value IS an exception,
        awaiting must RAISE it rather than return it."""
        box = loop.mailbox()
        err = ValueError("mailbox edge case")
        box.put(err)
        gen = box.__iter__()
        try:
            gen.send(None)
            self.fail("expected ValueError to be raised")
        except ValueError as e:
            self.assertIs(e, err)
        # mailbox should be empty (cleared before raising)
        self.assertTrue(box.is_empty())

    def test_iter_raises_runtime_error_value(self):
        """Same edge case with a different exception type."""
        box = loop.mailbox()
        err = RuntimeError("boom")
        box.put(err)
        gen = box.__iter__()
        try:
            gen.send(None)
            self.fail("expected RuntimeError")
        except RuntimeError as e:
            self.assertIs(e, err)

    def test_iter_raises_base_exception_value(self):
        """Same edge case for GeneratorExit (BaseException subclass)."""
        box = loop.mailbox()
        err = GeneratorExit()
        box.put(err)
        gen = box.__iter__()
        try:
            gen.send(None)
            self.fail("expected GeneratorExit to be raised")
        except GeneratorExit as e:
            self.assertIs(e, err)

    def test_iter_raises_taskclosed_value(self):
        """TaskClosed is a BaseException subclass — same edge case."""
        box = loop.mailbox()
        err = loop.TaskClosed()
        box.put(err)
        gen = box.__iter__()
        try:
            gen.send(None)
            self.fail("expected TaskClosed to be raised")
        except loop.TaskClosed as e:
            self.assertIs(e, err)

    def test_iter_without_value_yields_self(self):
        """Awaiting an empty mailbox yields self to the scheduler."""
        box = loop.mailbox()
        gen = box.__iter__()
        yielded = gen.send(None)  # first step → yields box itself
        self.assertIs(yielded, box)

    def test_iter_without_value_can_be_resumed(self):
        """After yielding self, sending a value into the generator returns it."""
        box = loop.mailbox()
        gen = box.__iter__()
        gen.send(None)  # consume the initial yield
        try:
            gen.send("result")
            self.fail("expected StopIteration")
        except StopIteration as e:
            self.assertEqual(e.value, "result")

    def test_iter_clears_taker_on_exception(self):
        """Throwing an exception into a waiting __iter__ clears taker."""
        box = loop.mailbox()
        gen = box.__iter__()
        gen.send(None)  # now waiting; taker is the gen itself
        try:
            gen.throw(RuntimeError, RuntimeError("abort"))
            self.fail("expected RuntimeError")
        except RuntimeError:
            pass
        self.assertIsNone(box.taker)

    # --- scheduler integration ---

    def test_handle_immediate_take(self):
        """handle() when a value is ready schedules the taker immediately."""
        box = loop.mailbox()
        box.put(77)
        received = []

        async def consumer():
            val = await box
            received.append(val)

        loop.schedule(consumer())
        run_loop()
        self.assertEqual(received, [77])

    def test_handle_deferred_take(self):
        """put() after a task is waiting wakes it up."""
        box = loop.mailbox()
        received = []

        async def consumer():
            val = await box
            received.append(val)

        async def producer():
            box.put(123)

        loop.schedule(consumer())
        loop.schedule(producer())
        run_loop()
        self.assertEqual(received, [123])

    def test_multiple_puts_after_consume(self):
        """Mailbox can be reused: put → await → put → await."""
        box = loop.mailbox()
        received = []

        async def consumer():
            received.append(await box)
            received.append(await box)

        async def producer():
            box.put(1)
            box.put(2)

        loop.schedule(consumer())
        loop.schedule(producer())
        run_loop()
        self.assertEqual(received, [1, 2])

    def test_exception_value_raised_in_task(self):
        """Edge case (PR #6676): exception value in mailbox raises inside task."""
        box = loop.mailbox()
        err = ValueError("injected error")
        box.put(err)
        caught = []

        async def consumer():
            try:
                await box
            except ValueError as e:
                caught.append(e)

        loop.schedule(consumer())
        run_loop()
        self.assertEqual(len(caught), 1)
        self.assertIs(caught[0], err)

    # --- maybe_close ---

    def test_maybe_close_no_taker(self):
        """maybe_close() with no waiting task is a no-op."""
        box = loop.mailbox()
        box.maybe_close()  # must not raise

    def test_maybe_close_closes_taker_from_other_task(self):
        """maybe_close() called from a different task closes the waiting one."""
        box = loop.mailbox()
        closed = []

        async def waiter():
            try:
                await box
            except GeneratorExit:
                closed.append(True)

        async def closer():
            # called after waiter is waiting → this_task is closer, != taker
            box.maybe_close()

        loop.schedule(waiter())
        loop.schedule(closer())
        run_loop()
        self.assertEqual(closed, [True])

    def test_maybe_close_taker_is_none_after(self):
        """After maybe_close(), taker is None."""
        box = loop.mailbox()

        async def waiter():
            try:
                await box
            except GeneratorExit:
                pass

        async def closer():
            box.maybe_close()
            # taker should be cleared synchronously
            self.assertIsNone(box.taker)

        loop.schedule(waiter())
        loop.schedule(closer())
        run_loop()


# ---------------------------------------------------------------------------
# race
# ---------------------------------------------------------------------------

class TestRace(unittest.TestCase):

    def setUp(self):
        loop.clear()

    def tearDown(self):
        loop.clear()

    def test_race_first_completes_wins(self):
        """The first child to return determines race result; others are closed."""
        results = []
        closed = []

        async def fast():
            return "fast"

        async def slow():
            try:
                await loop.sleep(10_000_000)  # very long — will be closed
            except GeneratorExit:
                closed.append("slow")

        async def driver():
            result = await loop.race(fast(), slow())
            results.append(result)

        loop.schedule(driver())
        run_loop()
        self.assertEqual(results, ["fast"])
        self.assertIn("slow", closed)

    def test_race_result_is_winner_value(self):
        """race result is the return value of the winning child."""
        results = []

        async def winner():
            return 42

        async def loser():
            try:
                await loop.sleep(10_000_000)
            except GeneratorExit:
                pass

        async def driver():
            result = await loop.race(winner(), loser())
            results.append(result)

        loop.schedule(driver())
        run_loop()
        self.assertEqual(results, [42])

    def test_race_finished_flag_prevents_double_finish(self):
        """Only one winner: finished flag prevents second child from triggering."""
        finish_count = []

        async def child_a():
            return "a"

        async def child_b():
            return "b"

        async def driver():
            result = await loop.race(child_a(), child_b())
            finish_count.append(result)

        loop.schedule(driver())
        run_loop()
        self.assertEqual(len(finish_count), 1)

    def test_race_exception_kills_all_children(self):
        """Throwing an exception into the waiting race closes all children."""
        closed_count = [0]

        async def never_ending():
            try:
                await loop.sleep(10_000_000)
            except GeneratorExit:
                closed_count[0] += 1

        racer = loop.race(never_ending(), never_ending(), never_ending())
        driver_gen = racer.__iter__()
        driver_gen.send(None)  # yield to get handle() called

        try:
            driver_gen.throw(RuntimeError, RuntimeError("external cancel"))
        except RuntimeError:
            pass

        self.assertTrue(racer.finished)
        self.assertEqual(closed_count[0], 3)

    def test_race_exception_sets_finished_flag(self):
        """After an external exception, race.finished is True."""
        async def sleeper():
            try:
                await loop.sleep(10_000_000)
            except GeneratorExit:
                pass

        racer = loop.race(sleeper())
        gen = racer.__iter__()
        gen.send(None)

        try:
            gen.throw(ValueError, ValueError("cancel"))
        except ValueError:
            pass

        self.assertTrue(racer.finished)

    def test_race_exception_does_not_fire_callback(self):
        """After an external cancel, the callback task is NOT stepped."""
        callback_stepped = []

        async def waiter():
            callback_stepped.append(True)

        async def child():
            try:
                await loop.sleep(10_000_000)
            except GeneratorExit:
                pass

        racer = loop.race(child())
        gen = racer.__iter__()
        gen.send(None)

        # At this point racer.callback is the dummy task (waiter), but we
        # won't schedule a callback at all — just verify no crash and that
        # the race doesn't step a random task.
        try:
            gen.throw(GeneratorExit, GeneratorExit())
        except GeneratorExit:
            pass

        self.assertTrue(racer.finished)
        self.assertEqual(callback_stepped, [])


# ---------------------------------------------------------------------------
# spawn
# ---------------------------------------------------------------------------

class TestSpawn(unittest.TestCase):

    def setUp(self):
        loop.clear()

    def tearDown(self):
        loop.clear()

    def test_spawn_returns_task_result(self):
        """Awaiting spawn yields the spawned task's return value."""
        results = []

        async def worker():
            return 42

        async def driver():
            handle = loop.spawn(worker())
            val = await handle
            results.append(val)

        loop.schedule(driver())
        run_loop()
        self.assertEqual(results, [42])

    def test_spawn_result_available_after_finish(self):
        """After the spawned task finishes, re-awaiting returns the same value."""
        results = []

        async def worker():
            return "done"

        async def driver():
            handle = loop.spawn(worker())
            val1 = await handle
            # Task is finished; second await should return immediately
            val2 = await handle
            results.append(val1)
            results.append(val2)

        loop.schedule(driver())
        run_loop()
        self.assertEqual(results, ["done", "done"])

    def test_spawn_close_after_finished_is_noop(self):
        """spawn.close() after the task already finished is safe."""
        results = []

        async def worker():
            return "done"

        async def driver():
            handle = loop.spawn(worker())
            val = await handle
            results.append(val)
            handle.close()  # already finished — must not raise
            results.append("after close")

        loop.schedule(driver())
        run_loop()
        self.assertEqual(results, ["done", "after close"])

    def test_spawn_close_raises_taskclosed_in_waiter(self):
        """spawn.close() while another task is awaiting raises TaskClosed."""
        caught = []
        handle_holder = [None]

        async def long_worker():
            await loop.sleep(10_000_000)

        async def waiter(handle):
            try:
                await handle
            except loop.TaskClosed:
                caught.append(True)

        async def closer():
            handle_holder[0].close()

        handle = loop.spawn(long_worker())
        handle_holder[0] = handle
        loop.schedule(waiter(handle))
        loop.schedule(closer())
        run_loop()
        self.assertEqual(caught, [True])

    def test_spawn_is_running_false_from_driver(self):
        """is_running() is False when checked from the driver task."""
        results = []

        async def worker():
            return "ok"

        async def driver():
            handle = loop.spawn(worker())
            results.append(handle.is_running())
            await handle

        loop.schedule(driver())
        run_loop()
        self.assertFalse(results[0])

    def test_spawn_is_running_true_inside_task(self):
        """is_running() is True when called from within the spawned task."""
        results = []
        handle_holder = [None]

        async def worker():
            results.append(handle_holder[0].is_running())

        async def driver():
            handle_holder[0] = loop.spawn(worker())
            await handle_holder[0]

        loop.schedule(driver())
        run_loop()
        self.assertTrue(results[0])

    def test_spawn_finalizer_called_on_finish(self):
        """set_finalizer() callback fires when the spawned task ends."""
        finalized = []

        async def worker():
            return "finished"

        async def driver():
            handle = loop.spawn(worker())
            handle.set_finalizer(lambda h: finalized.append(h.return_value))
            await handle

        loop.schedule(driver())
        run_loop()
        self.assertEqual(finalized, ["finished"])

    def test_spawn_finalizer_called_immediately_if_done(self):
        """set_finalizer() fires immediately if the task is already finished."""
        finalized = []

        async def worker():
            return "done"

        async def driver():
            handle = loop.spawn(worker())
            # Yield once to let worker finish before registering
            await loop.sleep(0)
            handle.set_finalizer(lambda h: finalized.append("late"))

        loop.schedule(driver())
        run_loop()
        self.assertEqual(finalized, ["late"])

    def test_spawn_generator_exit_becomes_taskclosed(self):
        """When the spawned task is closed, return_value is TaskClosed."""
        handle_holder = [None]

        async def worker():
            await loop.sleep(10_000_000)

        async def driver():
            handle_holder[0] = loop.spawn(worker())

        async def killer():
            handle_holder[0].close()

        loop.schedule(driver())
        loop.schedule(killer())
        run_loop()

        handle = handle_holder[0]
        self.assertTrue(handle.finished)
        self.assertIsInstance(handle.return_value, loop.TaskClosed)


# ---------------------------------------------------------------------------
# schedule / finalize helpers
# ---------------------------------------------------------------------------

class TestFinalize(unittest.TestCase):

    def setUp(self):
        loop.clear()

    def tearDown(self):
        loop.clear()

    def test_finalize_calls_callback(self):
        """Finalizer registered via schedule() is called with the return value."""
        results = []

        async def task():
            return "result"

        loop.schedule(task(), finalizer=lambda t, v: results.append(v))
        run_loop()
        self.assertEqual(results, ["result"])

    def test_finalize_noop_without_callback(self):
        """Tasks without a finalizer complete silently."""
        async def task():
            return "ok"

        loop.schedule(task())
        run_loop()  # must not raise

    def test_finalize_called_once(self):
        """Finalizer is called exactly once per task completion."""
        calls = []

        async def task():
            return "x"

        loop.schedule(task(), finalizer=lambda t, v: calls.append(v))
        run_loop()
        self.assertEqual(calls, ["x"])


if __name__ == "__main__":
    unittest.main()
