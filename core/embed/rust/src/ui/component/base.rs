use heapless::Vec;

use crate::{
    strutil::{ShortString, TString},
    time::Duration,
    ui::{
        button_request::{ButtonRequest, ButtonRequestCode},
        component::{maybe::PaintOverlapping, MsgMap, PageMap},
        display::Color,
        geometry::{Offset, Rect},
        shape::Renderer,
    },
};

#[cfg(feature = "button")]
use crate::ui::event::ButtonEvent;
use crate::ui::event::USBEvent;
#[cfg(feature = "touch")]
use crate::ui::{
    event::{SwipeEvent, TouchEvent},
    geometry::Direction,
};

use super::Paginate;

/// Type used by components that do not return any messages.
///
/// Alternative to the yet-unstable `!`-type.
pub enum Never {}

/// User interface is composed of components that can react to `Event`s through
/// the `event` method, and know how to paint themselves to screen through the
/// `paint` method.  Components can emit messages as a reaction to events.
pub trait Component {
    type Msg;

    /// Position the component into some available space, specified by `bounds`.
    ///
    /// Component should lay itself out, together with all children, and return
    /// the total bounding box. This area can, occasionally, be larger than
    /// `bounds` (it is a soft-limit), but the component **should never** paint
    /// outside of it.
    ///
    /// No painting should be done in this phase.
    fn place(&mut self, bounds: Rect) -> Rect;

    /// React to an outside event. See the `Event` type for possible cases.
    ///
    /// Component should modify its internal state as a response to the event,
    /// and usually call `EventCtx::request_paint` to mark itself for painting.
    /// Component can also optionally return a message as a result of the
    /// interaction.
    ///
    /// For all components to work properly (e.g. react to `ctx.request_paint`),
    /// it is required to call `event` function to them, even if they never
    /// return a message.
    ///
    /// No painting should be done in this phase.
    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg>;

    /// Render to screen, based on current internal state.
    ///
    /// To prevent unnecessary over-draw, dirty state checking is performed in
    /// the `Child` wrapper.
    fn paint(&mut self);

    fn render<'s>(&'s self, _target: &mut impl Renderer<'s>);
}

/// Components should always avoid unnecessary overpaint to prevent obvious
/// tearing and flickering. `Child` wraps an inner component `T` and keeps a
/// dirty flag for it. Any mutation of `T` has to happen through the `mutate`
/// accessor, `T` can then request a paint call to be scheduled later by calling
/// `EventCtx::request_paint` in its `event` pass.
#[derive(Clone)]
pub struct Child<T> {
    component: T,
    marked_for_paint: bool,
}

impl<T> Child<T> {
    pub const fn new(component: T) -> Self {
        Self {
            component,
            marked_for_paint: true,
        }
    }

    pub fn inner(&self) -> &T {
        &self.component
    }

    pub fn into_inner(self) -> T {
        self.component
    }

    /// Access inner component mutably, track whether a paint call has been
    /// requested, and propagate the flag upwards the component tree.
    pub fn mutate<F, U>(&mut self, ctx: &mut EventCtx, component_func: F) -> U
    where
        F: FnOnce(&mut EventCtx, &mut T) -> U,
    {
        let prev_requested = core::mem::replace(&mut ctx.paint_requested, false);
        let result = component_func(ctx, &mut self.component);
        if ctx.paint_requested {
            // If a paint was requested anywhere in the inner component tree, we need to
            // mark ourselves for paint as well, and keep the `ctx` flag so it can
            // propagate upwards.
            self.marked_for_paint = true;
        } else {
            // Paint has not been requested in the *inner* component, so there's no need to
            // paint it, but we need to preserve the previous flag carried in `ctx` so it
            // properly propagates upwards (i.e. from our previous siblings).
            ctx.paint_requested = prev_requested;
        }
        result
    }

    /// Do not draw on screen until an event requests paint. This is used by
    /// homescreens to avoid flickering when workflow restart happens.
    pub fn skip_paint(&mut self) {
        self.marked_for_paint = false;
    }

    pub fn will_paint(&self) -> bool {
        self.marked_for_paint
    }
}

