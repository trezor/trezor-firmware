use crate::ui::{
    component::{Component, Event, EventCtx, PaginateFull},
    event::SwipeEvent,
    geometry::{Axis, Direction, Rect},
    shape::Renderer,
    util::Pager,
};

/// Allows any implementor of `Paginate` to be part of `Swipable` UI flow.
/// Renders sliding animation when changing pages.
pub struct SwipePage<T> {
    inner: T,
    bounds: Rect,
    axis: Axis,
    pager: Pager,
    limit: Option<u16>,
}

impl<T: Component + PaginateFull> SwipePage<T> {
    pub fn vertical(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Vertical,
            pager: Pager::single_page(),
            limit: None,
        }
    }

    pub fn horizontal(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Horizontal,
            pager: Pager::single_page(),
            limit: None,
        }
    }

    pub fn inner(&self) -> &T {
        &self.inner
    }

    pub fn with_limit(mut self, limit: Option<u16>) -> Self {
        self.limit = limit;
        self
    }
}

impl<T: Component + PaginateFull> Component for SwipePage<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = self.inner.place(bounds);
        self.pager = self.inner.pager();
        if let Some(limit) = self.limit {
            self.pager = self.pager.with_limit(limit);
        }
        self.bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.pager.total() as usize);

        if let Event::Swipe(SwipeEvent::End(direction)) = event {
            match (self.axis, direction) {
                (Axis::Vertical, Direction::Up) => {
                    self.pager.goto_next();
                    self.inner.change_page(self.pager.current());
                    ctx.request_paint();
                }
                (Axis::Vertical, Direction::Down) => {
                    self.pager.goto_prev();
                    self.inner.change_page(self.pager.current());
                    ctx.request_paint();
                }
                (Axis::Horizontal, Direction::Left) => {
                    self.pager.goto_next();
                    self.inner.change_page(self.pager.current());
                    ctx.request_paint();
                }
                (Axis::Horizontal, Direction::Right) => {
                    self.pager.goto_prev();
                    self.inner.change_page(self.pager.current());
                    ctx.request_paint();
                }
                _ => {}
            }
        }

        self.inner.event(ctx, event)
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.inner.render(target)
    }
}

impl<T: PaginateFull> PaginateFull for SwipePage<T> {
    fn pager(&self) -> Pager {
        self.pager
    }

    fn change_page(&mut self, to_page: u16) {
        self.pager.set_current(to_page);
        self.inner.change_page(self.pager.current());
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
