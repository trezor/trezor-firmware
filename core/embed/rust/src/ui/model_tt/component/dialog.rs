use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::{Grid, Rect},
};

pub enum DialogMsg<T, L, R> {
    Content(T),
    Left(L),
    Right(R),
}

pub struct Dialog<T, L, R> {
    content: Child<T>,
    left: Child<L>,
    right: Child<R>,
}

impl<T, L, R> Dialog<T, L, R>
where
    T: Component,
    L: Component,
    R: Component,
{
    pub fn new(content: T, left: L, right: R) -> Self {
        Self {
            content: Child::new(content),
            left: Child::new(left),
            right: Child::new(right),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, L, R> Component for Dialog<T, L, R>
where
    T: Component,
    L: Component,
    R: Component,
{
    type Msg = DialogMsg<T::Msg, L::Msg, R::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let layout = DialogLayout::middle(bounds);
        self.content.place(layout.content);
        self.left.place(layout.left);
        self.right.place(layout.right);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content
            .event(ctx, event)
            .map(Self::Msg::Content)
            .or_else(|| self.left.event(ctx, event).map(Self::Msg::Left))
            .or_else(|| self.right.event(ctx, event).map(Self::Msg::Right))
    }

    fn paint(&mut self) {
        self.content.paint();
        self.left.paint();
        self.right.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.content.bounds(sink);
        self.left.bounds(sink);
        self.right.bounds(sink);
    }
}

pub struct DialogLayout {
    pub content: Rect,
    pub left: Rect,
    pub right: Rect,
}

impl DialogLayout {
    pub fn middle(area: Rect) -> Self {
        let grid = Grid::new(area, 5, 2);
        Self {
            content: Rect::new(
                grid.row_col(0, 0).top_left(),
                grid.row_col(3, 1).bottom_right(),
            ),
            left: grid.row_col(4, 0),
            right: grid.row_col(4, 1),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T, L, R> crate::trace::Trace for Dialog<T, L, R>
where
    T: crate::trace::Trace,
    L: crate::trace::Trace,
    R: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Dialog");
        t.field("content", &self.content);
        t.field("left", &self.left);
        t.field("right", &self.right);
        t.close();
    }
}
