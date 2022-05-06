use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::{Grid, Rect},
};

use super::{theme, Button};

pub enum DialogMsg<T, U> {
    Content(T),
    Controls(U),
}

pub struct Dialog<T, U> {
    content: Child<T>,
    controls: Child<U>,
}

impl<T, U> Dialog<T, U>
where
    T: Component,
    U: Component,
{
    pub fn new(content: T, controls: U) -> Self {
        Self {
            content: Child::new(content),
            controls: Child::new(controls),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, U> Component for Dialog<T, U>
where
    T: Component,
    U: Component,
{
    type Msg = DialogMsg<T::Msg, U::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let layout = DialogLayout::middle(bounds);
        self.content.place(layout.content);
        self.controls.place(layout.controls);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        self.content
            .event(ctx, event)
            .map(Self::Msg::Content)
            .or_else(|| self.controls.event(ctx, event).map(Self::Msg::Controls))
    }

    fn paint(&mut self) {
        self.content.paint();
        self.controls.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.content.bounds(sink);
        self.controls.bounds(sink);
    }
}

pub struct DialogLayout {
    pub content: Rect,
    pub controls: Rect,
}

impl DialogLayout {
    pub fn middle(area: Rect) -> Self {
        let grid = Grid::new(area, 5, 1);
        Self {
            content: Rect::new(
                grid.row_col(0, 0).top_left(),
                grid.row_col(3, 0).bottom_right(),
            ),
            controls: grid.row_col(4, 0),
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for Dialog<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Dialog");
        t.field("content", &self.content);
        t.field("controls", &self.controls);
        t.close();
    }
}