impl<T> Component for Child<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.component.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.mutate(ctx, |ctx, c| {
            // Handle the internal invalidation event here, so components don't have to. We
            // still pass it inside, so the event propagates correctly to all components in
            // the sub-tree.
            if let Event::RequestPaint = event {
                ctx.request_paint();
            }
            c.event(ctx, event)
        })
    }

    fn paint(&mut self) {
        if self.marked_for_paint {
            self.marked_for_paint = false;
            self.component.paint();
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.component.render(target);
    }
}

impl<T: Paginate> Paginate for Child<T> {
    fn page_count(&mut self) -> usize {
        self.component.page_count()
    }

    fn change_page(&mut self, active_page: usize) {
        self.component.change_page(active_page);
    }
}

impl<T> PaintOverlapping for Child<T>
where
    T: PaintOverlapping,
{
    fn cleared_area(&self) -> Option<(Rect, Color)> {
        self.component.cleared_area()
    }

    fn paint_overlapping(&mut self) {
        if self.marked_for_paint {
            self.marked_for_paint = false;
            self.component.paint_overlapping()
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Child<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.component.trace(t)
    }
}

impl<M, T, U> Component for (T, U)
where
    T: Component<Msg = M>,
    U: Component<Msg = M>,
{
    type Msg = M;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.0.place(bounds).union(self.1.place(bounds))
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0
            .event(ctx, event)
            .or_else(|| self.1.event(ctx, event))
    }

    fn paint(&mut self) {
        self.0.paint();
        self.1.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.0.render(target);
        self.1.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for (T, U)
where
    T: crate::trace::Trace,
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.in_list("children", &|l| {
            l.child(&self.0);
            l.child(&self.1);
        });
    }
}

impl<M, T, U, V> Component for (T, U, V)
where
    T: Component<Msg = M>,
    U: Component<Msg = M>,
    V: Component<Msg = M>,
{
    type Msg = M;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.0
            .place(bounds)
            .union(self.1.place(bounds))
            .union(self.2.place(bounds))
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0
            .event(ctx, event)
            .or_else(|| self.1.event(ctx, event))
            .or_else(|| self.2.event(ctx, event))
    }

    fn paint(&mut self) {
        self.0.paint();
        self.1.paint();
        self.2.paint();
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.0.render(target);
        self.1.render(target);
        self.2.render(target);
    }
}

impl<T> Component for Option<T>
where
    T: Component,
{
    type Msg = T::Msg;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self {
            Some(ref mut c) => c.event(ctx, event),
            _ => None,
        }
    }

    fn paint(&mut self) {
        if let Some(ref mut c) = self {
            c.paint()
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(ref c) = self {
            c.render(target)
        }
    }

    fn place(&mut self, bounds: Rect) -> Rect {
        match self {
            Some(ref mut c) => c.place(bounds),
            _ => bounds.with_size(Offset::zero()),
        }
    }
}

pub trait ComponentExt: Sized {
    fn map<F>(self, func: F) -> MsgMap<Self, F>;
    fn with_pages<F>(self, func: F) -> PageMap<Self, F>;
    fn into_child(self) -> Child<Self>;
    fn request_complete_repaint(&mut self, ctx: &mut EventCtx);
}

