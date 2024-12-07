use crate::{
    strutil::TString,
    ui::{
        component::{Child, Component, Event, EventCtx, Never},
        geometry::{Insets, Rect},
        shape::Renderer,
    },
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
    pub fn new(
        content: T,
        cancel_button: Option<TString<'static>>,
        button: TString<'static>,
    ) -> Self {
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

impl<T> Component for ShowMore<T>
where
    T: Component<Msg = Never>,
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
        self.content.event(ctx, event);
        let button_event = self.buttons.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(pos, _)) = button_event {
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

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.content.render(target);
        self.buttons.render(target);
    }
}

// DEBUG-ONLY SECTION BELOW

#[cfg(feature = "ui_debug")]
impl<T> crate::trace::Trace for ShowMore<T>
where
    T: crate::trace::Trace + Component,
{
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("ShowMore");
        t.child("buttons", &self.buttons);
        t.child("content", &self.content);
    }
}
