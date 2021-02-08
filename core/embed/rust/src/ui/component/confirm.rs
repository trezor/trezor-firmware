use crate::ui::geometry::Grid;

use super::{
    button::{Button, ButtonContent, ButtonMsg, ButtonStyleSheet},
    component::{Component, Event, Widget},
};

pub enum ConfirmMsg<T> {
    Content(T),
    LeftClicked,
    RightClicked,
}

pub struct Confirm<T> {
    widget: Widget,
    content: T,
    left_btn: Button,
    right_btn: Button,
}

impl<T> Confirm<T> {
    pub fn new(
        content: T,
        left: ButtonContent,
        left_styles: ButtonStyleSheet,
        right: ButtonContent,
        right_styles: ButtonStyleSheet,
    ) -> Self {
        let grid = Grid::screen(5, 2);
        Self {
            widget: Widget::new(grid.area),
            content,
            left_btn: Button::new(grid.row_col(4, 0), left, left_styles),
            right_btn: Button::new(grid.row_col(4, 1), right, right_styles),
        }
    }
}

impl<T: Component> Component for Confirm<T> {
    type Msg = ConfirmMsg<T::Msg>;

    fn widget(&mut self) -> &mut Widget {
        &mut self.widget
    }

    fn event(&mut self, event: Event) -> Option<Self::Msg> {
        if let Some(msg) = self.content.event(event) {
            Some(ConfirmMsg::Content(msg))
        } else if let Some(ButtonMsg::Clicked) = self.left_btn.event(event) {
            Some(ConfirmMsg::LeftClicked)
        } else if let Some(ButtonMsg::Clicked) = self.right_btn.event(event) {
            Some(ConfirmMsg::RightClicked)
        } else {
            None
        }
    }

    fn paint(&mut self) {
        self.content.paint();
        self.left_btn.paint();
        self.right_btn.paint();
    }
}