impl<T> ComponentExt for T
where
    T: Component,
{
    fn map<F>(self, func: F) -> MsgMap<Self, F> {
        MsgMap::new(self, func)
    }

    fn with_pages<F>(self, func: F) -> PageMap<Self, F> {
        PageMap::new(self, func)
    }

    fn into_child(self) -> Child<Self> {
        Child::new(self)
    }

    fn request_complete_repaint(&mut self, ctx: &mut EventCtx) {
        if self.event(ctx, Event::RequestPaint).is_some() {
            // Messages raised during a `RequestPaint` dispatch are not propagated, let's
            // make sure we don't do that.
            #[cfg(feature = "ui_debug")]
            fatal_error!("Cannot raise messages during RequestPaint");
        }
        // Make sure to at least a propagate the paint flag upwards (in case there are
        // no `Child` instances in `self`, paint would not get automatically requested
        // by sending `Event::RequestPaint` down the tree).
        ctx.request_paint();
    }
}

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum AttachType {
    /// Initial attach, redraw the whole screen
    Initial,
    /// The layout is already rendered on display, resume any animation
    /// where we left off. The animation state is expected to be stored locally
    /// in the given component.
    Resume,
    #[cfg(feature = "touch")]
    Swipe(Direction),
}

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum Event {
    #[cfg(feature = "button")]
    Button(ButtonEvent),
    #[cfg(feature = "touch")]
    Touch(TouchEvent),
    USB(USBEvent),
    /// Previously requested timer was triggered. This invalidates the timer
    /// token (another timer has to be requested).
    Timer(TimerToken),
    /// Advance progress bar. Progress screens only.
    Progress(u16, TString<'static>),
    /// Component has been attached to component tree. This event is sent once
    /// before any other events.
    Attach(AttachType),
    /// Internally-handled event to inform all `Child` wrappers in a sub-tree to
    /// get scheduled for painting.
    RequestPaint,
    /// Swipe and transition events
    #[cfg(feature = "touch")]
    Swipe(SwipeEvent),
}

/// Result of an event processor.
///
/// Indicates whether to continue processing the event, propagate it further,
/// or stop processing it.
#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub enum EventPropagation {
    /// Event was not consumed by the component, propagate it further.
    Continue,
    /// Event was consumed by the component, do not propagate it further.
    Stop,
}

#[derive(Copy, Clone, PartialEq, Eq)]
#[cfg_attr(feature = "debug", derive(ufmt::derive::uDebug))]
pub struct TimerToken(u32);

impl TimerToken {
    /// Value of an invalid (or missing) token.
    pub const INVALID: TimerToken = TimerToken(0);

    pub const fn from_raw(raw: u32) -> Self {
        Self(raw)
    }

    pub const fn into_raw(self) -> u32 {
        self.0
    }
}

pub struct EventCtx {
    timers: Vec<(TimerToken, Duration), { Self::MAX_TIMERS }>,
    next_token: u32,
    place_requested: bool,
    paint_requested: bool,
    anim_frame_scheduled: bool,
    page_count: Option<usize>,
    button_request: Option<ButtonRequest>,
    root_repaint_requested: bool,
    swipe_disable_req: bool,
    swipe_enable_req: bool,
    transition_out: Option<AttachType>,
}

impl EventCtx {
    /// Timer token dedicated for animation frames.
    pub const ANIM_FRAME_TIMER: TimerToken = TimerToken(1);

    /// How long into the future we should schedule the animation frame timer.
    const ANIM_FRAME_DURATION: Duration = Duration::from_millis(1);

    // 0 == `TimerToken::INVALID`,
    // 1 == `Self::ANIM_FRAME_TIMER`.
    const STARTING_TIMER_TOKEN: u32 = 2;

    /// Maximum amount of timers requested in one event tick.
    const MAX_TIMERS: usize = 4;

    pub fn new() -> Self {
        Self {
            timers: Vec::new(),
            next_token: Self::STARTING_TIMER_TOKEN,
            place_requested: true, // We need to perform a place pass in the beginning.
            paint_requested: false, /* We also need to paint, but this is supplemented by
                                    * `Child::marked_for_paint` being true. */
            anim_frame_scheduled: false,
            page_count: None,
            button_request: None,
            root_repaint_requested: false,
            swipe_disable_req: false,
            swipe_enable_req: false,
            transition_out: None,
        }
    }

    /// Indicate that position or sizes of components inside the component tree
    /// have changed, and we should perform a place pass before next event or
    /// paint traversals.
    pub fn request_place(&mut self) {
        self.place_requested = true;
    }

    /// Returns `true` if we should first perform a place traversal before
    /// processing events or painting.
    pub fn needs_place(&self) -> bool {
        self.place_requested
    }

    /// Indicate that the inner state of the component has changed, any screen
    /// content it has painted before is now invalid, and it should be painted
    /// again by the nearest `Child` wrapper.
    pub fn request_paint(&mut self) {
        self.paint_requested = true;
    }

    /// Request a timer event to be delivered after `duration` elapses.
    pub fn request_timer(&mut self, duration: Duration) -> TimerToken {
        let token = self.next_timer_token();
        self.register_timer(token, duration);
        token
    }

