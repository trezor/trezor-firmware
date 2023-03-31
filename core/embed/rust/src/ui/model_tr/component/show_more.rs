use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    geometry::{Insets, Rect},
};

use super::{theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos};

pub enum CancelInfoConfirmMsg {
    Cancelled,
    Info,
    Confirmed,
}

pub struct ShowMore<T> {
    content: Child<T>,
    buttons: Child<ButtonController>,
}

impl<T> ShowMore<T>
where
    T: Component,
{
    pub fn new(content: T) -> Self {
        let btn_layout = ButtonLayout::cancel_armed_text("CONFIRM".into(), "i".into());
        Self {
            content: Child::new(content),
            buttons: Child::new(ButtonController::new(btn_layout)),
        }
    }
}

impl<T> Component for ShowMore<T>
where
    T: Component,
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
use super::ButtonAction;
#[cfg(feature = "ui_debug")]
use heapless::String;

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ShowMore<T>
where
    T: crate::trace::Trace + Component,
{
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => ButtonAction::Cancel.string(),
            ButtonPos::Middle => ButtonAction::Confirm.string(),
            ButtonPos::Right => ButtonAction::Action("INFO").string(),
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("ShowMore");
        self.report_btn_actions(t);
        t.field("buttons", &self.buttons);
        t.field("content", &self.content);
        t.close();
    }
}
