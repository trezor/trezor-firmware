# Trezor Core event loop

The event loop is implemented in `src/trezor/loop.py` and forms the core of the
processing. At boot time, default tasks are started and inserted into an event queue.
Such task will usually run in an endless loop: wait for event, process event, loop back.

Application code is written with `async/await` constructs. Low level of the event queue
processes running coroutines via `coroutine.send()` and `coroutine.throw()` calls.

### MicroPython details

MicroPython does not distinguish between coroutines, awaitables, and generators. Some
low-level constructs are using `yield` and `yield from` constructions.

`async def` definition marks the function as a generator, even if it does not contain
`await` or `yield` expressions. It is thus possible to see `async def __iter__`, which
indicates that the function is a generator.

For type-checking purposes, objects usually define an `__await__` method that delegates
to `__iter__`. The `__await__` method is never executed, however.


## Low-level API

### Function summary

`loop.run()` starts the event loop. The call only returns when there are no further
waiting tasks -- so, in usual conditions, never.

`loop.schedule(task, value, deadline, finalizer, reschedule)` schedules an awaitable to
be run either as soon as possible, or at a specified time (given as a `deadline` in
microseconds since system bootup.)

In addition, when the task finishes processing or is closed externally, the `finalizer`
callback will be executed, with the task and the return value (or the raised exception)
as a parameter.

If `reschedule` is true, the task is first cleared from the scheduled queue -- in
effect, it is rescheduled to run at a different time.

`loop.close(task)` removes a previously scheduled task from the list of waiting tasks
and calls its finalizer.

`loop.pause(task, interface)` sets the task as waiting for a particular _interface_:
either reading from or writing to one of the USB interfaces, or waiting for a touch
event.

### Implementation details

Trezor Core runs coroutine-based cooperative multitasking, i.e., there is no preemption.

Every _task_ is a coroutine, which means that it runs uninterrupted until it yields a
value (or, in async terms, until it awaits something). In every processing step, the
currently selected coroutine is resumed by sending a value to it (which is returned as a
result of the yield/await, or raised as an exception if it is an instance of
`BaseException`). The tasks then runs uninterrupted again, until it yields or exits.

A loop in `loop.run()` spins for as long as any tasks are waiting. Two lists of waiting
tasks exist:

-   `_queue` is a priority queue where the ordering is defined by real-time deadlines.
    In most cases, tasks are scheduled for "now", which makes them run one after another
    in FIFO order. It is also possible to schedule a task to run in the future.

-   `_paused` is a collection of tasks grouped by the interface for which they are
    waiting.

In each run of the loop, `io.poll` is called to query I/O events. If an event arrives on
an interface, _all_ tasks waiting on that interface are resumed one after another. No
scheduled tasks in `_queue` can execute until the waiting tasks yield again.

At most one I/O event is processsed in this phase.

When the I/O phase is done, a task with the highest priority is popped from `_queue` and
resumed.

### I/O wait

When no tasks are paused on a given interface, events on that interface remain in queue.

When multiple tasks are paused on the same interface, all of them receive every event.
However, a waiting task receives at most one event. To receive more, it must pause
itself again. Event processing is usually done in an endless loop with a pause call.

If two tasks are attempting to read from the same interface, and one of them re-pauses
itself immediately while the other doesn't (possibly due to use of `loop.race`, which
introduces scheduling gaps), the other task might lose some events.

For this reason, you should avoid waiting on the same interface from multiple tasks.

### Syscalls

Syscalls bridge the gap between `await`-based application code and the coroutine-based
low-level implementation.

Every sequence of `await`s will at some point boil down to yielding a `Syscall`
instance. (Yielding anything else is an error.) When that happens, control returns to
the event loop.

The `handle(task)` method is called on the result. This way the syscall gets hold of the
task object, and can `schedule()` or `pause()` it as appropriate.

As an example, consider pausing on an input event. A running task has no way to call
`pause()` _on itself_. It would need to pass a separate function as a callback.

The `wait` syscall can be implemented as a simple wrapper around the `pause()` low-level
call:

```python
class wait(Syscall):
    def __init__(self, msg_iface: int) -> None:
        self.msg_iface = msg_iface

    def handle(self, task: Task) -> None:
        pause(task, self.msg_iface)
```

The `__init__()` method takes all the arguments of the "call", and `handle()` pauses the
task on the given interface.

Calling code will look like this:
```python
event = await loop.wait(io.TOUCH)
```
The `loop.wait(io.TOUCH)` expression instantiates a new `Syscall` object. The argument
is passed to the constructor, and stored on the instance. The rest boils down to
```python
event = await some_syscall_instance
```
which is equivalent to
```python
event = yield from some_syscall_instance.__iter__()
```
The `Syscall.__iter__()` method yields `self`, returning control to the event loop. The
event loop invokes `some_syscall_instance.handle(task_object)`. The `task_object` is
then set to resume when a touch event arrives.

A side-effect of this design is that it is possible to store and reuse syscall
instances. That can be advantageous for avoiding unnecessary allocations.
```python
while True:
    # every run of the loop allocates a new object
    event = await loop.wait(io.TOUCH)
    process_event(event)

touch_source = loop.wait(io.TOUCH)
while True:
    # same instance is reused
    event = await touch_source
    process_event(event)
```

## High-level API

Application code should not be using any of the above low-level functions. Awaiting
syscalls is the preferred method of writing code.

The following syscalls and constructs are available:

**`loop.sleep(delay_ms: int)`**: Suspend execution until the given delay (in
milliseconds) elapses. Return value is the planned deadline in milliseconds since system
start.

Calling `await loop.sleep(0)` yields execution to other tasks, and schedules the current
task for the next tick.

**`loop.wait(interface)`**: Wait indefinitely for an event on the given interface.
Return value is the event.

_Upcoming code modification adds a timeout parameter to `loop.wait`._

**`loop.race(*children)`**: Schedule each argument to run, and suspend execution until
the first of them finishes.

It is possible to specify wait timeout for `loop.wait` by using `loop.race`:
```python
result = await loop.race(loop.wait(io.TOUCH), loop.sleep(1000))
```
This introduces scheduling gaps: every child is treated as a task and scheduled
to run. This means that if the child is a syscall, as in the above example, its action
is not done immediately. Instead, the `wait` begins on the next tick (or whenever the
newly created coroutine runs) and the `sleep` in the tick afterwards. When nesting
multiple `race`s, the child `races` also run later.

Also, when a child task is done, another scheduling gap happens, and the parent task
is scheduled to run on the next tick.

_Upcoming changes may solve this in relevant cases, by inlining syscall operations._

**`loop.spawn(task)`**: Start the task asynchronously. Return an object that allows
the caller to await its result, or shut the task down.

Example usage:
```python
task = loop.spawn(some_background_task())
await do_something_here()
result = await task
```

Unlike other syscalls, `loop.spawn` starts the task at instantiation time. `await`ing
the same `loop.spawn` instance a second time will immediately return the result of the
original run.

If the task is cancelled (usually by calling `task.close()`), the awaiter receives a
`loop.TaskClosed` exception.

It is also possible to register a synchronous finalizer callback via
`task.set_finalizer`. This is used internally to implement workflow management.

**`loop.chan()`** is a unidirectional communication channel that actually implements two
syscalls:

 * **`chan.put()`** sends a value to the channel, and waits until it is picked up
   by a taker task.
 * **`chan.take()`** waits until a value is sent to the channel and then returns it.

It is possible to put in a value without waiting for a taker, by calling
`chan.publish()`. It is not possible to take a value without waiting.
