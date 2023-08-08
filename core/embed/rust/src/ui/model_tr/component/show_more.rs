use crate::{
    strutil::StringType,
    ui::{
        component::{Child, Component, Event, EventCtx},
        geometry::{Insets, Rect},
    },
};

use super::{theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos};

pub enum CancelInfoConfirmMsg {
    Cancelled,
    Info,
    Confirmed,
}

pub struct ShowMore<T, U>
where
    U: StringType,
{
    content: Child<T>,
    buttons: Child<ButtonController<U>>,
}

impl<T, U> ShowMore<T, U>
where
    T: Component,
    U: StringType + Clone,
{
    pub fn new(content: T, cancel_button: Option<U>, button: U) -> Self {
        let btn_layout = if let Some(cancel_text) = cancel_button {
            ButtonLayout::text_armed_info(cancel_text, button)
        } else {
            ButtonLayout::cancel_armed_info(button)
        };
        Self {
            content: Child::new(content),
            buttons: Child::new(ButtonController::new(btn_layout)),
        }
    }
}

impl<T, U> Component for ShowMore<T, U>
where
    T: Component,
    U: StringType + Clone,
{
    type Msg = CancelInfoConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        let content_area = content_area.inset(Insets::top(1));
        self.content.place(content_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            match pos {
                ButtonPos::Left => {
                    return Some(CancelInfoConfirmMsg::Cancelled);
                }
                ButtonPos::Middle => {
                    return Some(CancelInfoConfirmMsg::Confirmed);
                }
                ButtonPos::Right => {
                    return Some(CancelInfoConfirmMsg::Info);
                }
            }
        }
        None
    }

    fn paint(&mut self) {
        self.content.paint();
        self.buttons.paint();
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T, U> crate::trace::Trace for ShowMore<T, U>
where
    T: crate::trace::Trace + Component,
    U: StringType + Clone,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShowMore");
        t.child("buttons", &self.buttons);
        t.child("content", &self.content);
    }
}
