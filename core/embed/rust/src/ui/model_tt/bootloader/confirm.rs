use crate::ui::component::text::paragraphs::Paragraphs;
use crate::ui::component::Pad;
use crate::ui::display::Color;
use crate::ui::geometry::Point;
use crate::ui::model_tt::bootloader::theme::{button_cancel, button_confirm};
use crate::ui::model_tt::bootloader::ReturnToC;
use crate::ui::model_tt::component::Button;
use crate::ui::model_tt::component::ButtonMsg::Clicked;
use crate::ui::model_tt::constant::{HEIGHT, WIDTH};
use crate::ui::model_tt::theme::{BG, FG, FONT_NORMAL, ICON_CANCEL, ICON_CONFIRM};
use crate::ui::{
    component::{Child, Component, Event, EventCtx},
    display,
    geometry::Rect,
};

#[repr(u32)]
#[derive(Copy, Clone)]
pub enum ConfirmMsg {
    Cancel = 1,
    Confirm = 2,
}
impl ReturnToC for ConfirmMsg {
    fn return_to_c(&self) -> u32 {
        *self as u32
    }
}

pub struct Confirm {
    bg: Pad,
    label: &'static str,
    icon: Option<&'static [u8]>,
    message: Child<Paragraphs<&'static str>>,
    warning: Option<&'static str>,
    cancel: Child<Button<&'static str>>,
    confirm: Child<Button<&'static str>>,
}

impl Confirm {
    pub fn new(
        label: &'static str,
        icon: Option<&'static [u8]>,
        message: Paragraphs<&'static str>,
    ) -> Self {
        let mut instance = Self {
            bg: Pad::with_background(FG),
            label,
            icon,
            warning: None,
            message: Child::new(message),
            cancel: Child::new(Button::with_icon(ICON_CANCEL).styled(button_cancel())),
            confirm: Child::new(Button::with_icon(ICON_CONFIRM).styled(button_confirm())),
        };
        instance.bg.clear();
        instance
    }

    pub fn add_warning(&mut self, warning: &'static str) {
        self.warning = Option::from(warning);
    }
}

impl Component for Confirm {
    type Msg = ConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.bg
            .place(Rect::new(Point::new(0, 0), Point::new(WIDTH, HEIGHT)));
        self.message.place(Rect::new(
            Point::new(55, 52),
            Point::new(WIDTH - 12, HEIGHT - 80),
        ));
        self.cancel
            .place(Rect::new(Point::new(9, 184), Point::new(117, 234)));
        self.confirm
            .place(Rect::new(Point::new(123, 184), Point::new(231, 234)));
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(Clicked) = self.cancel.event(ctx, event) {
            return Some(Self::Msg::Cancel);
        };
        if let Some(Clicked) = self.confirm.event(ctx, event) {
            return Some(Self::Msg::Confirm);
        };
        None
    }

    fn paint(&mut self) {
        self.bg.paint();
        display::rect_fill(
            Rect::new(Point::new(16, 44), Point::new(WIDTH - 12, 45)),
            BG,
        );
        display::text(Point::new(16, 32), self.label, FONT_NORMAL, BG, FG);

        match self.icon {
            Some(icon) => {
                display::icon(Point::new(32, 70), icon, Color::rgb(0x99, 0x99, 0x99), FG);
            }
            None => (),
        }

        match self.warning {
            Some(warning) => {
                display::text_center(
                    Point::new(120, 170),
                    warning,
                    FONT_NORMAL,
                    Color::rgb(0xFF, 0x00, 0x00),
                    FG,
                );
            }
            None => (),
        }

        self.message.paint();
        self.cancel.paint();
        self.confirm.paint();
    }

    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.cancel.bounds(sink);
        self.confirm.bounds(sink);
    }
}
