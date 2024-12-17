use crate::{
    error::{self, Error},
    maybe_trace::MaybeTrace,
    micropython::{
        gc::{self, GcBox},
        obj::Obj,
    },
    ui::{
        component::{
            base::AttachType::{self, Swipe},
            Component, Event, EventCtx, FlowMsg, SwipeDetect,
        },
        display::Color,
        event::SwipeEvent,
        flow::{base::Decision, FlowController},
        geometry::{Direction, Rect},
        layout::base::{Layout, LayoutState},
        shape::{render_on_display, ConcreteRenderer, Renderer, ScopedRenderer},
        util::animation_disabled,
        CommonUI, ModelUI,
    },
};

use super::{base::FlowState, Swipable};

use heapless::Vec;

/// Component-like proto-object-safe trait.
///
/// This copies the Component interface, but it is parametrized by a concrete
/// Renderer type, making it object-safe.
pub trait FlowComponentTrait<'s, R: Renderer<'s>>: Swipable {
    fn place(&mut self, bounds: Rect) -> Rect;
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<FlowMsg>;
    fn render(&'s self, target: &mut R);

    #[cfg(feature = "ui_debug")]
    fn trace(&self, t: &mut dyn crate::trace::Tracer);
}

/// FlowComponentTrait implementation for Components.
///
/// Components implementing FlowComponentTrait must:
/// * also implement Swipable, required by FlowComponentTrait,
/// * use FlowMsg as their Msg type,
/// * implement MaybeTrace to be able to conform to ObjComponent.
impl<'s, R, C> FlowComponentTrait<'s, R> for C
where
    C: Component<Msg = FlowMsg> + MaybeTrace + Swipable,
    R: Renderer<'s>,
{
    fn place(&mut self, bounds: Rect) -> Rect {
        <Self as Component>::place(self, bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<FlowMsg> {
        <Self as Component>::event(self, ctx, event)
    }

    fn render(&'s self, target: &mut R) {
        <Self as Component>::render(self, target)
    }

    #[cfg(feature = "ui_debug")]
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        <Self as crate::trace::Trace>::trace(self, t)
    }
}

/// Shortcut type for the concrete renderer passed into `render()` method.
type RendererImpl<'a, 'alloc, 'env> = ScopedRenderer<'alloc, 'env, ConcreteRenderer<'a, 'alloc>>;

/// Fully object-safe component-like trait for flow components.
///
/// This trait has no generic parameters:
/// * it is instantiated with a concrete Renderer type, and
/// * it requires the `FlowComponentTrait` trait to be implemented for _any_
///   lifetimes.
pub trait FlowComponentDynTrait:
    for<'a, 'alloc, 'env> FlowComponentTrait<'alloc, RendererImpl<'a, 'alloc, 'env>>
{
}

impl<T> FlowComponentDynTrait for T where
    T: for<'a, 'alloc, 'env> FlowComponentTrait<'alloc, RendererImpl<'a, 'alloc, 'env>>
{
}

/// Swipe flow consisting of multiple screens.
///
/// Implements swipe navigation between the states with animated transitions,
/// based on state transitions provided by the FlowState type.
///
/// If a swipe is detected:
/// - currently active component is asked to handle the event,
/// - if it can't then FlowState::handle_swipe is consulted.
pub struct SwipeFlow {
    /// Current state of the flow.
    state: FlowState,
    /// Store of all screens which are part of the flow.
    store: Vec<GcBox<dyn FlowComponentDynTrait>, 12>,
    /// Swipe detector.
    swipe: SwipeDetect,
    /// Swipe allowed
    allow_swipe: bool,
    /// Current page index
    internal_page_idx: u16,
    /// Internal pages count
    internal_pages: u16,
    /// If triggering swipe by event, make this decision instead of default
    /// after the swipe.
    pending_decision: Option<Decision>,
    /// Layout lifecycle state.
    lifecycle_state: LayoutState,
    /// Returned value from latest transition, stored as Obj.
    returned_value: Option<Result<Obj, Error>>,
}

impl SwipeFlow {
    pub fn new(initial_state: &'static dyn FlowController) -> Result<Self, error::Error> {
        Ok(Self {
            state: initial_state,
            swipe: SwipeDetect::new(),
            store: Vec::new(),
            allow_swipe: true,
            internal_page_idx: 0,
            internal_pages: 1,
            pending_decision: None,
            lifecycle_state: LayoutState::Initial,
            returned_value: None,
        })
    }

    /// Add a page to the flow.
    ///
    /// Pages must be inserted in the order of the flow state index.
    pub fn with_page(
        mut self,
        state: &'static dyn FlowController,
        page: impl FlowComponentDynTrait + 'static,
    ) -> Result<Self, error::Error> {
        debug_assert!(self.store.len() == state.index());
        let alloc = GcBox::new(page)?;
        let page = gc::coerce!(FlowComponentDynTrait, alloc);
        unwrap!(self.store.push(page));
        Ok(self)
    }

    fn current_page(&self) -> &GcBox<dyn FlowComponentDynTrait> {
        &self.store[self.state.index()]
    }

    fn current_page_mut(&mut self) -> &mut GcBox<dyn FlowComponentDynTrait> {
        &mut self.store[self.state.index()]
    }

    fn update_page_count(&mut self, attach_type: AttachType) {
        // update page count
        self.internal_pages = self.current_page_mut().get_internal_page_count() as u16;
        // reset internal state:
        self.internal_page_idx = if let Swipe(Direction::Down) = attach_type {
            // if coming from below, set to the last page
            self.internal_pages.saturating_sub(1)
        } else {
            // else reset to the first page
            0
        };
    }

    /// Transition to a different state.
    ///
    /// This is the only way to change the current flow state.
    fn goto(&mut self, ctx: &mut EventCtx, new_state: FlowState, attach_type: AttachType) {
        // update current page
        self.state = new_state;

        // reset and unlock swipe config
        self.swipe = SwipeDetect::new();
        // unlock swipe events
        self.allow_swipe = true;

        // send an Attach event to the new page
        self.current_page_mut()
            .event(ctx, Event::Attach(attach_type));

        self.update_page_count(attach_type);
        ctx.request_paint();
    }

    fn render_state<'s>(&'s self, state: usize, target: &mut RendererImpl<'_, 's, '_>) {
        self.store[state].render(target);
    }

    fn handle_swipe_child(&mut self, _ctx: &mut EventCtx, direction: Direction) -> Decision {
        self.state.handle_swipe(direction)
    }

    fn handle_event_child(&mut self, ctx: &mut EventCtx, event: Event) -> Decision {
        let msg = self.current_page_mut().event(ctx, event);

        if let Some(msg) = msg {
            self.state.handle_event(msg)
        } else {
            Decision::Nothing
        }
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<LayoutState> {
        let mut decision = Decision::Nothing;
        let mut return_transition: AttachType = AttachType::Initial;

        if let Event::Attach(attach_type) = event {
            self.update_page_count(attach_type);
        }

        let mut attach = false;

        let event = if self.allow_swipe {
            let page = self.current_page();
            let config = page
                .get_swipe_config()
                .with_pagination(self.internal_page_idx, self.internal_pages);

            match self.swipe.event(ctx, event, config) {
                Some(SwipeEvent::End(dir)) => {
                    return_transition = AttachType::Swipe(dir);

                    let new_internal_page_idx =
                        config.paging_event(dir, self.internal_page_idx, self.internal_pages);
                    if new_internal_page_idx != self.internal_page_idx {
                        // internal paging event
                        self.internal_page_idx = new_internal_page_idx;
                        decision = Decision::Nothing;
                        attach = true;
                    } else if let Some(override_decision) = self.pending_decision.take() {
                        // end of simulated swipe, applying original decision
                        decision = override_decision;
                    } else {
                        // normal end-of-swipe event handling
                        decision = self.handle_swipe_child(ctx, dir);
                    }
                    Event::Swipe(SwipeEvent::End(dir))
                }
                Some(e) => Event::Swipe(e),
                None => event,
            }
        } else {
            event
        };

        match decision {
            Decision::Nothing => {
                decision = self.handle_event_child(ctx, event);

                // when doing internal transition, pass attach event to the child after sending
                // swipe end.
                if attach {
                    if let Event::Swipe(SwipeEvent::End(dir)) = event {
                        self.current_page_mut()
                            .event(ctx, Event::Attach(AttachType::Swipe(dir)));
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

                let config = self.current_page().get_swipe_config();

                if let Decision::Transition(_, Swipe(direction)) = decision {
                    if config.is_allowed(direction) {
                        self.allow_swipe = true;
                        if !animation_disabled() {
                            self.swipe.trigger(ctx, direction, config);
                            self.pending_decision = Some(decision);
                            return Some(LayoutState::Transitioning(return_transition));
                        }
                    }
                }
            }
            _ => {
                //ignore message, we are already transitioning
                let msg = self.current_page_mut().event(ctx, event);
                assert!(msg.is_none());
            }
        }

        match decision {
            Decision::Transition(new_state, attach) => {
                self.goto(ctx, new_state, attach);
                Some(LayoutState::Attached(ctx.button_request().take()))
            }
            Decision::Return(msg) => {
                ctx.set_transition_out(return_transition);
                self.swipe.reset();
                self.allow_swipe = true;
                self.returned_value = Some(msg.try_into());
                Some(LayoutState::Done)
            }
            Decision::Nothing if matches!(event, Event::Attach(_)) => {
                Some(LayoutState::Attached(ctx.button_request().take()))
            }
            _ => None,
        }
    }
}

/// Layout implementation for SwipeFlow.
///
/// This way we can completely avoid implementing `Component`. That also allows
/// us to pass around concrete Renderers instead of having to conform to
/// `Component`'s not-object-safe interface.
impl Layout<Result<Obj, Error>> for SwipeFlow {
    fn place(&mut self) {
        for elem in self.store.iter_mut() {
            elem.place(ModelUI::SCREEN);
        }
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<LayoutState> {
        self.event(ctx, event)
    }

    fn value(&self) -> Option<&Result<Obj, Error>> {
        self.returned_value.as_ref()
    }

    fn paint(&mut self) {
        render_on_display(None, Some(Color::black()), |target| {
            self.render_state(self.state.index(), target);
        });
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SwipeFlow {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.current_page().trace(t)
    }
}
