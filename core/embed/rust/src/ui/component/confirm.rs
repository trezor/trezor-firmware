use crate::ui::math::{Grid, Rect};

use super::{
    button::{Button, ButtonContent, ButtonMsg::Clicked, ButtonStyleSheet},
    component::{Component, Event, EventCtx, Widget},
};

pub enum ConfirmMsg<T: Component> {
    Content(T::Msg),
    LeftClicked,
    RightClicked,
}

pub struct Confirm<T> {
    widget: Widget,
    content: T,
    left_btn: Option<Button>,
    right_btn: Option<Button>,
}

impl<T> Confirm<T> {
    pub fn new(
        area: Rect,
        content: T,
        left: Option<ButtonContent>,
        left_styles: ButtonStyleSheet,
        right: Option<ButtonContent>,
        right_styles: ButtonStyleSheet,
    ) -> Self {
        let grid = if left.is_some() && right.is_some() {
            Grid::new(area, 5, 2)
        } else {
            Grid::new(area, 5, 1)
        };
        let left_btn = left.map(|left| Button::new(grid.row_col(4, 0), left, left_styles));
        let right_btn = right.map(|right| Button::new(grid.row_col(4, 1), right, right_styles));
        Self {
            widget: Widget::new(grid.area),
            content,
            left_btn,
            right_btn,
        }
    }
}

impl<T: Component> Component for Confirm<T> {
    type Msg = ConfirmMsg<T>;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.content.event(ctx, event) {
            Some(ConfirmMsg::Content(msg))
        } else if let Some(Clicked) = self.left_btn.as_mut().and_then(|b| b.event(ctx, event)) {
            Some(ConfirmMsg::LeftClicked)
        } else if let Some(Clicked) = self.right_btn.as_mut().and_then(|b| b.event(ctx, event)) {
            Some(ConfirmMsg::RightClicked)
        } else {
            None
        }
    }

    fn paint(&mut self) {
        self.content.paint_if_requested();
        self.left_btn.as_mut().map(|b| b.paint_if_requested());
        self.right_btn.as_mut().map(|b| b.paint_if_requested());
    }
}
