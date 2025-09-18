use crate::{
    storage,
    trezorhal::display,
    ui::{
        component::{Component, Event, EventCtx},
        geometry::Rect,
        shape::Renderer,
    },
};

use super::{
    super::theme,
    number_input_slider::{NumberInputSliderDialog, NumberInputSliderDialogMsg},
    CancelConfirmMsg,
};

pub struct SetBrightnessDialog(NumberInputSliderDialog);

impl SetBrightnessDialog {
    pub fn new(current: u8) -> Self {
        Self(NumberInputSliderDialog::new(
            theme::backlight::get_backlight_min().into(),
            theme::backlight::get_backlight_max().into(),
            current.into(),
        ))
    }
}

impl Component for SetBrightnessDialog {
    type Msg = CancelConfirmMsg;

    fn place(&mut self, bounds: Rect) -> Rect {
        self.0.place(bounds)
    }

    fn event(&mut self, ctx: &mut EventCtx, event: Event) -> Option<Self::Msg> {
        match self.0.event(ctx, event) {
            Some(NumberInputSliderDialogMsg::Changed(value)) => {
                // TODO: needs more analysis; why is "value" u16? Can it be changed to u8?
                // Original code: display::set_backlight(value.into());
                // Possible solution: display::set_backlight(value.try_into().unwrap());
                // It's not save. To rather use unwrap!() macro? Another solution below.
                if let Ok(val) = value.try_into() {
                    display::set_backlight(val);
                } else {
                    display::set_backlight(255);
                }
                None
            }
            Some(NumberInputSliderDialogMsg::Cancelled) => Some(CancelConfirmMsg::Cancelled),
            Some(NumberInputSliderDialogMsg::Confirmed) => {
                unwrap!(storage::set_brightness(self.0.value() as _));
                Some(CancelConfirmMsg::Confirmed)
            }
            None => None,
        }
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.0.render(target);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SetBrightnessDialog {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SetBrightnessDialog");
        t.child("input", &self.0);
    }
}
