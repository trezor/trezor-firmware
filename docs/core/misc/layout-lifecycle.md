# UI Layout Lifecycle

## Overview

There can be at most one UI layout running. The running layout is stored in
`ui.CURRENT_LAYOUT`. The value of this attribute must only be managed internally by the
layout objects themselves.

There are two kinds of layouts. The `Layout` class represents the normal kind of layout
which can accept user interaction or timer events. Such layout can return a _result_
of the interaction, retrievable from the `Layout.get_result()` async method. Typically,
calling code will block on an `await` for the result.

`ProgressLayout` represents loaders for long-running operations. It does not respond to
events and cannot return a result. Calling code will start the progress layout in the
background, call to it to update progress via `ProgressLayout.report()`, and then stop
it when done.

## Individual layout lifecycle

A newly created layout object is in **READY** state. It does not accept events, has no
background tasks, does not draw on screen.

When started, it moves into **RUNNING** state. It is drawn on screen (with backlight
on), accepts events, and runs background tasks. The value of `ui.CURRENT_LAYOUT` is set
to the running layout object.

(This implies that at most one layout can be in **RUNNING** state.)

Layout in **RUNNING** state may stop and return a result, either in response to a user
interaction event (touch, button click, USB) or an internal timer firing. This moves it
into a **STOPPED** state. It is no longer shown on screen (backlight is off unless
another layout turns it on again), does not accept events, and does not run background
tasks.

A layout in a **STOPPED** state has a **result** value, available for pickup by awaiting
`get_result()`.

Stopping a layout before returning a result, or retrieving a result of a **STOPPED**
layout, will move it back to **READY** state.

### State transitions

```
+-------+    start()   +-----------+    <event>    +-----------+
| READY | -----------> |  RUNNING  | ------------> |  STOPPED  |
+-------+              +-----------+               +-----------+
  ^   ^                      |                           |
  |   |                      |                           |
  |   +------- stop() -------+                           |
  |                                                      |
  +--------------------- get_result() -------------------+
```

Calling `start()` checks if other layout is running, and if it is, stops it first. Then
it performs the setup and moves layout into **RUNNING** state.

(At most one layout can be in **RUNNING** state at one time. That means that before
a layout moves to **RUNNING**, the previously running layout must move out.)

When layout is in **RUNNING** state, calling `start()` is a no-op. When layout is in
**STOPPED** state, calling `start()` fails an assertion.

After `start()` returns, the layout is in **RUNNING** state. It will stay in this state
until it returns a result, or is stopped.

Calling `stop()` on a **READY** or **STOPPED** layout is a no-op. Calling `stop()` on a
**RUNNING** layout will shut down any tasks waiting on the layout's result, and move to
**READY** state.

After `stop()` returns, the layout is not in **RUNNING** state and the current layout is
no longer this layout.

Awaiting `get_result()` will resume the lifecycle from its current stage, that is:

* in **READY** state, starts the layout and waits for its result
* in **RUNNING** state, waits for the result
* in **STOPPED** state, returns the result

After `get_result()` returns, the layout is in **READY** state.

All state transitions are synchronous -- so, in terms of trezor-core's cooperative
multitasking, effectively atomic.

## Global layout lifecycle

When Trezor boots, `ui.CURRENT_LAYOUT is None`. The screen backlight is on and displays
the "filled lock" welcome screen with model name.

When a layout is started, the backlight is turned on and the layout is drawn on screen.
`ui.CURRENT_LAYOUT` is the instance of the layout.

When a layout is stopped, the backlight is turned off and `ui.CURRENT_LAYOUT` is set to
`None`.

Between two different layouts, there is always an interval where backlight is off and
the value of `ui.CURRENT_LAYOUT` is `None`. This state may not be visible from the
outside; it is possible to synchronously go from `A -> None -> B`. However, there MUST
be a `None` inbetween in all cases.

## Button requests

A `ButtonRequest` MUST be sent while the corresponding layout is already in **RUNNING**
state. That is, in particular, the value of `ui.CURRENT_LAYOUT` is of the corresponding
layout.

