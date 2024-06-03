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
    pub fn new(current: Option<u16>) -> Self {
        let current = current.unwrap_or(theme::backlight::get_backlight_normal());
        Self(NumberInputSliderDialog::new(
            theme::backlight::get_backlight_min(),
            theme::backlight::get_backlight_max(),
            current,
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
                display::backlight(value as _);
                None
            }
            Some(NumberInputSliderDialogMsg::Cancelled) => Some(CancelConfirmMsg::Cancelled),
            Some(NumberInputSliderDialogMsg::Confirmed) => {
                match storage::set_brightness(self.0.value() as _) {
                    Ok(_) => Some(CancelConfirmMsg::Confirmed),
                    Err(_) => Some(CancelConfirmMsg::Cancelled), // TODO: handle error
                }
            }
            None => None,
        }
    }

    fn paint(&mut self) {
        self.0.paint()
    }

    fn render<'s>(&'s self, target: &mut impl Renderer<'s>) {
        self.0.render(target);
    }

    #[cfg(feature = "ui_bounds")]
    fn bounds(&self, sink: &mut dyn FnMut(Rect)) {
        self.0.bounds(sink);
    }
}

#[cfg(feature = "ui_debug")]
impl crate::trace::Trace for SetBrightnessDialog {
    fn trace(&self, t: &mut dyn crate::trace::Tracer) {
        t.component("SetBrightnessDialog");
        t.child("input", &self.0);
    }
}
