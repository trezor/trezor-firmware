use super::{theme, ButtonController, ButtonControllerMsg, ButtonDetails, ButtonLayout, ButtonPos};
use crate::micropython::Error;
use crate::strutil::TString;
use crate::ui::component::{Child, Component, Event, EventCtx, Pad, Qr};
use crate::ui::geometry::Rect;
use crate::ui::shape::Renderer;

const QR_BORDER: i16 = 3;

/// QR code of an address, opened from the context menu. The account
/// information is shown in its own menu item.
pub struct AddressDetails {
    qr_code: Qr,
    pad: Pad,
    buttons: Child<ButtonController>,
}

impl AddressDetails {
    pub fn new(qr_address: TString<'static>, case_sensitive: bool) -> Result<Self, Error> {
        let qr_code = qr_address
            .map(|s| Qr::new(s, case_sensitive))?
            .with_border(QR_BORDER);
        Ok(Self {
            qr_code,
            pad: Pad::with_background(theme::BG).with_clear(),
            buttons: Child::new(ButtonController::new(ButtonLayout::new(
                Some(ButtonDetails::close_icon()),
                None,
                None,
            ))),
        })
    }
}

impl Component for AddressDetails {
    type Msg = ();

    fn place(&mut self, bounds: Rect) -> Rect {
        // QR code is being placed on the whole bounds, so it can be as big as possible
        // (it will not collide with the buttons, they are narrow and on the sides).
        // Therefore, also placing pad on the whole bounds.
        self.qr_code.place(bounds);
        self.pad.place(bounds);
        let (_, button_area) = bounds.split_bottom(theme::BUTTON_HEIGHT);
        self.buttons.place(button_area);
        bounds
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        if let Some(ButtonControllerMsg::Triggered(ButtonPos::Left, _)) =
            self.buttons.event(ctx, event)
        {
            return Some(());
        }
        None
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.pad.render(target);
        self.buttons.render(target);
        self.qr_code.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for AddressDetails {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("AddressDetails");
        t.child("qr_code", &self.qr_code);
    }
}
