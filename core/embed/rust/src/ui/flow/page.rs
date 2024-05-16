use crate::{
    micropython::gc::Gc,
    time::Instant,
    ui::{
        animation::Animation,
        component::{Component, Event, EventCtx, Paginate, SwipeDirection},
        flow::base::Swipable,
        geometry::{Axis, Rect},
        shape::Renderer,
        util,
    },
};

pub struct Transition<T> {
    /// Clone of the component before page change.
    cloned: Gc<T>,
    /// Animation progress.
    animation: Animation<f32>,
    /// Direction of the slide animation.
    direction: SwipeDirection,
}

/// Allows any implementor of `Paginate` to be part of `Swipable` UI flow.
/// Renders sliding animation when changing pages.
pub struct SwipePage<T> {
    inner: T,
    bounds: Rect,
    axis: Axis,
    pages: usize,
    current: usize,
    transition: Option<Transition<T>>,
}

impl<T: Component + Paginate + Clone> SwipePage<T> {
    pub fn vertical(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Vertical,
            pages: 1,
            current: 0,
            transition: None,
        }
    }

    pub fn horizontal(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Horizontal,
            pages: 1,
            current: 0,
            transition: None,
        }
    }

    fn handle_transition(ctx: &mut EventCtx, event: Event, transition: &mut Transition<T>) -> bool {
        let mut finished = false;
        if let Event::Timer(EventCtx::ANIM_FRAME_TIMER) = event {
            if transition.animation.finished(Instant::now()) {
                finished = true;
            } else {
                ctx.request_anim_frame();
            }
            ctx.request_paint()
        }
        finished
    }

    fn render_transition<'s>(
        &'s self,
        transition: &'s Transition<T>,
        target: &mut impl Renderer<'s>,
    ) {
        target.in_clip(self.bounds, &|target| {
            util::render_slide(
                |target| transition.cloned.render(target),
                |target| self.inner.render(target),
                transition.animation.value(Instant::now()),
                transition.direction,
                target,
            );
        });
    }
}

impl<T: Component + Paginate + Clone> Component for SwipePage<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = self.inner.place(bounds);
        self.pages = self.inner.page_count();
        self.bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(t) = &mut self.transition {
            let finished = Self::handle_transition(ctx, event, t);
            if finished {
                // FIXME: how to ensure the Gc allocation is returned?
                self.transition = None
            }
            return None;
        }
        self.inner.event(ctx, event)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        if let Some(t) = &self.transition {
            return self.render_transition(t, target);
        }
        self.inner.render(target)
    }
}

impl<T: Component + Paginate + Clone> Swipable for SwipePage<T> {
    fn swipe_start(&mut self, ctx: &mut EventCtx, direction: SwipeDirection) -> bool {
        match (self.axis, direction) {
            // Wrong direction
            (Axis::Horizontal, SwipeDirection::Up | SwipeDirection::Down) => return false,
            (Axis::Vertical, SwipeDirection::Left | SwipeDirection::Right) => return false,
            // Begin
            (_, SwipeDirection::Right | SwipeDirection::Down) if self.current == 0 => return false,
            // End
            (_, SwipeDirection::Left | SwipeDirection::Up) if self.current + 1 >= self.pages => {
                return false
            }
            _ => {}
        };
        self.current = match direction {
            SwipeDirection::Left | SwipeDirection::Up => (self.current + 1).min(self.pages - 1),
            SwipeDirection::Right | SwipeDirection::Down => self.current.saturating_sub(1),
        };
        if util::animation_disabled() {
            self.inner.change_page(self.current);
            ctx.request_paint();
            return true;
        }
        self.transition = Some(Transition {
            cloned: unwrap!(Gc::new(self.inner.clone())),
            animation: Animation::new(0.0f32, 1.0f32, util::SLIDE_DURATION, Instant::now()),
            direction,
        });
        self.inner.change_page(self.current);
        ctx.request_anim_frame();
        ctx.request_paint();
        true
    }

    fn swipe_finished(&self) -> bool {
        self.transition.is_none()
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for SwipePage<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.inner.trace(t)
    }
}

/// Make any component swipable by ignoring all swipe events.
pub struct IgnoreSwipe<T>(T);

impl<T> IgnoreSwipe<T> {
    pub fn new(inner: T) -> Self {
        IgnoreSwipe(inner)
    }
}

impl<T: Component> Component for IgnoreSwipe<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.0.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.0.event(ctx, event)
    }

    fn paint(&mut self) {
        self.0.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.0.render(target)
    }
}

impl<T> Swipable for IgnoreSwipe<T> {}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for IgnoreSwipe<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.0.trace(t)
    }
}
