use core::sync::atomic::{AtomicU8, Ordering};

use crate::{
    error::Error,
    storage,
    translations::TR,
    trezorhal::display,
    ui::{
        component::{swipe_detect::SwipeSettings, EventCtx, FlowMsg},
        flow::{
            base::{Decision, DecisionBuilder as _},
            FlowController, SwipeFlow,
        },
        geometry::Direction,
    },
};

use super::super::{
    component::{
        number_input_slider::{NumberInputSliderDialog, NumberInputSliderDialogMsg},
        Footer, Frame,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetBrightness {
    Slider,
}

impl FlowController for SetBrightness {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Slider, Direction::Up) => {
                unwrap!(storage::set_brightness(BRIGHTNESS.load(Ordering::Relaxed)));
                self.return_msg(FlowMsg::Confirmed)
            }
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Slider, FlowMsg::Cancelled) => self.return_msg(FlowMsg::Cancelled),
            _ => self.do_nothing(),
        }
    }
}

static BRIGHTNESS: AtomicU8 = AtomicU8::new(0);

fn footer_update_fn(
    content: &NumberInputSliderDialog,
    ctx: &mut EventCtx,
    footer: &mut Footer<'static>,
) {
    if content.value() == content.init_value() || content.touching() {
        footer.update_instruction(ctx, TR::instructions__swipe_horizontally);
        footer.update_description(ctx, TR::setting__adjust);
    } else {
        footer.update_instruction(ctx, TR::instructions__tap_to_confirm);
        footer.update_description(ctx, TR::setting__apply);
    }
}

pub fn new_set_brightness(brightness: u8) -> Result<SwipeFlow, Error> {
    let content_slider = Frame::left_aligned(
        TR::brightness__title.into(),
        NumberInputSliderDialog::new(
            theme::backlight::get_backlight_min().into(),
            theme::backlight::get_backlight_max().into(),
            brightness.into(),
        ),
    )
    .with_subtitle(TR::homescreen__settings_subtitle.into())
    .with_cancel_button()
    .with_swipe(Direction::Up, SwipeSettings::Default)
    .with_footer(
        TR::instructions__swipe_horizontally.into(),
        Some(TR::setting__adjust.into()),
    )
    .register_footer_update_fn(footer_update_fn)
    .map(|msg| match msg {
        NumberInputSliderDialogMsg::Changed(n) => {
            display::set_backlight(n as _);
            BRIGHTNESS.store(n as u8, Ordering::Relaxed);
            None
        }
    });

    let mut res = SwipeFlow::new(&SetBrightness::Slider)?;
    res.add_page(&SetBrightness::Slider, content_slider)?;

    Ok(res)
}
