use crate::{
    error,
    time::Instant,
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Swipe, SwipeDirection},
        flow::{base::Decision, FlowMsg, FlowState, FlowStore},
        geometry::{Offset, Rect},
        shape::Renderer,
        util,
    },
};

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
    /// `Transition::None` when state transition animation is in not progress.
    transition: Transition<Q>,
    /// Swipe detector.
    swipe: Swipe,
}

enum Transition<Q> {
    /// SwipeFlow is performing transition between different states.
    External {
        /// State we are transitioning _from_.
        prev_state: Q,
        /// Animation progress.
        animation: Animation<f32>,
        /// Direction of the slide animation.
        direction: SwipeDirection,
    },
    /// Transition runs in child component, we forward events and wait.
    Internal,
    /// No transition.
    None,
}

impl<Q: FlowState, S: FlowStore> SwipeFlow<Q, S> {
    pub fn new(init: Q, store: S) -> Result<Self, error::Error> {
        Ok(Self {
            state: init,
            store,
            transition: Transition::None,
            swipe: Swipe::new().down().up().left().right(),
        })
    }

    fn goto(&mut self, ctx: &mut EventCtx, direction: SwipeDirection, state: Q) {
        if state == self.state {
            self.transition = Transition::Internal;
            return;
        }
        if util::animation_disabled() {
            self.state = state;
            self.store.event(state.index(), ctx, Event::Attach);
            ctx.request_paint();
            return;
        }
        self.transition = Transition::External {
            prev_state: self.state,
            animation: Animation::new(0.0f32, 1.0f32, util::SLIDE_DURATION, Instant::now()),
            direction,
        };
        self.state = state;
        ctx.request_anim_frame();
        ctx.request_paint();
    }

    fn render_state<'s>(&'s self, state: Q, target: &mut impl Renderer<'s>) {
        self.store.render(state.index(), target)
    }

    fn render_transition<'s>(
        &'s self,
        prev_state: &Q,
        animation: &Animation<f32>,
        direction: &SwipeDirection,
        target: &mut impl Renderer<'s>,
    ) {
        util::render_slide(
            |target| self.render_state(*prev_state, target),
            |target| self.render_state(self.state, target),
            animation.value(Instant::now()),
            *direction,
            target,
        );
    }

    fn handle_transition(&mut self, ctx: &mut EventCtx, event: Event) -> Option<FlowMsg> {
        let i = self.state.index();
        let mut finished = false;
        let result = match &self.transition {
            Transition::External { animation, .. }
                if matches!(event, Event::Timer(EventCtx::ANIM_FRAME_TIMER)) =>
            {
                if animation.finished(Instant::now()) {
                    finished = true;
                    ctx.request_paint();
                    self.store.event(i, ctx, Event::Attach)
                } else {
                    ctx.request_anim_frame();
                    ctx.request_paint();
                    None
                }
            }
            Transition::External { .. } => None, // ignore all events until animation finishes
            Transition::Internal => {
                let msg = self.store.event(i, ctx, event);
                if self.store.map_swipable(i, |s| s.swipe_finished()) {
                    finished = true;
                };
                msg
            }
            Transition::None => unreachable!(),
        };
        if finished {
            self.transition = Transition::None;
        }
        result
    }

    fn handle_swipe_child(&mut self, ctx: &mut EventCtx, direction: SwipeDirection) -> Decision<Q> {
        let i = self.state.index();
        if self
            .store
            .map_swipable(i, |s| s.swipe_start(ctx, direction))
        {
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
        self.swipe.place(bounds);
        self.store.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if !matches!(self.transition, Transition::None) {
            return self.handle_transition(ctx, event);
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
        match &self.transition {
            Transition::None | Transition::Internal => self.render_state(self.state, target),
            Transition::External {
                prev_state,
                animation,
                direction,
            } => self.render_transition(prev_state, animation, direction, target),
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
