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
    limit: Option<u16>,
}

impl<T: PaginateFull> SwipePage<T> {
    pub fn vertical(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Vertical,
            limit: None,
        }
    }

    pub fn horizontal(inner: T) -> Self {
        Self {
            inner,
            bounds: Rect::zero(),
            axis: Axis::Horizontal,
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

    fn total_with_limit(&self) -> u16 {
        let total = self.inner.pager().total();
        let limit = self.limit.unwrap_or(total);
        total.min(limit)
    }
}

impl<T: Component + PaginateFull> Component for SwipePage<T> {
    type Msg = T::Msg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bounds = self.inner.place(bounds);
        self.bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        ctx.set_page_count(self.total_with_limit() as usize);

        if let Event::Swipe(SwipeEvent::End(direction)) = event {
            match (self.axis, direction) {
                (Axis::Vertical, Direction::Up) => {
                    self.inner.next_page();
                    ctx.request_paint();
                }
                (Axis::Vertical, Direction::Down) => {
                    self.inner.prev_page();
                    ctx.request_paint();
                }
                (Axis::Horizontal, Direction::Left) => {
                    self.inner.next_page();
                    ctx.request_paint();
                }
                (Axis::Horizontal, Direction::Right) => {
                    self.inner.prev_page();
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
        self.inner.pager().with_limit(self.total_with_limit())
    }

    fn change_page(&mut self, to_page: u16) {
        let to_page = to_page.min(self.total_with_limit());
        self.inner.change_page(to_page);
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
