use crate::ui::{
    component::{Component, Event, EventCtx, Paginate},
    event::SwipeEvent,
    geometry::{Axis, Direction, Rect},
    shape::Renderer,
};

/// Allows any implementor of `Paginate` to be part of `Swipable` UI flow.
/// Renders sliding animation when changing pages.
pub struct SwipePage<T> {
    inner: T,
    bounds: Rect,
    axis: Axis,
    pages: usize,
    current: usize,
    limit: Option<usize>,
}

impl<T: Component + Paginate> SwipePage<T> {
    pub fn vertical(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Vertical,
            pages: 1,
            current: 0,
            limit: None,
        }
    }

    pub fn horizontal(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Horizontal,
            pages: 1,
            current: 0,
            limit: None,
        }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }

    pub fn with_limit(mut self, limit: Option<usize>) -> Self {
        self.limit = limit;
        self
    }
}

impl<T: Component + Paginate> Component for SwipePage<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = self.inner.place(bounds);
        self.pages = self.inner.page_count();
        if let Some(limit) = self.limit {
            self.pages = self.pages.min(limit);
        }
        self.bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.pages);

        if let Event::Swipe(SwipeEvent::End(direction)) = event {
            match (self.axis, direction) {
                (Axis::Vertical, Direction::Up) => {
                    self.current = (self.current + 1).min(self.pages - 1);
                    self.inner.change_page(self.current);
                    ctx.request_paint();
                }
                (Axis::Vertical, Direction::Down) => {
                    self.current = self.current.saturating_sub(1);
                    self.inner.change_page(self.current);
                    ctx.request_paint();
                }
                (Axis::Horizontal, Direction::Left) => {
                    self.current = (self.current + 1).min(self.pages - 1);
                    self.inner.change_page(self.current);
                    ctx.request_paint();
                }
                (Axis::Horizontal, Direction::Right) => {
                    self.current = self.current.saturating_sub(1);
                    self.inner.change_page(self.current);
                    ctx.request_paint();
                }
                _ => {}
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
