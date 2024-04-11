use crate::ui::{
    component::{Component, Event, EventCtx, Paginate},
    flow::base::{Swipable, SwipeDirection},
    geometry::{Axis, Rect},
    shape::Renderer,
};

/// Allows any implementor of `Paginate` to be part of `Swipable` UI flow.
#[derive(Clone)]
pub struct SwipePage<T> {
    inner: T,
    axis: Axis,
    pages: usize,
    current: usize,
}

impl<T> SwipePage<T> {
    pub fn vertical(inner: T) -> Self {
        Self {
            inner,
            axis: Axis::Vertical,
            pages: 1,
            current: 0,
        }
    }
}

impl<T: Component + Paginate> Component for SwipePage<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let result = self.inner.place(bounds);
        self.pages = self.inner.page_count();
        result
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let msg = self.inner.event(ctx, event);
        msg
    }

    fn paint(&mut self) {
        self.inner.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target)
    }
}

impl<T: Component + Paginate> Swipable for SwipePage<T> {
    fn can_swipe(&self, direction: SwipeDirection) -> bool {
        match (self.axis, direction) {
            (Axis::Horizontal, SwipeDirection::Up | SwipeDirection::Down) => false,
            (Axis::Vertical, SwipeDirection::Left | SwipeDirection::Right) => false,
            (_, SwipeDirection::Left | SwipeDirection::Up) => self.current + 1 < self.pages,
            (_, SwipeDirection::Right | SwipeDirection::Down) => self.current > 0,
        }
    }

    fn swiped(&mut self, ctx: &mut EventCtx, direction: SwipeDirection) {
        match (self.axis, direction) {
            (Axis::Horizontal, SwipeDirection::Up | SwipeDirection::Down) => return,
            (Axis::Vertical, SwipeDirection::Left | SwipeDirection::Right) => return,
            (_, SwipeDirection::Left | SwipeDirection::Up) => {
                self.current = (self.current + 1).min(self.pages - 1);
            }
            (_, SwipeDirection::Right | SwipeDirection::Down) => {
                self.current = self.current.saturating_sub(1);
            }
        }
        self.inner.change_page(self.current);
        ctx.request_paint();
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
#[derive(Clone)]
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

impl<T> Swipable for IgnoreSwipe<T> {
    fn can_swipe(&self, _direction: SwipeDirection) -> bool {
        false
    }
    fn swiped(&mut self, _ctx: &mut EventCtx, _direction: SwipeDirection) {}
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for IgnoreSwipe<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        self.0.trace(t)
    }
}
