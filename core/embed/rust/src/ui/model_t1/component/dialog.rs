use super::{
    button::{Button, ButtonMsg::Clicked, ButtonPos},
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

impl<T: Component, U: AsRef<[u8]>> Dialog<T, U> {
    pub fn new(
        area: Rect,
        content: impl FnOnce(Rect) -> T,
        left: Option<impl FnOnce(Rect, ButtonPos) -> Button<U>>,
        right: Option<impl FnOnce(Rect, ButtonPos) -> Button<U>>,
    ) -> Self {
        let (content_area, button_area) = Self::areas(area);
        let content = Child::new(content(content_area));
        let left_btn = left.map(|f| Child::new(f(button_area, ButtonPos::Left)));
        let right_btn = right.map(|f| Child::new(f(button_area, ButtonPos::Right)));
        Self {
            content,
            left_btn,
            right_btn,
        }
    }

    fn areas(area: Rect) -> (Rect, Rect) {
        let button_height = theme::FONT_BOLD.line_height() + 2;
        let (content_area, button_area) = area.split_bottom(button_height);
        (content_area, button_area)
    }
}

impl<T: Component, U: AsRef<[u8]>> Component for Dialog<T, U> {
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
impl<T, U> crate::trace::Trace for Dialog<T, U>
where
    T: crate::trace::Trace,
    U: crate::trace::Trace + AsRef<[u8]>,
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
