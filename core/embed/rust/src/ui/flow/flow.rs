use crate::{
    error,
    time::{Duration, Instant},
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Swipe, SwipeDirection},
        flow::{base::Decision, FlowMsg, FlowState, FlowStore},
        geometry::{Offset, Rect},
        shape::Renderer,
    },
};

const ANIMATION_DURATION: Duration = Duration::from_millis(333);

/// Given a state enum and a corresponding FlowStore, create a Component that
/// implements a swipe navigation between the states with animated transitions.
///
/// If a swipe is detected:
/// - currently active component is asked to handle the event,
/// - if it can't then FlowState::handle_swipe is consulted.
pub struct SwipeFlow<Q, S> {
    /// Current state.
    state: Q,
    /// FlowStore with all screens/components.
    store: S,
    /// `Some` when state transition animation is in progress.
    transition: Option<Transition<Q>>,
    /// Swipe detector.
    swipe: Swipe,
    /// Animation parameter.
    anim_offset: Offset,
}

struct Transition<Q> {
    prev_state: Q,
    animation: Animation<Offset>,
    direction: SwipeDirection,
}

impl<Q: FlowState, S: FlowStore> SwipeFlow<Q, S> {
    pub fn new(init: Q, store: S) -> Result<Self, error::Error> {
        Ok(Self {
            state: init,
            store,
            transition: None,
            swipe: Swipe::new().down().up().left().right(),
            anim_offset: Offset::zero(),
        })
    }

    fn goto(&mut self, ctx: &mut EventCtx, direction: SwipeDirection, state: Q) {
        self.transition = Some(Transition {
            prev_state: self.state,
            animation: Animation::new(
                Offset::zero(),
                direction.as_offset(self.anim_offset),
                ANIMATION_DURATION,
                Instant::now(),
            ),
            direction,
        });
        self.state = state;
        ctx.request_anim_frame();
        ctx.request_paint()
    }

    fn render_state<'s>(&'s self, state: Q, target: &mut impl Renderer<'s>) {
        self.store.render(state.index(), target)
    }

    fn render_transition<'s>(&'s self, transition: &Transition<Q>, target: &mut impl Renderer<'s>) {
        let off = transition.animation.value(Instant::now());

        if self.state == transition.prev_state {
            target.with_origin(off, &|target| {
                self.store.render_cloned(target);
            });
        } else {
            target.with_origin(off, &|target| {
                self.render_state(transition.prev_state, target);
            });
        }
        target.with_origin(
            off - transition.direction.as_offset(self.anim_offset),
            &|target| {
                self.render_state(self.state, target);
            },
        );
    }

    fn handle_transition(&mut self, ctx: &mut EventCtx) {
        if let Some(transition) = &self.transition {
            if transition.animation.finished(Instant::now()) {
                self.transition = None;
                unwrap!(self.store.clone(None)); // Free the clone.

                let msg = self.store.event(self.state.index(), ctx, Event::Attach);
                assert!(msg.is_none())
            } else {
                ctx.request_anim_frame();
            }
            ctx.request_paint();
        }
    }

    fn handle_swipe_child(&mut self, ctx: &mut EventCtx, direction: SwipeDirection) -> Decision<Q> {
        let i = self.state.index();
        if self.store.map_swipable(i, |s| s.can_swipe(direction)) {
            // Before handling the swipe we make a copy of the original state so that we
            // can render both states in the transition animation.
            unwrap!(self.store.clone(Some(i)));
            self.store.map_swipable(i, |s| s.swiped(ctx, direction));
            Decision::Goto(self.state, direction)
        } else {
            Decision::Nothing
        }
    }

    fn handle_event_child(&mut self, ctx: &mut EventCtx, event: Event) -> Decision<Q> {
        let msg = self.store.event(self.state.index(), ctx, event);
        if let Some(msg) = msg {
            self.state.handle_event(msg)
        } else {
            Decision::Nothing
        }
    }
}

impl<Q: FlowState, S: FlowStore> Component for SwipeFlow<Q, S> {
    type Msg = FlowMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        // Save screen size for slide animation. Once we have reasonable constants trait
        // this can be set in the constructor.
        self.anim_offset = bounds.size();

        self.swipe.place(bounds);
        self.store.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        // TODO: are there any events we want to send to all? timers perhaps?
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            self.handle_transition(ctx);
        }
        // Ignore events while transition is running.
        if self.transition.is_some() {
            return None;
        }

        let mut decision = Decision::Nothing;
        if let Some(direction) = self.swipe.event(ctx, event) {
            decision = self
                .handle_swipe_child(ctx, direction)
                .or_else(|| self.state.handle_swipe(direction));
        }
        decision = decision.or_else(|| self.handle_event_child(ctx, event));

        match decision {
            Decision::Nothing => None,
            Decision::Goto(next_state, direction) => {
                self.goto(ctx, direction, next_state);
                None
            }
            Decision::Return(msg) => Some(msg),
        }
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(transition) = &self.transition {
            self.render_transition(transition, target)
        } else {
            self.render_state(self.state, target)
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<Q: FlowState, S: FlowStore> crate::trace::Trace for SwipeFlow<Q, S> {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.store.trace(self.state.index(), t)
    }
}

#[cfg(feature = "micropython")]
impl<Q: FlowState, S: FlowStore> crate::ui::layout::obj::ComponentMsgObj for SwipeFlow<Q, S> {
    fn msg_try_into_obj(
        &self,
        msg: Self::Msg,
    ) -> Result<crate::micropython::obj::Obj, error::Error> {
        match msg {
            FlowMsg::Confirmed => Ok(crate::ui::layout::result::CONFIRMED.as_obj()),
            FlowMsg::Cancelled => Ok(crate::ui::layout::result::CANCELLED.as_obj()),
            FlowMsg::Info => Ok(crate::ui::layout::result::INFO.as_obj()),
            FlowMsg::Choice(i) => {
                Ok((crate::ui::layout::result::CONFIRMED.as_obj(), i.try_into()?).try_into()?)
            }
        }
    }
}
