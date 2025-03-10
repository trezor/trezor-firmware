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
        Footer, Frame, PromptMsg, PromptScreen, StatusScreen, SwipeContent, VerticalMenu,
    },
    theme,
};

#[derive(Copy, Clone, PartialEq, Eq, ToPrimitive)]
pub enum SetBrightness {
    Slider,
    Menu,
    Confirm,
    Confirmed,
}

impl FlowController for SetBrightness {
    #[inline]
    fn index(&'static self) -> usize {
        *self as usize
    }

    fn handle_swipe(&'static self, direction: Direction) -> Decision {
        match (self, direction) {
            (Self::Menu, Direction::Right) => Self::Slider.swipe(direction),
            (Self::Slider, Direction::Up) => Self::Confirm.swipe(direction),
            (Self::Confirm, Direction::Down) => Self::Slider.swipe(direction),
            (Self::Confirm, Direction::Left) => Self::Menu.swipe(direction),
            (Self::Confirmed, Direction::Up) => self.return_msg(FlowMsg::Confirmed),
            _ => self.do_nothing(),
        }
    }

    fn handle_event(&'static self, msg: FlowMsg) -> Decision {
        match (self, msg) {
            (Self::Slider, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Menu, FlowMsg::Cancelled) => Self::Slider.swipe_right(),
            (Self::Menu, FlowMsg::Choice(0)) => self.return_msg(FlowMsg::Cancelled),
            (Self::Confirm, FlowMsg::Confirmed) => Self::Confirmed.swipe_up(),
            (Self::Confirm, FlowMsg::Info) => Self::Menu.swipe_left(),
            (Self::Confirmed, FlowMsg::Confirmed) => self.return_msg(FlowMsg::Confirmed),
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
        footer.update_instruction(ctx, TR::instructions__tap_to_continue);
        footer.update_description(ctx, TR::setting__apply);
    }
}

pub fn new_set_brightness(brightness: Option<u8>) -> Result<SwipeFlow, Error> {
    let brightness = brightness.unwrap_or(theme::backlight::get_backlight_normal());
    let content_slider = Frame::left_aligned(
        TR::brightness__title.into(),
        NumberInputSliderDialog::new(
            theme::backlight::get_backlight_min() as u16,
            theme::backlight::get_backlight_max() as u16,
            brightness as u16,
        ),
    )
    .with_subtitle(TR::homescreen__settings_subtitle.into())
    .with_menu_button()
    .with_swipe(Direction::Up, SwipeSettings::default())
    .with_footer(
        TR::instructions__swipe_horizontally.into(),
        Some(TR::setting__adjust.into()),
    )
    .register_footer_update_fn(footer_update_fn)
    .map(|msg| match msg {
        NumberInputSliderDialogMsg::Changed(n) => {
            display::backlight(n as _);
            BRIGHTNESS.store(n as u8, Ordering::Relaxed);
            None
        }
    });

    let content_menu = Frame::left_aligned(
        "".into(),
        VerticalMenu::empty().danger(theme::ICON_CANCEL, TR::buttons__cancel.into()),
    )
    .with_cancel_button()
    .with_swipe(Direction::Right, SwipeSettings::immediate())
    .map(super::util::map_to_choice);

    let content_confirm = Frame::left_aligned(
        TR::brightness__change_title.into(),
        SwipeContent::new(PromptScreen::new_tap_to_confirm()),
    )
    .with_footer(TR::instructions__tap_to_confirm.into(), None)
    .with_menu_button()
    .with_swipe(Direction::Down, SwipeSettings::default())
    .with_swipe(Direction::Left, SwipeSettings::default())
    .map(move |msg| match msg {
        PromptMsg::Confirmed => {
            let _ = storage::set_brightness(BRIGHTNESS.load(Ordering::Relaxed));
            Some(FlowMsg::Confirmed)
        }
        _ => None,
    });

    let content_confirmed = Frame::left_aligned(
        TR::words__title_success.into(),
        SwipeContent::new(StatusScreen::new_success(
            TR::brightness__changed_title.into(),
        ))
        .with_no_attach_anim(),
    )
    .with_swipeup_footer(None)
    .with_result_icon(theme::ICON_BULLET_CHECKMARK, theme::GREEN_LIGHT)
    .map(move |_msg| Some(FlowMsg::Confirmed));

    let mut res = SwipeFlow::new(&SetBrightness::Slider)?;
    res.add_page(&SetBrightness::Slider, content_slider)?
        .add_page(&SetBrightness::Menu, content_menu)?
        .add_page(&SetBrightness::Confirm, content_confirm)?
        .add_page(&SetBrightness::Confirmed, content_confirmed)?;

    Ok(res)
}
