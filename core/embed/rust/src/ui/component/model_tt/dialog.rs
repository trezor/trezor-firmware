use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::{Grid, Rect},
};

use super::button::{Button, ButtonMsg::Clicked};

pub enum DialogMsg<T> {
    Content(T),
    LeftClicked,
    RightClicked,
}

pub struct Dialog<T> {
    content: Child<T>,
    left_btn: Option<Child<Button>>,
    right_btn: Option<Child<Button>>,
}

impl<T: Component> Dialog<T> {
    pub fn new(
        area: Rect,
        content: impl FnOnce(Rect) -> T,
        left: impl FnOnce(Rect) -> Button,
        right: impl FnOnce(Rect) -> Button,
    ) -> Self {
        let grid = Grid::new(area, 5, 2);
        let content = Child::new(content(Rect::new(
            grid.row_col(0, 0).top_left(),
            grid.row_col(4, 1).bottom_right(),
        )));
        let left_btn = Child::new(left(grid.row_col(4, 0)));
        let right_btn = Child::new(right(grid.row_col(4, 1)));
        Self {
            content,
            left_btn: Some(left_btn),
            right_btn: Some(right_btn),
        }
    }
}

impl<T: Component> Component for Dialog<T> {
    type Msg = DialogMsg<T::Msg>;

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.content.event(ctx, event) {
            Some(DialogMsg::Content(msg))
        } else if let Some(Clicked) = self.left_btn.as_mut().and_then(|b| b.event(ctx, event)) {
            Some(DialogMsg::LeftClicked)
        } else if let Some(Clicked) = self.right_btn.as_mut().and_then(|b| b.event(ctx, event)) {
            Some(DialogMsg::RightClicked)
        } else {
            None
        }
    }

    fn paint(&mut self) {
        self.content.paint();
        if let Some(b) = self.left_btn.as_mut() {
            b.paint();
        }
        if let Some(b) = self.right_btn.as_mut() {
            b.paint();
        }
    }
}

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for Dialog<T>
where
    T: crate::trace::Trace,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Dialog");
        t.field("content", &self.content);
        t.field("left", &self.left_btn);
        t.field("right", &self.right_btn);
        t.close();
    }
}
