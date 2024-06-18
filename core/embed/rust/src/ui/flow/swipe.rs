use crate::{
    error,
    ui::{
        component::{
            base::AttachType, swipe_detect::SwipeSettings, Component, Event, EventCtx, SwipeDetect,
            SwipeDetectMsg, SwipeDirection,
        },
        event::{SwipeEvent, TouchEvent},
        flow::{base::Decision, FlowMsg, FlowState, FlowStore},
        geometry::Rect,
        shape::Renderer,
        util::animation_disabled,
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
    /// Swipe detector.
    swipe: SwipeDetect,
    /// Swipe allowed
    allow_swipe: bool,
    /// Current internal state
    internal_state: u16,
    /// Internal pages count
    internal_pages: u16,
    /// If triggering swipe by event, make this decision instead of default
    /// after the swipe.
    decision_override: Option<Decision<Q>>,
}

impl<Q: FlowState, S: FlowStore> SwipeFlow<Q, S> {
    pub fn new(init: Q, store: S) -> Result<Self, error::Error> {
        Ok(Self {
            state: init,
            swipe: SwipeDetect::new(),
            store,
            allow_swipe: true,
            internal_state: 0,
            internal_pages: 1,
            decision_override: None,
        })
    }
    fn goto(&mut self, ctx: &mut EventCtx, direction: SwipeDirection, state: Q) {
        self.state = state;
        self.swipe = SwipeDetect::new();
        self.allow_swipe = true;

        self.store.event(
            state.index(),
            ctx,
            Event::Attach(AttachType::Swipe(direction)),
        );

        self.internal_pages = self.store.get_internal_page_count(state.index()) as u16;

        match direction {
            SwipeDirection::Up => {
                self.internal_state = 0;
            }
            SwipeDirection::Down => {
                self.internal_state = self.internal_pages.saturating_sub(1);
            }
            _ => {}
        }

        ctx.request_paint();
    }

    fn render_state<'s>(&'s self, state: Q, target: &mut impl Renderer<'s>) {
        self.store.render(state.index(), target)
    }

    fn handle_swipe_child(
        &mut self,
        _ctx: &mut EventCtx,
        direction: SwipeDirection,
    ) -> Decision<Q> {
        self.state.handle_swipe(direction)
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
        self.store.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let mut decision: Decision<Q> = Decision::Nothing;
        let mut return_transition: AttachType = AttachType::Initial;

        let mut attach = false;

        let e = if self.allow_swipe {
            let mut config = self.store.get_swipe_config(self.state.index());

            self.internal_pages = self.store.get_internal_page_count(self.state.index()) as u16;

            // add additional swipe directions if there are more internal pages
            // todo can we get internal settings from config somehow?
            // might wanna different duration or something
            if config.vertical_pages && self.internal_state > 0 {
                config = config.with_swipe(SwipeDirection::Down, SwipeSettings::default())
            }
            if config.horizontal_pages && self.internal_state > 0 {
                config = config.with_swipe(SwipeDirection::Right, SwipeSettings::default())
            }
            if config.vertical_pages && self.internal_state < self.internal_pages - 1 {
                config = config.with_swipe(SwipeDirection::Up, SwipeSettings::default())
            }
            if config.horizontal_pages && self.internal_state < self.internal_pages - 1 {
                config = config.with_swipe(SwipeDirection::Left, SwipeSettings::default())
            }

            match self.swipe.event(ctx, event, config) {
                Some(SwipeDetectMsg::Trigger(dir)) => {
                    if let Some(override_decision) = self.decision_override.take() {
                        decision = override_decision;
                    } else {
                        decision = self.handle_swipe_child(ctx, dir);
                    }

                    return_transition = AttachType::Swipe(dir);

                    let states_num = self.internal_pages;
                    if states_num > 0 {
                        if config.has_horizontal_pages() {
                            let current_state = self.internal_state;
                            if dir == SwipeDirection::Left && current_state < states_num - 1 {
                                self.internal_state += 1;
                                decision = Decision::Nothing;
                                attach = true;
                            } else if dir == SwipeDirection::Right && current_state > 0 {
                                self.internal_state -= 1;
                                decision = Decision::Nothing;
                                attach = true;
                            }
                        }
                        if config.has_vertical_pages() {
                            let current_state = self.internal_state;
                            if dir == SwipeDirection::Up && current_state < states_num - 1 {
                                self.internal_state += 1;
                                decision = Decision::Nothing;
                                attach = true;
                            } else if dir == SwipeDirection::Down && current_state > 0 {
                                self.internal_state -= 1;
                                decision = Decision::Nothing;
                                attach = true;
                            }
                        }
                    }

                    Some(Event::Swipe(SwipeEvent::End(dir)))
                }
                Some(SwipeDetectMsg::Move(dir, progress)) => {
                    Some(Event::Swipe(SwipeEvent::Move(dir, progress as i16)))
                }
                Some(SwipeDetectMsg::Start(_)) => Some(Event::Touch(TouchEvent::TouchAbort)),
                _ => Some(event),
            }
        } else {
            Some(event)
        };

        if let Some(e) = e {
            match decision {
                Decision::Nothing => {
                    decision = self.handle_event_child(ctx, e);

                    // when doing internal transition, pass attach event to the child after sending
                    // swipe end.
                    if attach {
                        if let Event::Swipe(SwipeEvent::End(dir)) = e {
                            self.store.event(
                                self.state.index(),
                                ctx,
                                Event::Attach(AttachType::Swipe(dir)),
                            );
                        }
                    }

                    if ctx.disable_swipe_requested() {
                        self.swipe.reset();
                        self.allow_swipe = false;
                    }
                    if ctx.enable_swipe_requested() {
                        self.swipe.reset();
                        self.allow_swipe = true;
                    };

                    let config = self.store.get_swipe_config(self.state.index());

                    if let Decision::Goto(_, direction) = decision {
                        if config.is_allowed(direction) {
                            if !animation_disabled() {
                                self.swipe.trigger(ctx, direction, config);
                                self.decision_override = Some(decision);
                                decision = Decision::Nothing;
                            }
                            self.allow_swipe = true;
                        }
                    }
                }
                _ => {
                    //ignore message, we are already transitioning
                    self.store.event(self.state.index(), ctx, event);
                }
            }
        }

        match decision {
            Decision::Goto(next_state, direction) => {
                self.goto(ctx, direction, next_state);
                None
            }
            Decision::Return(msg) => {
                ctx.set_transition_out(return_transition);
                self.swipe.reset();
                self.allow_swipe = true;
                Some(msg)
            }
            _ => None,
        }
    }

    fn paint(&mut self) {}

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.render_state(self.state, target);
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
