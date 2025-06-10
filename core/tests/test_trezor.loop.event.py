# flake8: noqa: F403,F405
from common import *  # isort:skip

from trezor import loop

RESULT = object()


class TestLoopEvent(unittest.TestCase):
    def test_set(self):
        event = loop.event()
        self.assertFalse(event.is_set())
        # make sure setting the result works as intended
        event.set(RESULT)
        self.assertTrue(event.is_set())

        # test short-circuit path: return result without blocking
        with self.assertRaises(StopIteration) as exc:
            event.__iter__().send(None)

        self.assertIs(exc.value.value, RESULT)

    def test_wait_once(self):
        event = loop.event()
        self.assertFalse(event.is_set())

        # event is not set: nothing changes
        gen = event.__iter__().send(None)
        self.assertIs(gen, event)

        # now it is set: return result without blocking
        event.set(RESULT)
        with self.assertRaises(StopIteration) as exc:
            event.__iter__().send(None)

        self.assertIs(exc.value.value, RESULT)

    def test_handle_callback(self):
        event = loop.event()
        self.assertFalse(event.is_set())

        step = 0

        async def task():
            nonlocal step
            step = 1
            result = await event
            self.assertIs(result, RESULT)
            step = 2

        gen = task()
        self.assertEqual(step, 0)
        # start task and make sure it's blocked on `await`
        self.assertIs(event, gen.send(None))
        self.assertEqual(step, 1)
        # register the task as event's callback
        self.assertIs(event.callback, None)
        event.handle(gen)
        self.assertIs(event.callback, gen)
        self.assertEqual(step, 1)
        self.assertFalse(event.is_set())
        # set result and make sure the task has finished
        event.set(RESULT)
        self.assertEqual(step, 2)

    def test_handle_no_callback(self):
        event = loop.event()
        self.assertFalse(event.is_set())

        step = 0

        async def task():
            nonlocal step
            step = 1
            result = await event
            self.assertIs(result, RESULT)
            step = 2

        gen = task()
        self.assertEqual(step, 0)
        # start task and make sure it's blocked on `await`
        self.assertIs(event, gen.send(None))
        self.assertEqual(step, 1)
        self.assertIs(event.callback, None)
        self.assertFalse(event.is_set())
        # set the event and make sure the task is still blocked (without callback)
        event.set(RESULT)
        self.assertIs(event.callback, None)
        self.assertEqual(step, 1)
        self.assertTrue(event.is_set())
        # handle the event, make sure the task has finished (without callback)
        event.handle(gen)
        self.assertIs(event.callback, None)
        self.assertEqual(step, 2)
        self.assertTrue(event.is_set())


if __name__ == "__main__":
    unittest.main()