    /// Request an animation frame timer to fire as soon as possible.
    pub fn request_anim_frame(&mut self) {
        if !self.anim_frame_scheduled {
            self.anim_frame_scheduled = true;
            self.register_timer(Self::ANIM_FRAME_TIMER, Self::ANIM_FRAME_DURATION);
        }
    }

    pub fn request_repaint_root(&mut self) {
        self.root_repaint_requested = true;
    }

    pub fn needs_repaint_root(&self) -> bool {
        self.root_repaint_requested
    }

    pub fn needs_repaint(&self) -> bool {
        self.paint_requested
    }

    pub fn set_page_count(&mut self, count: usize) {
        // #[cfg(feature = "ui_debug")]
        // assert!(self.page_count.unwrap_or(count) == count);
        self.page_count = Some(count);
    }

    pub fn map_page_count(&mut self, func: impl Fn(usize) -> usize) {
        self.page_count = Some(func(self.page_count.unwrap_or(1)));
    }

    pub fn page_count(&self) -> Option<usize> {
        self.page_count
    }

    pub fn send_button_request(&mut self, code: ButtonRequestCode, name: TString<'static>) {
        #[cfg(feature = "ui_debug")]
        assert!(self.button_request.is_none());
        self.button_request = Some(ButtonRequest::new(code, name));
    }

    pub fn button_request(&mut self) -> Option<ButtonRequest> {
        self.button_request.take()
    }

    pub fn pop_timer(&mut self) -> Option<(TimerToken, Duration)> {
        self.timers.pop()
    }

    pub fn disable_swipe(&mut self) {
        self.swipe_disable_req = true;
    }

    pub fn disable_swipe_requested(&self) -> bool {
        self.swipe_disable_req
    }

    pub fn enable_swipe(&mut self) {
        self.swipe_enable_req = true;
    }

    pub fn enable_swipe_requested(&self) -> bool {
        self.swipe_enable_req
    }

    pub fn clear(&mut self) {
        self.place_requested = false;
        self.paint_requested = false;
        self.anim_frame_scheduled = false;
        self.page_count = None;
        #[cfg(feature = "ui_debug")]
        assert!(self.button_request.is_none());
        self.button_request = None;
        self.root_repaint_requested = false;
        self.swipe_disable_req = false;
        self.swipe_enable_req = false;
        self.transition_out = None;
    }

    fn register_timer(&mut self, token: TimerToken, duration: Duration) {
        if self.timers.push((token, duration)).is_err() {
            // The timer queue is full, this would be a development error in the layout
            // layer. Let's panic in the debug env.
            #[cfg(feature = "ui_debug")]
            fatal_error!("Timer queue is full");
        }
    }

    fn next_timer_token(&mut self) -> TimerToken {
        let token = TimerToken(self.next_token);
        // We start again from the beginning if the token counter overflows. This would
        // probably happen in case of a bug and a long-running session. Let's risk the
        // collisions in such case.
        self.next_token = self
            .next_token
            .checked_add(1)
            .unwrap_or(Self::STARTING_TIMER_TOKEN);
        token
    }

    pub fn set_transition_out(&mut self, attach_type: AttachType) {
        self.transition_out = Some(attach_type);
    }

    pub fn get_transition_out(&self) -> Option<AttachType> {
        self.transition_out
    }
}

/// Component::Msg for component parts of a swipe flow. Converting results of
/// different screens to a shared type makes things easier to work with.
///
/// Also currently the type for message emitted by Flow::event to
/// micropython. They don't need to be the same.
#[derive(Clone)]
pub enum FlowMsg {
    Confirmed,
    Cancelled,
    Info,
    Choice(usize),
    Text(ShortString),
}

#[cfg(feature = "micropython")]
impl TryFrom<FlowMsg> for crate::micropython::obj::Obj {
    type Error = crate::error::Error;

    fn try_from(val: FlowMsg) -> Result<crate::micropython::obj::Obj, Self::Error> {
        use crate::ui::layout::result;

        match val {
            FlowMsg::Confirmed => Ok(result::CONFIRMED.as_obj()),
            FlowMsg::Cancelled => Ok(result::CANCELLED.as_obj()),
            FlowMsg::Info => Ok(result::INFO.as_obj()),
            FlowMsg::Choice(i) => i.try_into(),
            FlowMsg::Text(s) => s.as_str().try_into(),
        }
    }
}
