use super::{
    button::{Button, ButtonMsg::Clicked},
    theme,
};
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::Rect,
};

pub enum DialogMsg<T> {
    Content(T),
    LeftClicked,
    RightClicked,
}

pub struct Dialog<T, U> {
    content: Child<T>,
    left_btn: Option<Child<Button<U>>>,
    right_btn: Option<Child<Button<U>>>,
}

impl<T, U> Dialog<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    pub fn new(content: T, left: Option<Button<U>>, right: Option<Button<U>>) -> Self {
        Self {
            content: Child::new(content),
            left_btn: left.map(Child::new),
            right_btn: right.map(Child::new),
        }
    }

    pub fn inner(&self) -> &T {
        self.content.inner()
    }
}

impl<T, U> Component for Dialog<T, U>
where
    T: Component,
    U: AsRef<str>,
{
    type Msg = DialogMsg<T::Msg>;

    fn place(&mut self, bounds: Rect) -> Rect {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (content_area, button_area) = bounds.split_bottom(button_height);
        self.content.place(content_area);
        self.left_btn.as_mut().map(|b| b.place(button_area));
        self.right_btn.as_mut().map(|b| b.place(button_area));
        bounds
    }

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
impl<T, U> crate::trace::Trace for Dialog<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace + AsRef<str>,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("Dialog");
        t.field("content", &self.content);
        if let Some(label) = &self.left_btn {
            t.field("left", label);
        }
        if let Some(label) = &self.right_btn {
            t.field("right", label);
        }
        t.close();
    }
}
