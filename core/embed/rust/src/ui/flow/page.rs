use crate::{
    micropython::gc::Gc,
    ui::{
        animation::Animation,
        component::{base::SwipeEvent, Component, Event, EventCtx, Paginate, SwipeDirection},
        flow::base::Swipable,
        geometry::{Axis, Rect},
        shape::Renderer,
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
}

impl<T: Component + Paginate + Clone> SwipePage<T> {
    pub fn vertical(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Vertical,
            pages: 1,
            current: 0,
        }
    }

    pub fn horizontal(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Horizontal,
            pages: 1,
            current: 0,
        }
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
        ctx.set_page_count(self.pages);

        if let Event::Swipe(SwipeEvent::End(direction)) = event {
            if let Axis::Vertical = self.axis {
                match direction {
                    SwipeDirection::Up => {
                        self.current = (self.current + 1).min(self.pages - 1);
                        self.inner.change_page(self.current);
                        ctx.request_paint();
                    }
                    SwipeDirection::Down => {
                        self.current = self.current.saturating_sub(1);
                        self.inner.change_page(self.current);
                        ctx.request_paint();
                    }
                    _ => {}
                }
            }
            if let Axis::Horizontal = self.axis {
                match direction {
                    SwipeDirection::Left => {
                        self.current = (self.current + 1).min(self.pages - 1);
                        self.inner.change_page(self.current);
                        ctx.request_paint();
                    }
                    SwipeDirection::Right => {
                        self.current = self.current.saturating_sub(1);
                        self.inner.change_page(self.current);
                        ctx.request_paint();
                    }
                    _ => {}
                }
            }
        }

        self.inner.event(ctx, event)
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target)
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

impl<T: Component> Swipable<T::Msg> for IgnoreSwipe<T> {}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for IgnoreSwipe<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.0.trace(t)
    }
}
