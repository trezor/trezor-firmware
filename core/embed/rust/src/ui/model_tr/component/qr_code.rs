use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    display::{self, Font},
    geometry::Rect,
};

use super::{theme, ButtonController, ButtonControllerMsg, ButtonLayout, ButtonPos};

pub enum QRCodePageMessage {
    Confirmed,
    Cancelled,
}

pub struct QRCodePage<F, T> {
    title: T,
    title_area: Rect,
    qr_code: F,
    buttons: Child<ButtonController<T>>,
}

impl<F, T> QRCodePage<F, T>
where
    T: AsRef<str> + Clone,
{
    pub fn new(title: T, qr_code: F, btn_layout: ButtonLayout<T>) -> Self {
        Self {
            title,
            title_area: Rect::zero(),
            qr_code,
            buttons: Child::new(ButtonController::new(btn_layout)),
        }
    }
}

impl<F, T> Component for QRCodePage<F, T>
where
    T: AsRef<str> + Clone,
    F: Component,
{
    type Msg = QRCodePageMessage;

    fn place(&mut self, bounds: Rect) -> Rect {
        let (content_area, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        let (qr_code_area, title_area) = content_area.split_left(theme::QR_SIDE_MAX);
        self.title_area = title_area;
        self.qr_code.place(qr_code_area);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        let button_event = self.buttons.event(ctx, event);

        if let Some(ButtonControllerMsg::Triggered(pos)) = button_event {
            match pos {
                ButtonPos::Left => {
                    return Some(QRCodePageMessage::Cancelled);
                }
                ButtonPos::Right => {
                    return Some(QRCodePageMessage::Confirmed);
                }
                _ => {}
            }
        }

        None
    }

    fn paint(&mut self) {
        self.qr_code.paint();
        // TODO: add the Label from Suite
        display::text_multiline(
            self.title_area,
            self.title.as_ref(),
            Font::MONO,
            theme::FG,
            theme::BG,
        );
        self.buttons.paint();
    }
}

#[cfg(feature = "ui_debug")]
use super::ButtonAction;
#[cfg(feature = "ui_debug")]
use heapless::String;

#[cfg(feature = "ui_debug")]
impl<F, T> crate::trace::Trace for QRCodePage<F, T>
where
    T: AsRef<str> + Clone,
{
    fn get_btn_action(&self, pos: ButtonPos) -> String<25> {
        match pos {
            ButtonPos::Left => ButtonAction::Cancel.string(),
            ButtonPos::Right => ButtonAction::Confirm.string(),
            ButtonPos::Middle => ButtonAction::empty(),
        }
    }

    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.open("QRCodePage");
        t.kw_pair("active_page", "0");
        t.kw_pair("page_count", "1");
        self.report_btn_actions(t);
        t.content_flag();
        t.string("QR CODE");
        t.string(self.title.as_ref());
        t.content_flag();
        t.field("buttons", &self.buttons);
        t.close();
    }
}
