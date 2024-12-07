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

## Python layout object lifecycle

A newly created layout object is in **READY** state. It does not accept events, has no
background tasks, does not draw on screen.

When started, it moves into **RUNNING** state. It is drawn on screen (with backlight
on), accepts events, and runs background tasks. The value of `ui.CURRENT_LAYOUT` is set
to the running layout object.

(This implies that at most one layout can be in **RUNNING** state.)

Layout in **RUNNING** state may stop and return a result, either in response to a user
interaction event (touch, button click, USB) or an internal timer firing. This moves it
into a **FINISHED** state. It is no longer shown on screen (backlight is off unless
another layout turns it on again), does not accept events, and does not run background
tasks.

A layout in a **FINISHED** state has a **result** value, available for pickup by
awaiting `get_result()`.

Stopping a layout before returning a result, or retrieving a result of a **FINISHED**
layout, will move it back to **READY** state.

### State transitions

```
+-------+    start()   +-----------+    <event>    +------------+
| READY | -----------> |  RUNNING  | ------------> |  FINISHED  |
+-------+              +-----------+               +------------+
  ^   ^                      |                           |
  |   |                      |                           |
  |   +------- stop() -------+                           |
  |                                                      |
  +--------------------- get_result() -------------------+
```

Calling `start()` checks if other layout is running, and if it is, stops it first. Then
it performs the setup and moves layout into **RUNNING** state.

(At most one layout can be in **RUNNING** state at one time. That means that before a
layout moves to **RUNNING**, the previously running layout must move out.)

When layout is in **RUNNING** state, calling `start()` is a no-op. When layout is in
**FINISHED** state, calling `start()` fails an assertion.

After `start()` returns, the layout is in **RUNNING** state. It will stay in this state
until it returns a result, or is stopped.

Calling `stop()` on a **READY** or **FINISHED** layout is a no-op. Calling `stop()` on a
**RUNNING** layout will shut down any tasks waiting on the layout's result, and move to
**READY** state.

After `stop()` returns, the layout is not in **RUNNING** state and the current layout is
no longer this layout.

Awaiting `get_result()` will resume the lifecycle from its current stage, that is:

* in **READY** state, starts the layout and waits for its result
* in **RUNNING** state, waits for the result
* in **FINISHED** state, returns the result

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

## Rust layout object lifecycle

A layout on the Rust side is represented by the trait `Layout`, whose `event()` method
returns a value of type `Option<LayoutState>`. If this event caused a state transition,
the new state is returned.

Layout can be in one of four states:

* `Initial`: the layout is freshly constructed. This is never returned as a result of
  `event()`.
* `Attached`: the layout is running. Its timers have been started and it is accepting
  events. The state transition carries an `Option<ButtonRequest>`. If set, this is the
  ButtonRequest that should be sent to the host, as an indication that the layout is
  ready.
* `Transitioning`: the layout is running, but not ready to receive events; either a
  transition-in or a transition-out animation is running.<br>
  The enum value carries an `AttachType`, indicating which direction the transition is
  going. If this is an outgoing transition, the runtime is supposed to pass the
  attach type to the next layout, so that it can properly transition-in.
* `Done`: the layout has finished running. All its timers should be stopped, and there
  is a return value available via the `value()` method.

We currently _do not keep precise track_ of transitioning animations; it would be a lot
of effort to factor the code properly, while the only use case is debuglink state
tracking, which works well enough as-is.

### Simple layouts

Layouts that are not flows (i.e., have only one screen) are implemented as `Components`
with a `ComponentMsgObj` implementation. They are wrapped in a `RootComponent` struct
which essentially _simulates_ the layout lifecycle, in the following manner:

1. At start, the layout is `Initial`.
2. After processing the `Attach` event, the layout is `Attached`. The ButtonRequest
   value is picked up from `ctx.button_request()`.