The best choice is to always use the `interact()` function to take care of
`ButtonRequest`s. Explicitly sending `ButtonRequest`s is not supported.

## Debuglink

We assume that only one caller is using the debuglink and that debuglink commands are
strongly ordered on the caller side. On the firmware side, we impose strong ordering on
the received debuglink calls based on the time of arrival.

There are two layout-relevant debuglink commands.

### `DebugLinkDecision`

Caller can send a decision to the **RUNNING** layout. This injects an event into the
layout. In response, the layout can move to a **STOPPED** state.

A next debug command is read only after a `DebugLinkDecision` is fully processed. This
means that:

* if the decision caused the layout to stop, subsequent debug commands will be received
  by the next layout up, and
* if the decision did not cause the layout to stop, subsequent debug commands will be
  received by the same layout.

### `DebugLinkGetState`

Caller can read the contents of the **RUNNING** layout.

There are three available waiting behaviors:

* `IMMEDIATE` (default) returns the contents of the layout that is currently
  **RUNNING**, or empty response if no layout is running.
* `NEXT_LAYOUT` waits for the layout to change before returning. If no layout is
  running, waits until one is started and returns its contents. If a layout is running,
  waits until it shuts down and a new one appears.
* `CURRENT_LAYOUT` waits until a layout is running and returns its contents. If no
  layout is running, the behavior is the same as `NEXT_LAYOUT`. If a layout is running,
  the behavior is the same as `IMMEDIATE`.

When received after a `ButtonRequest` has been sent, the modes guarantee the following:

* `IMMEDIATE` and `CURRENT_LAYOUT`: return the contents of the layout corresponding to
  the button request (unless the layout has already been terminated by a timer event or
  user interaction, in which case the result is undefined).
* `NEXT_LAYOUT`: waits until the layout corresponding to `ButtonRequest` changes.

When received after a `DebugLinkDecision` has been received, the behavior is:

* `IMMEDIATE`: If the layout did not shut down (e.g., when paginating), returns the
  contents of the layout as modified by the decision. If the layout shut down, the
  result is not guaranteed.
* `CURRENT_LAYOUT`: Returns the layout that is the result of the decision.
* `NEXT_LAYOUT`: No guarantees.

While `DebugLinkGetState` is waiting, **no other debug commands are processed**. In
particular, it is impossible to start waiting and then send a `DebugLinkDecision` to
cause the layout to change. Doing so will result in a deadlock.

(TODO it _might_ be possible to lift this restriction.)

If a layout is shut down by a `DebugLinkDecision`, and the firmware expects more
messages, a new layout might not come up until those messages are exchanged. Calling
`DebugLinkGetState` except in `IMMEDIATE` mode will block the debuglink until the new
layout comes up. If the calling code is waiting for a `DebugLinkGetState` to return, it
will deadlock.

(Firmware tries to detect the above condition and sends an error over debuglink if the
wait state is `CURRENT_LAYOUT` and there is no current layout for more than 2 seconds.)

## Synchronizing

`ButtonRequest` is a synchronization event. After a `ButtonRequest` has been sent from
firmware, all debug commands are guaranteed to hit the layout corresponding to the
`ButtonRequest` (unless the layout is terminated by a timer event or user interaction).

`DebugLinkDecision` is also a synchronization event. After a `DebugLinkDecision` has
been received by the firmware, all debug commands are guaranteed to hit the layout
that is the "result" of the decision.

In order to synchronize on a homescreen, it is possible to either:

* invoke any workflow that triggers a `ButtonRequest`, and follow it until end
  (`Ping(button_protection=True)` would work fine), or
* poll `DebugLinkGetState` until the layout is `Homescreen`. Typically, running
  `DebugLinkGetState(wait_layout=CURRENT_LAYOUT)` will work on the first try if you are
  close enough to homescreen (such as after completing a workflow).

`wait_layout=NEXT_LAYOUT` _cannot_ be used for synchronization, because it always
returns the _next_ layout. If the current one is already homescreen, it will wait
forever.