3. When `Component::event()` returns non-`None` value, the layout is `Done`. The return
   value is converted to `Obj` via `ComponentMsgObj::msg_try_into_obj()` and cached as
   `value` on the `RootComponent`.

### Flows

Flow layouts in `mercury` are implemented as a `SwipeFlow` struct, which implements
`Layout` directly.

A flow lifecycle works like this:

1. At start, the layout is `Initial`.
2. After processing the `Attach` event, the layout is `Attached`. The ButtonRequest
   value is picked up from `ctx.button_request()`.
3. When the flow controller returns a transition from a _swipe_ event, the layout goes
   directly to `Attached` state. This is because at that point the transition animation
   is already finished.
4. When the flow controller returns a transition from a _non-swipe_ event (e.g., a
   button click), the flow controller starts an automatic transition-out animation, and
   the layout goes to `Transitioning` state, with the transition direction set to the
   swipe animation direction.
5. When the flow controller returns a `Return` decision, the layout goes to `Done`.

Transition-in animations are currently not tracked properly. This is fine for tests
because animations are disabled there, but it may break at some point. Correctly
tracking transitions would require a more significant refactor of the flow controllers.

Transition-out animations are partially tracked, when the animation is directed by the
`FlowState` object. In some cases (such as when a swipe is triggered), the animation is
instead controlled by the destination screen, in which case they are not tracked.

## Button requests

A `ButtonRequest` MUST be sent while the corresponding layout is already in **RUNNING**
state. That is, in particular, the value of `ui.CURRENT_LAYOUT` is of the corresponding
layout.

The best choice is to always use the `interact()` function to take care of
`ButtonRequest`s. Explicitly sending `ButtonRequest`s is not supported.

`ButtonRequest`s sent from Rust get sent as part of the `Attached` state transition,
which can only happen when the layout is already running.

TODO: instead of relying on `interact()`, it may be better to pass the `ButtonRequest`
inside the layout object and enqueue it so that when the respective Rust layout is
`Attached`, the outside-provided `ButtonRequest` is used.

## Debuglink

We assume that only one caller is using the debuglink and that debuglink commands are
strongly ordered on the caller side. On the firmware side, we impose strong ordering on
the received debuglink calls based on the time of arrival.

There are two layout-relevant debuglink commands.

### `DebugLinkDecision`

Caller can send a decision to the **RUNNING** and `Attached` layout. This injects an
event into the layout. In response, the layout can move to a **FINISHED** state.

If a `DebugLinkDecision` is received while a layout is not **RUNNING** or not
`Attached`, debuglink pauses until some layout becomes ready to receive decisions.

A next debug command is read only after a `DebugLinkDecision` is fully processed. This
means that:

* if the decision caused the layout to stop, subsequent debug commands will be received
  by the next layout up,
* if the decision caused the layout to transition, subsequent debug commands will be
  received by the respective layout when the transition is done, and
* if the decision did not cause the layout to change state, subsequent debug commands
  will be received by the same layout.

### `DebugLinkGetState`

Caller can read the contents of the **RUNNING** layout.

There are three available waiting behaviors:

* `IMMEDIATE` (default) returns the contents of the layout that is currently
  **RUNNING**, or empty response if no layout is running. Rust layout lifecycle state is
  not taken into account.
* `NEXT_LAYOUT` waits for the layout to change before returning -- that is, waits until
  the next time a **RUNNING** layout transitions into an `Attached` state:
  - If no layout is running, waits until one is started.
  - If a layout is running but not attached, waits until it is attached.
  - If a layout is running and attached, waits until the layout stops or becomes
    attached again.
* `CURRENT_LAYOUT` waits until a layout is running and attached, and returns its
  contents. If no layout is running or it is not attached, the behavior is the same as
  `NEXT_LAYOUT`. If a layout is running and attached, the behavior is the same as
  `IMMEDIATE`.

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
wait state is `CURRENT_LAYOUT` and there is no current layout for more than 3 seconds.)

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
